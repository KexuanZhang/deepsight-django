import copy
import datetime
from typing import Union, Optional

import dspy

from .storm_dataclass import StormArticle
from ...interface import ArticlePolishingModule
from ...utils import ArticleTextProcessing

from prompts import import_prompts

import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
# Import image utilities and other functions directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..')))
from reports.image_utils import preserve_figure_formatting
from utils.paper_processing import format_author_affiliations


class GenerateKeySection(dspy.Signature):
    __doc__ = import_prompts().GenerateKeySection_docstring

    speakers_json = dspy.InputField(desc="包含姓名和公司的 JSON 格式发言人名单")
    section = dspy.OutputField(
        desc="包含标题 '# 关键公司与人物' 和发言人列表的格式化章节"
    )


class GenerateOverallTitle(dspy.Signature):
    __doc__ = import_prompts().GenerateOverallTitle_docstring
    article_text = dspy.InputField(desc="文章内容")
    overall_title = dspy.OutputField(desc="生成的标题，不含任何前缀或后缀")


class StormArticlePolishingModule(ArticlePolishingModule):
    def __init__(
        self,
        article_gen_lm: Union[dspy.dsp.LM, dspy.dsp.HFModel],
        article_polish_lm: Union[dspy.dsp.LM, dspy.dsp.HFModel],
    ):
        self.article_gen_lm = article_gen_lm
        self.article_polish_lm = article_polish_lm
        self.polish_page = PolishPageModule(
            write_lead_engine=self.article_gen_lm, polish_engine=self.article_polish_lm
        )
        self.generate_overall_title = dspy.Predict(GenerateOverallTitle)
        self.generated_title = None  # Store the generated title

    def polish_article(
        self,
        text_input: str,
        draft_article: StormArticle,
        recent_content_only: bool,
        speakers: str = None,
        author_json: str = None,
        remove_duplicate: bool = True,
        preserve_citation_order: bool = True,
        time_range: str = None,
        parsed_paper_title: Optional[str] = None,
    ) -> StormArticle:
        """
        Polish article, add a new first-level title at the beginning, and adjust heading levels.

        Args:
            text_input (str): User-model conversation text for generating the lead section.
            draft_article (StormArticle): Article to polish.
            recent_content_only (bool): Whether the content is limited to a specific time range (day, week, month, year).
            speakers (str): JSON-formatted string of speaker information.
            author_json (str): Path to JSON file containing author and affiliation information.
            remove_duplicate (bool): Whether to remove duplicates from the article.
            preserve_citation_order (bool): Whether to preserve the citation order.
            time_range (str): The specific time range used (day, week, month, year).
            parsed_paper_title (Optional[str]): An optional title parsed directly from a single input paper.
        """
        
        article_text = draft_article.to_string()

        # Make sure figures are properly formatted in the draft article
        article_text = preserve_figure_formatting(article_text)

        # Store the speakers section if generated
        speakers_section = None
        if speakers:
            generate_key_section = dspy.Predict(GenerateKeySection)
            with dspy.settings.context(lm=self.article_gen_lm, show_guidelines=False):
                speakers_section = generate_key_section(speakers_json=speakers).section
                article_text = f"{speakers_section}\n{article_text}"

        # Generate author and affiliations section if author_json is provided
        author_section = None
        if author_json:
            try:
                author_data = format_author_affiliations(author_json)
                author_section = f"# 作者与机构\n- {author_data['author']}\n- {author_data['affiliation']}"
                article_text = f"{author_section}\n\n{article_text}"
            except Exception as e:
                print(f"Error processing author JSON: {e}")

        polish_result = self.polish_page(
            text_input=text_input,
            draft_page=article_text,
            polish_whole_page=remove_duplicate,
        )

        lead_section = f"# 摘要\n{polish_result.lead_section}"

        other_sections = []
        for line in polish_result.page.split("\n"):
            if line.startswith("# ") or line.startswith("## "):
                # Check if this is a section we want to keep
                if (
                    "Summary" not in line.lower()
                    and "摘要" not in line.lower()
                    and "总结" not in line.lower()
                    and "关键公司与人物" not in line
                    and "作者与机构" not in line
                ):
                    section_title = line
                    section_content = []
                    other_sections.append((section_title, section_content))
            elif other_sections and line:
                other_sections[-1][1].append(line)

        final_sections = []
        # Add author section first if available
        if author_json and author_section:
            # Only include author section if author_json was provided
            final_sections.append(author_section)

        # Then add the summary section
        final_sections.append(lead_section)

        # Now add speakers section if available
        if speakers and speakers_section:
            # Only include speakers section if speakers data was provided
            final_sections.append(speakers_section)

        for section_title, section_content in other_sections:
            section_text = "\n".join([section_title] + section_content)
            final_sections.append(section_text)
        polished_article_text = "\n\n".join(final_sections)

        # Ensure figures are properly formatted in the polished article
        # Apply twice to catch any edge cases where the first application might not have caught all instances
        polished_article_text = preserve_figure_formatting(polished_article_text)
        polished_article_text = preserve_figure_formatting(polished_article_text)

        # Use parsed_paper_title if available, otherwise generate the overall title
        if parsed_paper_title:
            overall_title = parsed_paper_title.strip()
        else:
            overall_title = draft_article.root.section_name
            with dspy.settings.context(lm=self.article_polish_lm):
                overall_title_result = self.generate_overall_title(
                    article_text=polished_article_text
                )
                overall_title = overall_title_result.overall_title.strip()
        
        # Store the generated title for external access
        self.generated_title = overall_title

        current_date = datetime.date.today()
        date_str = current_date.strftime("%Y-%m-%d")
        date_bullet = f"- 搜索截止日期: {date_str}"

        if recent_content_only and time_range:
            start_date = None
            if time_range == "day":
                start_date = current_date - datetime.timedelta(days=1)
            elif time_range == "week":
                start_date = current_date - datetime.timedelta(weeks=1)
            elif time_range == "month":
                start_date = current_date - datetime.timedelta(days=30)
            elif time_range == "year":
                start_date = current_date - datetime.timedelta(days=365)

            if start_date:
                start_date_str = start_date.strftime("%Y-%m-%d")
                date_bullet = f"- 搜索日期: {start_date_str} 至 {date_str}"
            else:
                date_bullet += "（限定时间范围的内容）"
        elif recent_content_only:
            date_bullet += "（限定时间范围的内容）"

        original_article_dict = ArticleTextProcessing.parse_article_into_dict(
            polished_article_text
        )
        new_article_dict = {
            overall_title: {
                "content": date_bullet,
                "subsections": original_article_dict,
            }
        }

        polished_article = StormArticle(topic_name=draft_article.root.section_name)
        polished_article.reference = copy.deepcopy(draft_article.reference)
        polished_article.insert_or_create_section(article_dict=new_article_dict)
        polished_article.post_processing(skip_reorder_reference=preserve_citation_order)

        return polished_article


