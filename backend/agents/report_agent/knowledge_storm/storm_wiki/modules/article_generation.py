import concurrent.futures
import copy
import logging
from concurrent.futures import as_completed
from typing import List, Union, Dict, Any, Optional
from sentence_transformers import CrossEncoder
import dspy
import re
import torch
import threading
from .callback import BaseCallbackHandler
from .storm_dataclass import StormInformationTable, StormArticle
from ...interface import ArticleGenerationModule, Information
from ...utils import ArticleTextProcessing
from .enhanced_rag import EnhancedStormInformationTable
from prompts import import_prompts

import json


def get_device():
    """Detect the best available device: 'cuda', 'mps', or 'cpu'."""
    if torch.cuda.is_available():
        return "cuda"
    # if torch.backends.mps.is_available() and torch.backends.mps.is_built():
    #     return "mps"
    return "cpu"


class QueryRewrite(dspy.Signature):
    __doc__ = import_prompts().QueryRewrite_docstring
    queries = dspy.InputField(
        description="List of search queries to rewrite", format=list
    )
    rewritten_queries = dspy.OutputField(
        description="Rewritten search queries, one per line, without any prefix or suffix:"
    )


def filter_queries(raw_output):
    """
    Filters out prefixes like 'Rewritten Queries:' in various formats from a raw string
    and returns a list of actual queries while preserving the original formatting.

    Args:
        raw_output (str): The raw string containing queries, possibly with prefixes.

    Returns:
        list: A list of cleaned queries with prefixes removed but original formatting preserved.
    """
    # Store the original lines for later reference to preserve formatting
    original_lines = raw_output.split("\n")
    # Create lowercase version for case-insensitive matching
    lowercase_lines = [line.lower() for line in original_lines]

    prefix_pattern = re.compile(r"^\s*rewritten\s+queries:\s*", re.IGNORECASE)
    actual_queries = []

    for i, (orig_line, lower_line) in enumerate(zip(original_lines, lowercase_lines)):
        # Strip whitespace but keep for later to preserve indentation
        orig_stripped = orig_line.strip()
        lower_stripped = lower_line.strip()

        # Skip empty lines
        if not orig_stripped:
            continue

        # Skip lines that match the prefix pattern
        if prefix_pattern.match(lower_stripped):
            continue

        # If the line contains a colon, it might be a label or prefix
        if (
            ":" in lower_stripped
            and "rewritten queries" in lower_stripped.split(":", 1)[0]
        ):
            # Extract the part after the first colon from the original string to preserve formatting
            colon_index = orig_stripped.find(":")
            query_part = orig_stripped[colon_index + 1 :].strip()
            if query_part:  # Only add non-empty query parts
                actual_queries.append(query_part)
        else:
            # If no matching prefix, assume the entire line is the query
            actual_queries.append(orig_stripped)

    # Final filter to remove any lines containing "rewritten queries" that might have been missed
    final_queries = []
    for query in actual_queries:
        if "rewritten queries" not in query.lower():
            final_queries.append(query)

    return final_queries


