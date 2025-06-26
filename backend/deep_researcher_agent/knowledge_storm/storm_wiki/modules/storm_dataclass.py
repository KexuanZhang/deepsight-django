import copy
import re
import threading
from collections import OrderedDict
from typing import Union, Optional, Any, List, Tuple, Dict

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import torch

from ...interface import Information, InformationTable, Article, ArticleSectionNode
from ...utils import ArticleTextProcessing, FileIOHelper


def get_device():
    """Detect the best available device: 'cuda', 'mps', or 'cpu'."""
    if torch.cuda.is_available():
        return "cuda"
    # if torch.backends.mps.is_available() and torch.backends.mps.is_built():
    #     return "mps"
    return "cpu"


class DialogueTurn:
    def __init__(
        self,
        agent_utterance: str = None,
        user_utterance: str = None,
        search_queries: Optional[List[str]] = None,
        search_results: Optional[List[Union[Information, Dict]]] = None,
    ):
        self.agent_utterance = agent_utterance
        self.user_utterance = user_utterance
        self.search_queries = search_queries
        self.search_results = search_results

        if self.search_results:
            for idx in range(len(self.search_results)):
                if type(self.search_results[idx]) == dict:
                    self.search_results[idx] = Information.from_dict(
                        self.search_results[idx]
                    )

    def log(self):
        """
        Returns a json object that contains all information inside `self`
        """
        search_results_data = []
        if self.search_results is not None:
            search_results_data = [data.to_dict() for data in self.search_results]

        return OrderedDict(
            {
                "agent_utterance": self.agent_utterance,
                "user_utterance": self.user_utterance,
                "search_queries": self.search_queries,
                "search_results": search_results_data,
            }
        )


class StormInformationTable(InformationTable):
    """
    Base class for information tables in Storm. Provides core functionality for
    storing and retrieving information.
    """

    ENCODER_MODEL_NAME = "all-mpnet-base-v2"  # "Alibaba-NLP/gte-multilingual-base"

    def __init__(self, conversations=None):
        super().__init__()
        self.conversations = conversations or []
        self.url_to_info = (
            StormInformationTable.construct_url_to_info(self.conversations)
            if self.conversations
            else {}
        )

        # Initialize model-related attributes
        self.encoder = None
        self._predict_lock = threading.Lock()
        self._device = get_device()

        # Storage for snippets
        self.collected_urls = []
        self.collected_snippets = []
        self.encoded_snippets = None

    def _initialize_encoder(self):
        """Initialize the sentence encoder if not already initialized."""
        if self.encoder is None:
            with self._predict_lock:
                if self.encoder is None:
                    self.encoder = SentenceTransformer(
                        self.ENCODER_MODEL_NAME,
                        trust_remote_code=True,
                        device=self._device,
                    )

    @staticmethod
    def construct_url_to_info(
        conversations: List[Tuple[str, List[DialogueTurn]]],
    ) -> Dict[str, Information]:
        url_to_info = {}

        for persona, conv in conversations:
            for turn in conv:
                # Skip if search_results is None
                if turn.search_results is None:
                    continue

                for storm_info in turn.search_results:
                    if storm_info.url in url_to_info:
                        url_to_info[storm_info.url].snippets.extend(storm_info.snippets)
                    else:
                        url_to_info[storm_info.url] = storm_info
        for url in url_to_info:
            url_to_info[url].snippets = list(set(url_to_info[url].snippets))
        return url_to_info

    @staticmethod
    def construct_log_dict(
        conversations: List[Tuple[str, List[DialogueTurn]]],
    ) -> List[Dict[str, Union[str, Any]]]:
        conversation_log = []
        for persona, conv in conversations:
            conversation_log.append(
                {"perspective": persona, "dlg_turns": [turn.log() for turn in conv]}
            )
        return conversation_log

    def dump_url_to_info(self, path):
        url_to_info = copy.deepcopy(self.url_to_info)
        for url in url_to_info:
            url_to_info[url] = url_to_info[url].to_dict()
        FileIOHelper.dump_json(url_to_info, path)

    @classmethod
    def from_conversation_log_file(cls, path):
        conversation_log_data = FileIOHelper.load_json(path)
        conversations = []
        for item in conversation_log_data:
            dialogue_turns = [DialogueTurn(**turn) for turn in item["dlg_turns"]]
            persona = item["perspective"]
            conversations.append((persona, dialogue_turns))
        return cls(conversations)

    def prepare_table_for_retrieval(self):
        """
        Prepare the table for retrieval by encoding snippets.
        """
        self._initialize_encoder()

        self.collected_urls = []
        self.collected_snippets = []

        for url, information in self.url_to_info.items():
            for snippet in information.snippets:
                self.collected_urls.append(url)
                self.collected_snippets.append(snippet)

        if self.collected_snippets:
            self.encoded_snippets = self.encoder.encode(
                self.collected_snippets,
                # batch_size=2, # for larger models
                convert_to_tensor=True,
                show_progress_bar=False,
            )

    def retrieve_information(
        self, queries: Union[List[str], str], search_top_k: int
    ) -> List[Information]:
        """
        Basic retrieval using cosine similarity with encoded snippets.
        """
        if not isinstance(queries, list):
            queries = [queries]

        if not self.collected_snippets:
            return []

        self._initialize_encoder()

        selected_urls = []
        selected_snippets = []

        for query in queries:
            encoded_query = self.encoder.encode(query, convert_to_tensor=True)
            encoded_query = encoded_query.to(self.encoded_snippets.device)

            # Calculate cosine similarities
            sim = cosine_similarity(
                [encoded_query.cpu().numpy()], self.encoded_snippets.cpu().numpy()
            )[0]

            sorted_indices = np.argsort(sim)
            for i in sorted_indices[-search_top_k:][::-1]:
                selected_urls.append(self.collected_urls[i])
                selected_snippets.append(self.collected_snippets[i])

        url_to_snippets = {}
        for url, snippet in zip(selected_urls, selected_snippets):
            if url not in url_to_snippets:
                url_to_snippets[url] = set()
            url_to_snippets[url].add(snippet)

        selected_url_to_info = {}
        for url in url_to_snippets:
            selected_url_to_info[url] = copy.deepcopy(self.url_to_info[url])
            selected_url_to_info[url].snippets = list(url_to_snippets[url])

        return list(selected_url_to_info.values())


