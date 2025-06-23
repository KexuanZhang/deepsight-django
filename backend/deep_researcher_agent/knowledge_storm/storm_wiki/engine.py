import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Union, Literal, Optional, List, Dict

import dspy

from .modules.article_generation import StormArticleGenerationModule
from .modules.article_polish import StormArticlePolishingModule
from .modules.callback import BaseCallbackHandler
from .modules.knowledge_curation import StormKnowledgeCurationModule
from .modules.outline_generation import StormOutlineGenerationModule
from .modules.persona_generator import StormPersonaGenerator
from .modules.storm_dataclass import StormInformationTable, StormArticle
from ..interface import Engine, LMConfigs, Retriever
from ..lm import LitellmModel
from ..utils import FileIOHelper, makeStringRed, truncate_filename
from prompts import import_prompts
prompts = import_prompts()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from utils.hyperlink_citations import add_hyperlinks_to_citations
from utils.paper_processing import insert_figure_images, preserve_figure_formatting


class TopicGenerator(dspy.Signature):
    __doc__ = prompts.TopicGenerator_docstring
    transcript = dspy.InputField(
        desc="Optional: Original transcript text, analyze the core theme, entities, technical terms, and high-frequency vocabulary to identify potential key content"
    )
    paper = dspy.InputField(
        desc="Optional: Original paper text, analyze the core theme, entities, technical terms, and high-frequency vocabulary to identify potential key content"
    )
    topic = dspy.InputField(
        desc="Topic to guide report generation"
    )
    improved_topic = dspy.OutputField(
        desc="Return ONLY the improved topic sentence with no additional text or formatting"
    )


class UserInputTopicImprover(dspy.Signature):
    __doc__ = prompts.UserInputTopicImprover_docstring
    topic = dspy.InputField(
        desc="Topic to guide report generation"
    )
    improved_topic = dspy.OutputField(
        desc="Return ONLY the improved topic sentence with no additional text or formatting"
    )