class StormArticleGenerationModule(ArticleGenerationModule):
    """
    The interface for article generation stage. Given topic, collected information from
    knowledge curation stage, generated outline from outline generation stage.
    """

    def __init__(
        self,
        article_gen_lm: Union[dspy.dsp.LM, dspy.dsp.HFModel],
        max_thread_num: int = 10,
        reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2",
        rerank_top_k: int = None,
        initial_retrieval_k: int = 150,
        final_context_k: int = 20,
        reranker_threshold: float = 0.5,
    ):
        super().__init__()
        self.initial_retrieval_k = initial_retrieval_k
        self.final_context_k = final_context_k
        self.article_gen_lm = article_gen_lm
        self.max_thread_num = max_thread_num
        self.section_gen = ConvToSection(article_gen_lm)
        self._predict_lock = threading.Lock()
        device = get_device()
        self.reranker = CrossEncoder(
            reranker_model_name,
            device=device,
            activation_fn=torch.nn.Sigmoid(),
            trust_remote_code=True,
        )
        self.rerank_top_k = rerank_top_k
        self.query_logger = None
        self.query_rewrite = dspy.Predict(QueryRewrite)
        self.reranker_threshold = reranker_threshold

    def generate_section(
        self,
        text_input: str,
        section_name: str,
        information_table: StormInformationTable,
        section_outline: str,
        section_query: list[str],
        topic: str,
        figure_data: Optional[List[Dict[str, str]]] = None,
    ) -> dict:
        """
        Generate a section using the enhanced RAG pipeline with contextual snippets,
        hybrid retrieval, and reranking.
        """
        logging.info(f"Generating section '{section_name}' using enhanced RAG pipeline")

        # Convert the standard information table to enhanced table if needed
        if not isinstance(information_table, EnhancedStormInformationTable):
            logging.info("Converting standard information table to enhanced table")
            enhanced_table = EnhancedStormInformationTable(
                reranker_threshold=self.reranker_threshold
            ).from_standard_table(information_table)

            # Prepare the table for retrieval
            enhanced_table.prepare_table_for_retrieval()
        else:
            enhanced_table = information_table

        # Rewrite the queries to improve retrieval
        logging.info(f"Original search queries: {section_query}")
        with dspy.settings.context(lm=self.article_gen_lm):
            rewritten_queries_str = self.query_rewrite(
                queries=section_query
            ).rewritten_queries
            # Use filter_queries to clean the rewritten queries
            rewritten_queries = filter_queries(rewritten_queries_str)
        logging.info(f"Rewritten search queries: {rewritten_queries}")

        # Perform hybrid retrieval with vector search and BM25
        collected_info = enhanced_table.retrieve_information(
            queries=rewritten_queries,
            initial_retrieval_k=self.initial_retrieval_k,
            final_context_k=self.final_context_k,
            query_logger=self.query_logger,
        )

        # Log results
        logging.info(
            f"Retrieved {len(collected_info)} information objects for section {section_name}"
        )
        for j, info in enumerate(collected_info[:5], start=1):
            logging.info(f"    [EnhancedRAG:{j}] URL={info.url}  Title={info.title}")

        # Call the LLM to generate the section content
        output = self.section_gen(
            text_input=text_input,
            outline=section_outline,
            section=section_name,
            collected_info=collected_info,
            topic=topic,
            figure_data=figure_data,
        )

        return {
            "section_name": section_name,
            "section_content": output.section,
            "collected_info": collected_info,
        }

    def generate_article(
        self,
        text_input: str,
        information_table: StormInformationTable,
        article_with_outline: StormArticle,
        callback_handler: BaseCallbackHandler = None,
        topic: str = None,
        figure_data: Optional[List[Dict[str, str]]] = None,
    ) -> StormArticle:
        """
        Generate article for the topic based on the information table and article outline.

        Args:
            text_input (str): The text content.
            information_table (StormInformationTable): The information table containing the collected information.
            article_with_outline (StormArticle): The article with specified outline.
            callback_handler (BaseCallbackHandler): An optional callback handler. Defaults to None.
            topic (str): The topic of the article.
            figure_data (Optional[List[Dict[str, str]]]): The figure data for the article.
        """
        if topic is None:
            raise ValueError("Topic must be provided for article generation.")

        # If using enhanced RAG, prepare the enhanced information table
        if not isinstance(information_table, EnhancedStormInformationTable):
            logging.info(
                "Converting to enhanced information table for article generation"
            )
            enhanced_table = EnhancedStormInformationTable().from_standard_table(
                information_table
            )

            enhanced_table.prepare_table_for_retrieval()
            information_table = enhanced_table
        else:
            information_table.prepare_table_for_retrieval()

        if article_with_outline is None:
            # If no outline provided, create a basic article object.
            article_with_outline = StormArticle(topic_name=topic)  # Use topic for name
            logging.warning(
                "No outline provided to generate_article. Proceeding with an empty structure."
            )

        # Define a function to collect sections that have leaf subheadings
        def get_sections_with_leaf_subheadings(node, parent_headings=None):
            if parent_headings is None:
                parent_headings = []
            section_data = []
            # Ensure node.section_name is a string before proceeding
            if not isinstance(node.section_name, str):
                logging.error(
                    f"Node section_name is not a string: {node.section_name}. Skipping node."
                )
                return section_data

            current_headings = parent_headings + [node.section_name]
            subheadings = [
                child.section_name
                for child in node.children
                if isinstance(child.section_name, str)
            ]  # Filter non-string names
            # is_leaf = len(subheadings) == 0

            # Check if the current node has leaf children
            leaf_children = [
                child
                for child in node.children
                if len(child.children) == 0 and isinstance(child.section_name, str)
            ]
            if leaf_children:  # Check if there are any leaf children
                section_data.append(
                    {
                        "section_name": node.section_name,
                        "parent_headings": parent_headings,
                        "full_path_text": " -> ".join(current_headings),
                        "leaf_subheadings": [
                            child.section_name for child in leaf_children
                        ],  # Get names of leaf children
                    }
                )

            # Recurse into non-leaf children
            for child in node.children:
                if len(child.children) > 0:  # Only recurse if the child is not a leaf
                    section_data.extend(
                        get_sections_with_leaf_subheadings(child, current_headings)
                    )
            return section_data

        # Helper function to recursively collect all leaf headings at the deepest level
        def get_all_deepest_leaf_headings(node):
            if not node.children:
                return [node.section_name] if isinstance(node.section_name, str) else []

            deepest_leaves = []
            for child in node.children:
                child_leaves = get_all_deepest_leaf_headings(child)
                deepest_leaves.extend(child_leaves)

            return deepest_leaves

        # Helper function to get all headings from level 1 to the deepest for a section
        def get_all_hierarchy_headings(node, include_self=True):
            headings = []
            if include_self and isinstance(node.section_name, str):
                headings.append(node.section_name)

            for child in node.children:
                if isinstance(child.section_name, str):
                    headings.append(child.section_name)
                    # Get headings from deeper levels
                    if child.children:
                        for descendant in child.children:
                            # For each descendant, add its name and its deepest leaves
                            if isinstance(descendant.section_name, str):
                                headings.append(descendant.section_name)
                            headings.extend(get_all_deepest_leaf_headings(descendant))

            return headings

        # Collect all potential sections first (original logic)
        all_potential_sections = []
        for child in article_with_outline.root.children:  # Starts at Level 1
            all_potential_sections.extend(
                get_sections_with_leaf_subheadings(
                    child, [article_with_outline.root.section_name]
                )
            )  # Pass root name as initial parent

        # Check the maximum heading level in the outline
        max_heading_level = 0
        for level in article_with_outline.get_all_section_levels():
            max_heading_level = max(max_heading_level, len(level.split("->")))

        # Filter sections based on the maximum outline depth
        sections_to_process = []
        if max_heading_level <= 2:  # If outline only has level 1 and 2 headings
            # For 2-level outlines, process all level 1 sections that have children
            for child in article_with_outline.root.children:
                if child.children and isinstance(child.section_name, str):
                    sections_to_process.append(
                        {
                            "section_name": child.section_name,
                            "parent_headings": [article_with_outline.root.section_name],
                            "full_path_text": f"{article_with_outline.root.section_name} -> {child.section_name}",
                            "leaf_subheadings": [
                                c.section_name
                                for c in child.children
                                if isinstance(c.section_name, str)
                            ],
                        }
                    )
        else:
            # Original logic for 3-level outlines - process sections at Level 2 or deeper with leaf children
            sections_to_process = [
                section_data
                for section_data in all_potential_sections
                if len(section_data["parent_headings"])
                >= 2  # Check if depth is >= 2 (root is level 0)
            ]

        if not sections_to_process:
            logging.warning(
                "No sections identified for content generation based on the outline structure and leaf node criteria."
            )

        # Generate content for these sections
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_thread_num
        ) as executor:
            future_to_section = {}
            for section_data in sections_to_process:
                section_title = section_data["section_name"]
                parent_headings = section_data["parent_headings"]
                leaf_subheadings = section_data["leaf_subheadings"]

                # Find the section node to get all headings
                section_node = article_with_outline.find_section(
                    article_with_outline.root, section_title
                )

                # Always include the section_title in the query
                section_query = [section_title]

                if len(parent_headings) == 1:  # Level 1 section (root is level 0)
                    # Get all headings from this section down to the deepest level
                    section_query.extend(
                        get_all_hierarchy_headings(section_node, include_self=False)
                    )
                else:
                    # For deeper level sections, include both the section title and its leaf subheadings
                    section_query.extend(leaf_subheadings)
                    # Also include any deeper headings if they exist
                    section_query.extend(get_all_deepest_leaf_headings(section_node))

                # Remove any duplicates while preserving order
                section_query = list(dict.fromkeys(section_query))

                # Construct the section outline snippet passed to the LLM
                current_level = len(
                    parent_headings
                )  # Level relative to root (root is level 0)
                queries_with_hashtags = [f"{'#' * current_level} {section_title}"]
                for subheading in leaf_subheadings:
                    queries_with_hashtags.append(
                        f"{'#' * (current_level + 1)} {subheading}"
                    )
                section_outline = "\n".join(queries_with_hashtags)

                # Submit section generation task
                future = executor.submit(
                    self.generate_section,
                    text_input,
                    section_title,
                    information_table,
                    section_outline,
                    section_query,
                    topic,
                    figure_data,
                )
                future_to_section[future] = section_data

            section_output_dict_collection = []
            for future in as_completed(future_to_section):
                try:
                    section_output_dict = future.result()
                    section_data = future_to_section[future]
                    # Get the immediate parent name for structure update
                    parent_section_name = (
                        section_data["parent_headings"][-1]
                        if section_data["parent_headings"]
                        else article_with_outline.root.section_name
                    )
                    section_output_dict["parent_section_name"] = parent_section_name
                    section_output_dict_collection.append(section_output_dict)
                except Exception as e:
                    logging.error(
                        f"Error processing section generation future: {e}",
                        exc_info=True,
                    )

        # Update the article with generated content
        article = copy.deepcopy(article_with_outline)
        for section_output_dict in section_output_dict_collection:
            parent_section_name = section_output_dict["parent_section_name"]
            # Ensure parent_section_name is valid before updating
            if article.find_section(article.root, parent_section_name):
                article.update_section(
                    parent_section_name=parent_section_name,
                    current_section_content=section_output_dict["section_content"],
                    current_section_info_list=section_output_dict["collected_info"],
                )
            else:
                logging.warning(
                    f"Parent section '{parent_section_name}' not found for section '{section_output_dict['section_name']}'. Skipping update."
                )

        article.post_processing()
        return article