class StormArticle(Article):
    def __init__(self, topic_name):
        super().__init__(topic_name=topic_name)
        self.reference = {"url_to_unified_index": {}, "url_to_info": {}}

    def find_section(
        self, node: ArticleSectionNode, name: str
    ) -> Optional[ArticleSectionNode]:
        """
        Return the node of the section given the section name.

        Args:
            node: the node as the root to find.
            name: the name of node as section name

        Return:
            reference of the node or None if section name has no match
        """
        if node.section_name == name:
            return node
        for child in node.children:
            result = self.find_section(child, name)
            if result:
                return result
        return None

    def _merge_new_info_to_references(
        self, new_info_list: List[Information], index_to_keep=None
    ) -> Dict[int, int]:
        """
        Merges new storm information into existing references and updates the citation index mapping.

        Args:
        new_info_list (List[Information]): A list of dictionaries representing new storm information.
        index_to_keep (List[int]): A list of index of the new_info_list to keep. If none, keep all.

        Returns:
        Dict[int, int]: A dictionary mapping the index of each storm information piece in the input list
                        to its unified citation index in the references.
        """
        citation_idx_mapping = {}
        for idx, storm_info in enumerate(new_info_list):
            if index_to_keep is not None and idx not in index_to_keep:
                continue
            url = storm_info.url
            if url not in self.reference["url_to_unified_index"]:
                self.reference["url_to_unified_index"][url] = (
                    len(self.reference["url_to_unified_index"]) + 1
                )  # The citation index starts from 1.
                self.reference["url_to_info"][url] = storm_info
            else:
                existing_snippets = self.reference["url_to_info"][url].snippets
                existing_snippets.extend(storm_info.snippets)
                self.reference["url_to_info"][url].snippets = list(
                    set(existing_snippets)
                )
            citation_idx_mapping[idx + 1] = self.reference["url_to_unified_index"][
                url
            ]  # The citation index starts from 1.
        return citation_idx_mapping

    def insert_or_create_section(
        self,
        article_dict: Dict[str, Dict],
        parent_section_name: str = None,
        trim_children=False,
    ):
        parent_node = (
            self.root
            if parent_section_name is None
            else self.find_section(self.root, parent_section_name)
        )

        if trim_children:
            section_names = set(article_dict.keys())
            for child in parent_node.children[:]:
                if child.section_name not in section_names:
                    parent_node.remove_child(child)

        for section_name, content_dict in article_dict.items():
            current_section_node = self.find_section(parent_node, section_name)
            if current_section_node is None:
                current_section_node = ArticleSectionNode(
                    section_name=section_name, content=content_dict["content"].strip()
                )
                insert_to_front = (
                    parent_node.section_name == self.root.section_name
                    and current_section_node.section_name == "summary"
                )
                parent_node.add_child(
                    current_section_node, insert_to_front=insert_to_front
                )
            else:
                current_section_node.content = content_dict["content"].strip()

            self.insert_or_create_section(
                article_dict=content_dict["subsections"],
                parent_section_name=section_name,
                trim_children=True,
            )

    def update_section(
        self,
        current_section_content: str,
        current_section_info_list: List[Information],
        parent_section_name: Optional[str] = None,
    ) -> Optional[ArticleSectionNode]:
        """
        Add new section to the article.

        Args:
            current_section_name: new section heading name in string format.
            parent_section_name: under which parent section to add the new one. Default to root.
            current_section_content: optional section content.

        Returns:
            the ArticleSectionNode for current section if successfully created / updated. Otherwise none.
        """

        if current_section_info_list is not None:
            references = set(
                [int(x) for x in re.findall(r"\[(\d+)\]", current_section_content)]
            )
            # for any reference number greater than max number of references, delete the reference
            if len(references) > 0:
                max_ref_num = max(references)
                if max_ref_num > len(current_section_info_list):
                    for i in range(len(current_section_info_list), max_ref_num + 1):
                        current_section_content = current_section_content.replace(
                            f"[{i}]", ""
                        )
                        if i in references:
                            references.remove(i)
            # for any reference that is not used, trim it from current_section_info_list
            index_to_keep = [i - 1 for i in references]
            citation_mapping = self._merge_new_info_to_references(
                current_section_info_list, index_to_keep
            )
            current_section_content = ArticleTextProcessing.update_citation_index(
                current_section_content, citation_mapping
            )

        if parent_section_name is None:
            parent_section_name = self.root.section_name
        article_dict = ArticleTextProcessing.parse_article_into_dict(
            current_section_content
        )
        self.insert_or_create_section(
            article_dict=article_dict,
            parent_section_name=parent_section_name,
            trim_children=False,
        )

    def get_outline_as_list(
        self,
        root_section_name: Optional[str] = None,
        add_hashtags: bool = False,
        include_root: bool = True,
    ) -> List[str]:
        """
        Get outline of the article as a list.

        Args:
            section_name: get all section names in pre-order travel ordering in the subtree of section_name.
                          For example:
                            #root
                            ##section1
                            ###section1.1
                            ###section1.2
                            ##section2
                          article.get_outline_as_list("section1") returns [section1, section1.1, section1.2, section2]

        Returns:
            list of section and subsection names.
        """
        if root_section_name is None:
            section_node = self.root
        else:
            section_node = self.find_section(self.root, root_section_name)
            include_root = include_root or section_node != self.root.section_name
        if section_node is None:
            return []
        result = []

        def preorder_traverse(node, level):
            prefix = (
                "#" * level if add_hashtags else ""
            )  # Adjust level if excluding root
            result.append(
                f"{prefix} {node.section_name}".strip()
                if add_hashtags
                else node.section_name
            )
            for child in node.children:
                preorder_traverse(child, level + 1)

        # Adjust the initial level based on whether root is included and hashtags are added
        if include_root:
            preorder_traverse(section_node, level=1)
        else:
            for child in section_node.children:
                preorder_traverse(child, level=1)
        return result

    def to_string(self) -> str:
        """
        Get outline of the article as a list.

        Returns:
            list of section and subsection names.
        """
        result = []

        def preorder_traverse(node, level):
            prefix = "#" * level
            result.append(f"{prefix} {node.section_name}".strip())
            result.append(node.content)
            for child in node.children:
                preorder_traverse(child, level + 1)

        # Adjust the initial level based on whether root is included and hashtags are added
        for child in self.root.children:
            preorder_traverse(child, level=1)
        result = [i.strip() for i in result if i is not None and i.strip()]
        return "\n\n".join(result)

    def reorder_reference_index(self):
        # pre-order traversal to get order of references appear in the article
        ref_indices = []

        def pre_order_find_index(node):
            if node is not None:
                if node.content is not None and node.content:
                    ref_indices.extend(
                        ArticleTextProcessing.parse_citation_indices(node.content)
                    )
                for child in node.children:
                    pre_order_find_index(child)

        pre_order_find_index(self.root)
        # constrcut index mapping
        ref_index_mapping = {}
        for ref_index in ref_indices:
            if ref_index not in ref_index_mapping:
                ref_index_mapping[ref_index] = len(ref_index_mapping) + 1

        # update content
        def pre_order_update_index(node):
            if node is not None:
                if node.content is not None and node.content:
                    node.content = ArticleTextProcessing.update_citation_index(
                        node.content, ref_index_mapping
                    )
                for child in node.children:
                    pre_order_update_index(child)

        pre_order_update_index(self.root)
        # update reference
        for url in list(self.reference["url_to_unified_index"]):
            pre_index = self.reference["url_to_unified_index"][url]
            if pre_index not in ref_index_mapping:
                del self.reference["url_to_unified_index"][url]
            else:
                new_index = ref_index_mapping[pre_index]
                self.reference["url_to_unified_index"][url] = new_index

    def get_outline_tree(self):
        def build_tree(node) -> Dict[str, Dict]:
            tree = {}
            for child in node.children:
                tree[child.section_name] = build_tree(child)
            return tree if tree else {}

        return build_tree(self.root)

    def get_first_level_section_names(self) -> List[str]:
        """
        Get first level section names
        """
        return [i.section_name for i in self.root.children]

    def get_all_section_levels(self) -> List[str]:
        """
        Get all section names that should have content generated,
        according to the hierarchical structure.
        This includes:
        1. All second-level headings if they don't have children
        2. All lowest level headings in each branch
        """
        result = []

        def traverse_tree(node, level):
            # Skip the root node
            if node == self.root:
                for child in node.children:
                    traverse_tree(child, 1)
                return

            # For first level headings (level 1)
            if level == 1:
                # If a first-level heading has no children, include it
                if not node.children:
                    result.append(node.section_name)
                # Otherwise, only traverse its children without including the first-level heading
                else:
                    for child in node.children:
                        traverse_tree(child, level + 1)
            # For second level and beyond
            else:
                # If this node has no children, it's a leaf node to include
                if not node.children:
                    result.append(node.section_name)
                # If it has children, don't include this node, only traverse down
                else:
                    for child in node.children:
                        traverse_tree(child, level + 1)

        traverse_tree(self.root, 0)
        return result

    @classmethod
    def from_outline_file(cls, topic: str, file_path: str):
        """
        Create StormArticle class instance from outline file.
        """
        outline_str = FileIOHelper.load_str(file_path)
        return StormArticle.from_outline_str(topic=topic, outline_str=outline_str)

    @classmethod
    def from_outline_str(cls, topic: str, outline_str: str):
        """
        Create StormArticle class instance from outline only string.
        """
        lines = []
        try:
            lines = outline_str.split("\n")
            lines = [line.strip() for line in lines if line.strip()]
        except:
            pass

        instance = cls(topic)
        if lines:
            # Check if the first line has hashtags and matches the topic name (case-insensitive)
            a = lines[0].startswith("#") and lines[0].replace("#", "").strip().lower()
            b = topic.lower().replace("_", " ")
            adjust_level = lines[0].startswith("#") and lines[0].replace(
                "#", ""
            ).strip().lower() == topic.lower().replace("_", " ")

            # The first line might be the title, so we skip it if it matches the topic
            if adjust_level:
                lines = lines[1:]

            node_stack = [(0, instance.root)]  # Stack to keep track of (level, node)

            for line in lines:
                level = line.count("#") - adjust_level
                section_name = line.replace("#", "").strip()

                # Ensure no periods at the end of section names when creating the article structure
                section_name = section_name.rstrip(".")

                # Skip if section name is the same as topic
                if section_name.lower() == topic.lower():
                    continue

                new_node = ArticleSectionNode(section_name)

                while node_stack and level <= node_stack[-1][0]:
                    node_stack.pop()

                node_stack[-1][1].add_child(new_node)
                node_stack.append((level, new_node))
        return instance

    def dump_outline_to_file(self, file_path):
        outline = self.get_outline_as_list(add_hashtags=True, include_root=False)

        # Check if we should remove the first element (if it appears to be a title)
        if outline and outline[0].startswith("# ") and len(outline) > 1:
            # Check if there are other first-level headings (starting with single #)
            has_other_first_level = False
            for i in range(1, len(outline)):
                if outline[i].startswith("# "):
                    has_other_first_level = True
                    break

            # If this is the only first-level heading, it might be a title - remove it
            if not has_other_first_level:
                outline = outline[1:]  # Remove the first item

        # If the file name is storm_gen_outline.txt (for revised outline),
        # we need to ensure the last line ends with a period (to check for truncation)
        if file_path.endswith("storm_gen_outline.txt") and outline:
            # Check if the last line ends with a period
            if not outline[-1].strip().endswith("."):
                # If the last line doesn't end with a period, it might be truncated - remove it
                outline = outline[:-1]

            # Add periods to each heading for WritePageOutlineFromConv to check for completeness
            outline_with_periods = [
                f"{line}." if not line.strip().endswith(".") else line
                for line in outline
            ]

            # Now remove the periods from the end of each heading for the final output
            final_outline = [line.rstrip(".") for line in outline_with_periods]

            # Write the final outline without periods
            FileIOHelper.write_str("\n".join(final_outline), file_path)
        else:
            # For other files, just write the outline as is
            FileIOHelper.write_str("\n".join(outline), file_path)

    def dump_reference_to_file(self, file_path):
        reference = copy.deepcopy(self.reference)
        for url in reference["url_to_info"]:
            reference["url_to_info"][url] = reference["url_to_info"][url].to_dict()
        FileIOHelper.dump_json(reference, file_path)

    def dump_article_as_plain_text(self, file_path):
        text = self.to_string()
        FileIOHelper.write_str(text, file_path)

    @classmethod
    def from_string(cls, topic_name: str, article_text: str, references: dict):
        article_dict = ArticleTextProcessing.parse_article_into_dict(article_text)
        article = cls(topic_name=topic_name)
        article.insert_or_create_section(article_dict=article_dict)
        for url in list(references["url_to_info"]):
            info_entry = references["url_to_info"][url]
            if isinstance(info_entry, dict):
                references["url_to_info"][url] = Information.from_dict(info_entry)

        article.reference = references
        return article

    @classmethod
    def from_article_str(
        cls, topic_name: str, article_str: str, url_to_info: dict = None
    ):
        """
        Create a StormArticle instance from article text and optional URL info.

        Args:
            topic_name (str): The topic name/title for the article
            article_str (str): The article content as a string
            url_to_info (dict, optional): URL to information dictionary

        Returns:
            StormArticle: A new article instance
        """
        article_dict = ArticleTextProcessing.parse_article_into_dict(article_str)
        article = cls(topic_name=topic_name)
        article.insert_or_create_section(article_dict=article_dict)

        # Handle references if provided
        if url_to_info:
            references = {"url_to_info": {}}
            for url, info_dict in url_to_info.items():
                if isinstance(info_dict, dict):
                    references["url_to_info"][url] = Information.from_dict(info_dict)
                else:
                    # If already an Information object, use it directly
                    references["url_to_info"][url] = info_dict
            article.reference = references

        return article

    def post_processing(self, skip_reorder_reference=False):
        self.prune_empty_nodes()
        if not skip_reorder_reference:
            self.reorder_reference_index()