class TopicImprover(dspy.Module):
    def __init__(self, engine: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        super().__init__()
        self.engine = engine
        self.topic_generator = dspy.Predict(TopicGenerator)
        self.user_input_topic_improver = dspy.Predict(UserInputTopicImprover)

    def forward(self, transcript: Optional[str] = None, paper: Optional[str] = None, user_input: Optional[str] = None) -> str:
        # Maintain backward compatibility by accepting user_input but treating it as topic
        topic = user_input
        system_topic = prompts.SystemTopic_docstring

        with dspy.settings.context(lm=self.engine):
            if transcript and paper and topic:
                # Both transcript, paper, and explicit topic provided
                result = self.topic_generator(transcript=transcript, paper=paper, topic=topic)
                return result.improved_topic
            elif transcript and topic:
                # Transcript and explicit topic provided
                result = self.topic_generator(transcript=transcript, paper=None, topic=topic)
                return result.improved_topic
            elif paper and topic:
                # Paper and explicit topic provided
                result = self.topic_generator(transcript=None, paper=paper, topic=topic)
                return result.improved_topic
            elif transcript and paper:
                # Both transcript and paper provided, no explicit topic.
                result = self.topic_generator(transcript=transcript, paper=paper, topic=system_topic)
                return result.improved_topic
            elif transcript:
                # Only transcript provided
                result = self.topic_generator(transcript=transcript, paper=None, topic=system_topic)
                return result.improved_topic
            elif paper:
                # Only paper provided.
                result = self.topic_generator(transcript=None, paper=paper, topic=system_topic)
                return result.improved_topic
            elif topic:
                # Only user input topic provided
                result = self.user_input_topic_improver(topic=topic)
                return result.improved_topic
            else:
                raise ValueError("Either transcript, paper, or topic must be provided")


class STORMWikiLMConfigs(LMConfigs):
    """Configurations for LLM used in different parts of STORM."""
    def __init__(self):
        self.conv_simulator_lm = None
        self.question_asker_lm = None
        self.outline_gen_lm = None
        self.article_gen_lm = None
        self.article_polish_lm = None
        self.topic_improver_lm = None

    def init_openai_model(
        self,
        openai_api_key: str,
        azure_api_key: str,
        openai_type: Literal["openai", "azure"],
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        temperature: Optional[float] = 1.0,
        top_p: Optional[float] = 0.9,
    ):
        azure_kwargs = {
            "api_key": azure_api_key,
            "temperature": temperature,
            "top_p": top_p,
            "api_base": api_base,
            "api_version": api_version,
        }

        openai_kwargs = {
            "api_key": openai_api_key,
            "temperature": temperature,
            "top_p": top_p,
            "api_base": None,
        }
        if openai_type and openai_type == "openai":
            self.conv_simulator_lm = LitellmModel(
                model="gpt-4.1-mini", max_tokens=500, **openai_kwargs
            )
            self.question_asker_lm = LitellmModel(
                model="gpt-4.1-mini", max_tokens=500, **openai_kwargs
            )
            self.outline_gen_lm = LitellmModel(
                model="gpt-4.1", max_tokens=3000, **openai_kwargs
            )
            self.article_gen_lm = LitellmModel(
                model="gpt-4.1", max_tokens=3000, **openai_kwargs
            )
            self.article_polish_lm = LitellmModel(
                model="gpt-4.1", max_tokens=20000, **openai_kwargs
            )

        elif openai_type and openai_type == "azure":
            self.conv_simulator_lm = LitellmModel(
                model="azure/gpt-4.1-mini", max_tokens=500, **openai_kwargs
            )
            self.question_asker_lm = LitellmModel(
                model="azure/gpt-4.1-mini",
                max_tokens=500,
                **azure_kwargs,
                model_type="chat",
            )
            self.outline_gen_lm = LitellmModel(
                model="azure/gpt-4.1", max_tokens=2000, **azure_kwargs, model_type="chat"
            )
            self.article_gen_lm = LitellmModel(
                model="azure/gpt-4.1",
                max_tokens=3000,
                **azure_kwargs,
                model_type="chat",
            )
            self.article_polish_lm = LitellmModel(
                model="azure/gpt-4.1",
                max_tokens=20000,
                **azure_kwargs,
                model_type="chat",
            )

        else:
            logging.warning(
                "No valid OpenAI API provider is provided. Cannot use default LLM configurations."
            )

    def set_conv_simulator_lm(self, model: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        self.conv_simulator_lm = model

    def set_question_asker_lm(self, model: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        self.question_asker_lm = model

    def set_outline_gen_lm(self, model: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        self.outline_gen_lm = model

    def set_article_gen_lm(self, model: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        self.article_gen_lm = model

    def set_article_polish_lm(self, model: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        self.article_polish_lm = model

    def set_topic_improver_lm(self, model: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        self.topic_improver_lm = model
        



@dataclass
class STORMWikiRunnerArguments:
    output_dir: str = field(metadata={"help": "Output directory for the results."})
    max_conv_turn: int = field(default=3, metadata={"help": "Maximum number of questions in conversational question asking."})
    max_perspective: int = field(default=3, metadata={"help": "Maximum number of perspectives to consider in perspective-guided question asking."})
    max_search_queries_per_turn: int = field(default=3, metadata={"help": "Maximum number of search queries to consider in each turn."})
    disable_perspective: bool = field(default=False, metadata={"help": "If True, disable perspective-guided question asking."})
    search_top_k: int = field(default=3, metadata={"help": "Top k search results to consider for each search query."})
    initial_retrieval_k: int = field(default=150, metadata={"help": "Number of chunks to retrieve in initial phase."})
    final_context_k: int = field(default=20, metadata={"help": "Number of chunks to return after reranking."})
    max_thread_num: int = field(default=10, metadata={"help": "Maximum number of threads to use."})
    recent_content_only: bool = field(default=False, metadata={"help": "Whether search is limited to specific time range (day, week, month, year)."})
    reranker_threshold: float = field(default=0.5, metadata={"help": "Minimum score threshold for reranker results (0 to 1)."})
    time_range: Optional[str] = field(default=None, metadata={"help": "Specific time range for search results (day, week, month, year)."})


class STORMWikiRunner(Engine):
    def __init__(self, args: STORMWikiRunnerArguments, lm_configs: STORMWikiLMConfigs, rm):
        super().__init__(lm_configs=lm_configs)
        self.args = args
        self.lm_configs = lm_configs
        self.transcript: Union[None, str, List[str]] = None
        self.paper: Union[None, str, List[str]] = None
        self.speakers = None
        self.author_json = None
        self.article_title = None
        self.generated_topic = None
        self.parsed_paper_title = None
        self.figure_data: List[Dict[str, str]] = []
        self.retriever = Retriever(rm=rm, max_thread=self.args.max_thread_num)
        self.persona_generator = StormPersonaGenerator(self.lm_configs.question_asker_lm)
        self.storm_knowledge_curation_module = StormKnowledgeCurationModule(
            retriever=self.retriever,
            persona_generator=self.persona_generator,
            conv_simulator_lm=self.lm_configs.conv_simulator_lm,
            question_asker_lm=self.lm_configs.question_asker_lm,
            max_search_queries_per_turn=self.args.max_search_queries_per_turn,
            search_top_k=self.args.search_top_k,
            max_conv_turn=self.args.max_conv_turn,
            max_thread_num=self.args.max_thread_num
        )
        self.storm_outline_generation_module = StormOutlineGenerationModule(
            outline_gen_lm=self.lm_configs.outline_gen_lm
        )
        self.storm_article_generation = StormArticleGenerationModule(
            article_gen_lm=self.lm_configs.article_gen_lm,
            max_thread_num=self.args.max_thread_num,
            reranker_model_name="cross-encoder/ms-marco-MiniLM-L6-v2",
            initial_retrieval_k=self.args.initial_retrieval_k,
            final_context_k=self.args.final_context_k,
            reranker_threshold=self.args.reranker_threshold
        )
        self.storm_article_polishing_module = StormArticlePolishingModule(
            article_gen_lm=self.lm_configs.article_gen_lm,
            article_polish_lm=self.lm_configs.article_polish_lm
        )
        self.topic_improver = TopicImprover(self.lm_configs.topic_improver_lm)
        self.lm_configs.init_check()
        self.apply_decorators()

    def _get_formatted_inputs(self) -> str:
        """Formats the transcript(s) and paper(s) for use in modules.
        Returns 'N/A' if no transcript and no paper.
        Returns formatted string for transcript(s) and/or paper(s).
        """
        parts = []
        if self.transcript:
            if isinstance(self.transcript, str):
                parts.append(f"=== Transcript 1 ===\\n{self.transcript}")
            elif isinstance(self.transcript, list):
                if not self.transcript: # Empty list
                    pass
                elif len(self.transcript) == 1:
                    parts.append(f"=== Transcript 1 ===\\n{self.transcript[0]}")
                else:
                    for i, content in enumerate(self.transcript):
                        parts.append(f"=== Transcript {i+1} ===\\n{content}")
        
        if self.paper:
            if isinstance(self.paper, str):
                parts.append(f"=== Paper 1 ===\\n{self.paper}")
            elif isinstance(self.paper, list):
                if not self.paper: # Empty list
                    pass
                elif len(self.paper) == 1:
                    parts.append(f"=== Paper 1 ===\\n{self.paper[0]}")
                else:
                    for i, content in enumerate(self.paper):
                        parts.append(f"=== Paper {i+1} ===\\n{content}")

        if not parts:
            return "N/A"
        return "\\n\\n".join(parts)

    def _get_considered_personas(self, combined_input_content: str, max_num_persona, topic: Optional[str] = None, old_outline: Optional[str] = None) -> List[str]:
        # Method signature changed to accept combined_input_content
        # The persona_generator might need to be aware of the structure "=== Transcript X ===" vs "=== Paper Y ==="
        # For now, passing the combined content.
        return self.persona_generator.generate_persona(transcript=combined_input_content, max_num_persona=max_num_persona, topic=topic, old_outline=old_outline)

    def run_knowledge_curation_module(self, ground_truth_url: str = "None", callback_handler: BaseCallbackHandler = None, topic: Optional[str] = None, old_outline: Optional[str] = None) -> StormInformationTable:
        combined_input_content = self._get_formatted_inputs()
        (information_table, conversation_log) = self.storm_knowledge_curation_module.research(
            transcript=combined_input_content, 
            ground_truth_url=ground_truth_url,
            callback_handler=callback_handler,
            max_perspective=self.args.max_perspective,
            disable_perspective=False, 
            return_conversation_log=True,
            topic=topic,
            old_outline=old_outline
        )
        FileIOHelper.dump_json(conversation_log, os.path.join(self.article_output_dir, "conversation_log.json"))
        information_table.dump_url_to_info(os.path.join(self.article_output_dir, "raw_search_results.json"))
        return information_table

    def run_outline_generation_module(self, information_table: StormInformationTable, old_outline: Optional[StormArticle] = None, callback_handler: BaseCallbackHandler = None, topic: Optional[str] = None) -> StormArticle:
        combined_input_content = self._get_formatted_inputs()
        outline, draft_outline = self.storm_outline_generation_module.generate_outline(
            transcript=combined_input_content,
            information_table=information_table,
            old_outline=old_outline,
            return_draft_outline=True,
            callback_handler=callback_handler,
            topic=topic,
            output_dir=self.article_output_dir
        )
        outline.dump_outline_to_file(os.path.join(self.article_output_dir, "storm_gen_outline.txt"))
        if old_outline is None:
            draft_outline.dump_outline_to_file(os.path.join(self.article_output_dir, "direct_gen_outline.txt"))
        else:
            old_outline.dump_outline_to_file(os.path.join(self.article_output_dir, "provided_outline.txt"))
        return outline

    def run_article_generation_module(self, outline: StormArticle, information_table: StormInformationTable, topic: str, callback_handler: BaseCallbackHandler = None) -> StormArticle:
        combined_input_content = self._get_formatted_inputs()

        draft_article = self.storm_article_generation.generate_article(
            transcript=combined_input_content, 
            information_table=information_table,
            article_with_outline=outline,
            callback_handler=callback_handler,
            topic=topic,
            figure_data=self.figure_data
        )

        # Insert figure images and captions into the draft article
        if self.figure_data and isinstance(self.figure_data, list) and len(self.figure_data) > 0:
            article_text_before_figs = draft_article.to_string()
            original_references = draft_article.reference # Preserve references
            
            modified_text_with_figs = insert_figure_images(
                article_content=article_text_before_figs, 
                figures=self.figure_data, 
                reorder=False 
            )
            
            # Apply figure formatting preservation to ensure proper newlines around figures
            modified_text_with_figs = preserve_figure_formatting(modified_text_with_figs)
            
            # Re-create the StormArticle object from the modified text
            # 'topic' here is self.generated_topic, which is the main topic for the article.
            draft_article = StormArticle.from_string(
                topic_name=topic, 
                article_text=modified_text_with_figs,
                references=original_references
            )
            logging.info("Figure images and captions inserted and article structure updated.")
        else:
            logging.info("No figure data available or figure_data is not a non-empty list, skipping figure image insertion.")

        # Ensure the article content has proper formatting before saving to file
        article_content = draft_article.to_string()
        article_content = preserve_figure_formatting(article_content)
        
        # Save with preserved formatting
        with open(os.path.join(self.article_output_dir, "storm_gen_article.md"), 'w', encoding='utf-8') as f:
            f.write(article_content)
            
        # Still keep the original function call for compatibility
        draft_article.dump_reference_to_file(os.path.join(self.article_output_dir, "url_to_info.json"))
        return draft_article

    def run_article_polishing_module(
        self,
        draft_article: StormArticle,
        recent_content_only: bool,
        speakers: Optional[str] = None,
        author_json: Optional[str] = None,
        remove_duplicate: bool = False,
        preserve_citation_order: bool = True,
        time_range: Optional[str] = None
    ) -> StormArticle:
        combined_input_content = self._get_formatted_inputs()
        
        polished_article = self.storm_article_polishing_module.polish_article(
            transcript=combined_input_content, 
            draft_article=draft_article,
            recent_content_only=recent_content_only,
            speakers=speakers or self.speakers,
            author_json=author_json or self.author_json,
            remove_duplicate=remove_duplicate,
            preserve_citation_order=preserve_citation_order,
            time_range=time_range,
            parsed_paper_title=self.parsed_paper_title
        )
        
        article_content_str = polished_article.to_string()
        reference_data = polished_article.reference
        
        # Apply formatting preservation before adding hyperlinks
        article_content_str = preserve_figure_formatting(article_content_str)
        
        hyperlinked_content_str = add_hyperlinks_to_citations(article_content_str, reference_data)
        
        # Apply formatting preservation again in case hyperlink process affected formatting
        hyperlinked_content_str = preserve_figure_formatting(hyperlinked_content_str)
        # Apply a second time to catch any edge cases
        hyperlinked_content_str = preserve_figure_formatting(hyperlinked_content_str)
        
        FileIOHelper.write_str(hyperlinked_content_str, os.path.join(self.article_output_dir, "storm_gen_article_polished.md"))
        return polished_article

    def post_run(self):
        config_log = self.lm_configs.log()
        FileIOHelper.dump_json(config_log, os.path.join(self.article_output_dir, "run_config.json"))
        llm_call_history = self.lm_configs.collect_and_reset_lm_history()
        with open(os.path.join(self.article_output_dir, "llm_call_history.jsonl"), "w") as f:
            for call in llm_call_history:
                if "kwargs" in call:
                    call.pop("kwargs")
                f.write(json.dumps(call) + "\n")

    def _load_information_table_from_local_fs(self, information_table_local_path):
        assert os.path.exists(information_table_local_path), makeStringRed(f"{information_table_local_path} not exists.")
        return StormInformationTable.from_conversation_log_file(information_table_local_path)

    def _load_outline_from_local_fs(self, outline_local_path):
        assert os.path.exists(outline_local_path), makeStringRed(f"{outline_local_path} not exists.")
        # combined_input_content = self._get_formatted_inputs() # Potentially needed if StormArticle.from_outline_file uses it
        topic_name = self.generated_topic or self.article_title or "Unknown Topic"
        return StormArticle.from_outline_file(topic=topic_name, file_path=outline_local_path)

    def _load_draft_article_from_local_fs(self, draft_article_path, url_to_info_path):
        assert os.path.exists(draft_article_path), makeStringRed(f"{draft_article_path} not exists.")
        assert os.path.exists(url_to_info_path), makeStringRed(f"{url_to_info_path} not exists.")
        # combined_input_content = self._get_formatted_inputs() # Not directly used by StormArticle.from_string
        article_text = FileIOHelper.load_str(draft_article_path)
        references = FileIOHelper.load_json(url_to_info_path)
        topic_name = self.generated_topic or self.article_title or "Unknown Topic"
        return StormArticle.from_string(topic_name=topic_name, article_text=article_text, references=references)

    def run(
        self,
        user_input: Optional[str] = None,
        ground_truth_url: str = "",
        do_research: bool = True,
        do_generate_outline: bool = True,
        do_generate_article: bool = True,
        do_polish_article: bool = True,
        remove_duplicate: bool = True,
        callback_handler: BaseCallbackHandler = BaseCallbackHandler(),
        old_outline_path: Optional[str] = None,
        skip_rewrite_outline: bool = False
    ) -> None:
        assert (do_research or do_generate_outline or do_generate_article or do_polish_article), makeStringRed("No action is specified.")
        if self.transcript is None and self.paper is None and user_input is None: # Check all three
            raise ValueError("Either transcript, paper, or topic must be provided.")

        original_topic = user_input
        if original_topic:
            print("Original topic provided. Improving topic.")
        
        # Prepare transcript and paper for TopicImprover
        # _get_formatted_inputs returns "N/A" if empty, TopicImprover expects None.
        formatted_transcript_for_improver = None
        if self.transcript:
            if isinstance(self.transcript, str):
                formatted_transcript_for_improver = self.transcript
            elif isinstance(self.transcript, list) and self.transcript:
                formatted_transcript_for_improver = "\\n\\n".join(self.transcript)


        formatted_paper_for_improver = None
        if self.paper:
            if isinstance(self.paper, str):
                formatted_paper_for_improver = self.paper
            elif isinstance(self.paper, list) and self.paper:
                formatted_paper_for_improver = "\\n\\n".join(self.paper)


        try:
            improved_topic = self.topic_improver(
                transcript=formatted_transcript_for_improver,
                paper=formatted_paper_for_improver,
                user_input=original_topic
            )
            print(f"Improved topic: {improved_topic}")
            self.generated_topic = improved_topic
        except Exception as e:
            logging.warning(f"Failed to improve topic: {e}")
            improved_topic = original_topic # Fallback to original if provided
            self.generated_topic = original_topic
            # If original_topic was None and improvement failed, generated_topic is None
            # The TopicImprover itself should raise error if all inputs are None.
            if not self.generated_topic and (formatted_transcript_for_improver or formatted_paper_for_improver):
                 logging.error("Topic could not be generated from transcript/paper and no user topic was provided.")
                 # Set a default or re-raise based on how TopicImprover is expected to behave.
                 # If it returns None silently, we need a fallback.
                 # Using a placeholder if all fails.
                 self.generated_topic = "Default Topic - Check Inputs"

        if not self.generated_topic:
            # This case occurs if user_input was None, and topic improvement (extraction) also resulted in None or failed.
            # TopicImprover should ideally handle the "no input" case by raising ValueError.
            # If it somehow returns None when it should have content, this is a fallback.
            if formatted_transcript_for_improver and not formatted_paper_for_improver:
                logging.warning("Topic improvement returned None, attempting to use a generic topic from transcript.")
                # This implies topic extraction logic from transcript alone inside TopicImprover needs to be robust.
                # Forcing a re-attempt or using a placeholder.
                # This path should ideally not be hit if TopicImprover is robust.
                self.generated_topic = "Topic derived from transcript"
            elif formatted_paper_for_improver and not formatted_transcript_for_improver:
                logging.warning("Topic improvement returned None, attempting to use a generic topic from paper.")
                self.generated_topic = "Topic derived from paper"
            elif formatted_paper_for_improver and formatted_transcript_for_improver:
                logging.warning("Topic improvement returned None, attempting to use a generic topic from transcript and paper.")
                self.generated_topic = "Topic derived from transcript and paper"
            else:
                 # This means transcript, paper, and user_input were all None initially, which TopicImprover should have caught.
                 # Or, topic_improver returned None despite having transcript/paper.
                logging.error("Generated topic is critically missing and could not be derived. Check TopicImprover logic and inputs.")
                raise ValueError("Failed to determine a topic for the report. All inputs (topic, transcript, paper) might be missing or topic generation failed.")
        
        if not hasattr(self, 'article_dir_name') or not self.article_dir_name:
            if not self.article_title:
                self.article_title = self.generated_topic if self.generated_topic else "Untitled_Report"
            self.article_dir_name = truncate_filename(self.article_title.replace(" ", "_").replace("/", "_"))
        
        self.article_output_dir = os.path.join(self.args.output_dir, self.article_dir_name)
        os.makedirs(self.article_output_dir, exist_ok=True)

        old_outline = None
        old_outline_str = None
        if old_outline_path:
            # Pass the determined topic name when loading outline
            old_outline = self._load_outline_from_local_fs(old_outline_path)
            old_outline_str = "\n".join(old_outline.get_outline_as_list(add_hashtags=True, include_root=False)) if old_outline else None

        information_table = None
        if do_research:
            information_table = self.run_knowledge_curation_module(ground_truth_url=ground_truth_url, callback_handler=callback_handler, topic=self.generated_topic, old_outline=old_outline_str)
        outline = None
        if do_generate_outline:
            if information_table is None:
                information_table = self._load_information_table_from_local_fs(os.path.join(self.article_output_dir, "conversation_log.json"))
            outline = self.run_outline_generation_module(information_table=information_table, old_outline=old_outline, callback_handler=callback_handler, topic=self.generated_topic)
        draft_article = None
        if do_generate_article:
            if information_table is None:
                information_table = self._load_information_table_from_local_fs(os.path.join(self.article_output_dir, "conversation_log.json"))
            if outline is None:
                outline = self._load_outline_from_local_fs(os.path.join(self.article_output_dir, "storm_gen_outline.txt"))
            draft_article = self.run_article_generation_module(
                outline=outline,
                information_table=information_table,
                topic=self.generated_topic, # Pass self.generated_topic as topic
                callback_handler=callback_handler
            )
        if do_polish_article:
            if draft_article is None:
                draft_article_path = os.path.join(self.article_output_dir, "storm_gen_article.md")
                url_to_info_path = os.path.join(self.article_output_dir, "url_to_info.json")
                draft_article = self._load_draft_article_from_local_fs(draft_article_path=draft_article_path, url_to_info_path=url_to_info_path)
            self.run_article_polishing_module(
                draft_article=draft_article,
                recent_content_only=self.args.recent_content_only,
                speakers=self.speakers,
                author_json=self.author_json,
                remove_duplicate=remove_duplicate,
                preserve_citation_order=True,
                time_range=self.args.time_range
            )