class WriteLeadSection(dspy.Signature):
    __doc__ = import_prompts().WriteLeadSection_docstring

    text_input = dspy.InputField(prefix="文本输入（或'N/A'如果不可用）: ", format=str)
    draft_page = dspy.InputField(prefix="原始草稿:\\n", format=str)
    lead_section = dspy.OutputField(prefix="撰写摘要部分:\\n", format=str)


class PolishPage(dspy.Signature):
    __doc__ = import_prompts().PolishPage_docstring

    draft_page = dspy.InputField(prefix="原始英文草稿:\n", format=str)
    page = dspy.OutputField(
        prefix="修订后的中文报告（WARNING: 必须100%保留所有HTML <img>标签，严禁删除任何图片标签！严禁删除文章中任何未重复的部分以及篡改原始引文编号顺序，必须严格保留原始 HTML <img> tag行），禁止删除或进行任何修改:\n",
        format=str,
    )


class PolishPageModule(dspy.Module):
    def __init__(
        self,
        write_lead_engine: Union[dspy.dsp.LM, dspy.dsp.HFModel],
        polish_engine: Union[dspy.dsp.LM, dspy.dsp.HFModel],
    ):
        super().__init__()
        self.write_lead_engine = write_lead_engine
        self.polish_engine = polish_engine
        self.write_lead = dspy.Predict(WriteLeadSection)
        self.polish_page = dspy.Predict(PolishPage)

    def forward(self, text_input: str, draft_page: str, polish_whole_page: bool = True):
        # Ensure figures are properly formatted in the draft page
        draft_page = preserve_figure_formatting(draft_page)

        with dspy.settings.context(lm=self.write_lead_engine, show_guidelines=False):
            lead_section = self.write_lead(
                text_input=text_input, draft_page=draft_page
            ).lead_section
            if "The lead section:" in lead_section:
                lead_section = lead_section.split("The lead section:")[1].strip()

        if polish_whole_page:
            with dspy.settings.context(lm=self.polish_engine, show_guidelines=False):
                page = self.polish_page(draft_page=draft_page).page
            # Ensure figures are properly formatted in the polished page
            page = preserve_figure_formatting(page)
        else:
            page = draft_page

        return dspy.Prediction(lead_section=lead_section, page=page)
