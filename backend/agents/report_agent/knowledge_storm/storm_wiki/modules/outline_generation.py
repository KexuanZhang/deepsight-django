import re
import os
import json
import logging
from typing import Union, Optional, Tuple

import dspy

from .callback import BaseCallbackHandler
from .storm_dataclass import StormInformationTable, StormArticle
from ...interface import OutlineGenerationModule
from ...utils import ArticleTextProcessing
from prompts import import_prompts

from .outline_rater import OutlineRater

logger = logging.getLogger(__name__)


class StormOutlineGenerationModule(OutlineGenerationModule):
    def __init__(self, outline_gen_lm: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        super().__init__()
        self.outline_gen_lm = outline_gen_lm
        self.write_outline = WriteOutline(engine=self.outline_gen_lm)

    def generate_outline(
        self,
        text_input: str,
        information_table: StormInformationTable,
        old_outline: Optional[StormArticle] = None,
        callback_handler: BaseCallbackHandler = None,
        return_draft_outline=False,
        topic: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Union[StormArticle, Tuple[StormArticle, StormArticle]]:
        if callback_handler is not None:
            callback_handler.on_information_organization_start()
        concatenated_dialogue_turns = sum(
            [conv for (_, conv) in information_table.conversations], []
        )
        old_outline_str = None
        if old_outline is not None:
            outline_list = old_outline.get_outline_as_list(
                add_hashtags=True, include_root=False
            )
            old_outline_str = "\n".join(outline_list)
        result = self.write_outline(
            text_input=text_input,
            dlg_history=concatenated_dialogue_turns,
            old_outline=old_outline_str,
            callback_handler=callback_handler,
            topic=topic,
            output_dir=output_dir,
        )

        # Post-process the outline to filter headings up to level 3
        outline_lines = result.outline.split("\n")
        filtered_lines = [
            line for line in outline_lines if re.match(r"^#{1,3} .+$", line.strip())
        ]
        complete_outline = "\n".join(filtered_lines)
        result.outline = complete_outline

        article_with_outline_only = StormArticle.from_outline_str(
            topic="StormReport", outline_str=result.outline
        )
        article_with_draft_outline_only = StormArticle.from_outline_str(
            topic="StormReport", outline_str=result.old_outline
        )
        if not return_draft_outline:
            return article_with_outline_only
        return article_with_outline_only, article_with_draft_outline_only


class WriteOutline(dspy.Module):
    def __init__(self, engine: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        super().__init__()
        self.draft_page_outline = dspy.Predict(WritePageOutline)
        self.write_page_outline = dspy.Predict(WritePageOutlineFromConv)
        self.engine = engine
        self.outline_rater = None

    def _normalize_heading_levels(self, outline: str) -> str:
        """
        Normalize heading levels so that the highest level headings become L1 (#),
        the second highest become L2 (##), etc.
        """
        if not outline:
            return outline

        lines = outline.split("\n")
        normalized_lines = []

        # Find the minimum heading level in the outline
        min_level = None
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                level = line.count("#")
                if min_level is None or level < min_level:
                    min_level = level

        # If no headings found or already at level 1, return as is
        if min_level is None or min_level == 1:
            return outline

        # Adjust all heading levels
        level_adjustment = min_level - 1
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                level = line.count("#")
                new_level = level - level_adjustment
                heading_text = line.lstrip("#").strip()
                normalized_line = "#" * new_level + " " + heading_text
                normalized_lines.append(normalized_line)
            else:
                normalized_lines.append(line)

        return "\n".join(normalized_lines)

    def forward(
        self,
        text_input: str,
        dlg_history,
        old_outline: Optional[str] = None,
        callback_handler: BaseCallbackHandler = None,
        topic: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        trimmed_dlg_history = [
            turn
            for turn in dlg_history
            if "topic you" not in turn.agent_utterance.lower()
            and "topic you" not in turn.user_utterance.lower()
        ]
        conv = "\n".join(
            [
                f"Report Writer: {turn.user_utterance}\nExpert: {turn.agent_utterance}"
                for turn in trimmed_dlg_history
            ]
        )
        conv = ArticleTextProcessing.remove_citations(conv)
        conv = ArticleTextProcessing.limit_word_count_preserve_newline(conv, 5000)

        # Initialize outline rater with output directory if provided
        if output_dir:
            self.outline_rater = OutlineRater(output_dir=output_dir)

        outline_score_json = None

        with dspy.settings.context(lm=self.engine):
            if old_outline is None:
                # Generate initial outline
                old_outline = ArticleTextProcessing.clean_up_outline(
                    self.draft_page_outline(text_input=text_input, topic=topic).outline
                )
                if callback_handler:
                    callback_handler.on_direct_outline_generation_end(
                        outline=old_outline
                    )

                # Rate and reorder the initial outline if rater is available
                if self.outline_rater:
                    # Normalize heading levels: ensure L1 headings start with single #
                    normalized_outline = self._normalize_heading_levels(old_outline)

                    rated_outline = self.outline_rater.rate_and_reassemble_outline(
                        outline=normalized_outline,
                        conv_history=conv,
                        text_input=text_input,
                    )

                    # Get the outline_score.json content
                    if output_dir:
                        outline_score_path = os.path.join(
                            output_dir, "outline_score.json"
                        )
                        if os.path.exists(outline_score_path):
                            try:
                                with open(
                                    outline_score_path, "r", encoding="utf-8"
                                ) as f:
                                    outline_score_json = json.dumps(
                                        json.load(f), indent=2
                                    )
                            except Exception as e:
                                logger.error(f"Error reading outline_score.json: {e}")

                    # Use the rated and reordered outline for the next step
                    old_outline = rated_outline

            # Generate final outline using conversation history and outline score if available
            if outline_score_json:
                outline = ArticleTextProcessing.clean_up_outline(
                    self.write_page_outline(
                        text_input=text_input,
                        old_outline=old_outline,
                        conv=conv,
                        topic=topic,
                        outline_score=outline_score_json,
                    ).outline
                )
            else:
                outline = ArticleTextProcessing.clean_up_outline(
                    self.write_page_outline(
                        text_input=text_input,
                        old_outline=old_outline,
                        conv=conv,
                        topic=topic,
                        outline_score="",
                    ).outline
                )

            if callback_handler:
                callback_handler.on_outline_refinement_end(outline=outline)
        return dspy.Prediction(outline=outline, old_outline=old_outline)


class WritePageOutline(dspy.Signature):
    __doc__ = import_prompts().WritePageOutline_docstring
    text_input = dspy.InputField(
        prefix="The text input (or 'N/A' if not available): ", format=str
    )
    topic = dspy.InputField(prefix="Topic to focus on:\n", format=str)
    outline = dspy.OutputField(
        prefix="Write the report outline based on the topic:\n", format=str
    )


class NaiveOutlineGen(dspy.Module):
    def __init__(self):
        super().__init__()
        self.write_outline = dspy.Predict(WritePageOutline)

    def forward(self, text_input: str):
        outline = self.write_outline(text_input=text_input).outline
        return dspy.Prediction(outline=outline)


class WritePageOutlineFromConv(dspy.Signature):
    __doc__ = import_prompts().WritePageOutlineFromConv_docstring

    text_input = dspy.InputField(
        prefix="The text input (or 'N/A' if not available): ", format=str
    )
    conv = dspy.InputField(prefix="Conversation history:\n", format=str)
    old_outline = dspy.InputField(prefix="Current draft outline:\n", format=str)
    topic = dspy.InputField(prefix="Topic to focus on:\n", format=str)
    outline_score = dspy.InputField(
        prefix="Outline section ratings (higher scores indicate more important sections):\n",
        format=str,
    )
    outline = dspy.OutputField(
        prefix="Write the tech report outline based on the topic (Use '#' for level 1 headings, '##' for level 2, '###' for level 3, and make sure every heading ends with a period):\n",
        format=str,
    )