class ConvToSection(dspy.Module):
    """Use the information collected from the information-seeking conversation to write a section."""

    def __init__(self, engine: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        super().__init__()
        self.write_section = dspy.Predict(WriteSection)
        self.engine = engine

    def forward(
        self,
        text_input: str,
        outline: str,
        section: str,
        collected_info: List[Information],
        topic: str,
        figure_data: Optional[List[Dict[str, str]]] = None,
    ):
        info = ""
        if collected_info:  # Check if collected_info is not empty
            for idx, storm_info in enumerate(collected_info):
                # Ensure snippets is a list and not empty before joining
                snippets_text = (
                    "\n".join(storm_info.snippets)
                    if storm_info.snippets
                    else "No snippets available."
                )
                info += f"[{idx + 1}]\n" + snippets_text + "\n\n"
            info = ArticleTextProcessing.limit_word_count_preserve_newline(info, 5000)
        else:
            info = "No information collected for this section."  # Provide default text if no info

        figure_data_str = "N/A"
        if figure_data:
            try:
                figure_data_str = json.dumps(
                    figure_data, indent=2
                )  # Convert list of dicts to JSON string
            except TypeError:
                figure_data_str = str(
                    figure_data
                )  # Fallback to simple string conversion if JSON fails

        with dspy.settings.context(lm=self.engine):
            section_content = ArticleTextProcessing.clean_up_section(
                self.write_section(
                    text_input=text_input,
                    info=info,
                    section=section,
                    outline=outline,
                    topic=topic,
                    figure_data=figure_data_str,
                ).output  # Pass figure_data_str
            )
            # Trim to the last complete sentence
            matches = list(re.finditer(r"[.!?](?=\s|$)", section_content))
            if matches:
                last_punct = matches[-1].end()
                section_content = section_content[:last_punct]

        return dspy.Prediction(section=section_content)


class WriteSection(dspy.Signature):
    __doc__ = import_prompts().WriteSection_docstring

    text_input = dspy.InputField(
        prefix="text(or 'N/A' if not available):\n", format=str
    )
    info = dspy.InputField(prefix="collected information:\n", format=str)
    section = dspy.InputField(prefix="You need to write the section:\n", format=str)
    outline = dspy.InputField(prefix="Outline:\n", format=str)
    topic = dspy.InputField(prefix="The topic of the report:\n", format=str)
    figure_data = dspy.InputField(
        prefix="Available figures (list of dictionaries with 'figure_id', 'caption', or 'N/A' if no figures):\n",
        format=str,
        optional=True,
    )
    output = dspy.OutputField(
        prefix="When writing, use the correct inline citations (e.g., [1][2] for web sources) to write the section:\n",
        format=str,
    )
