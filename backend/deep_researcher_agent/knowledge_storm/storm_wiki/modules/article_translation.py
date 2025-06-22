import copy
from typing import Union

import dspy

from .storm_dataclass import StormArticle
from ...utils import ArticleTextProcessing


class TranslateText(dspy.Signature):
    """Translate the following technical text from English to Chinese.
    Preserve the meaning, tone, and nuance of the original text.
    Maintain proper grammar, spelling, and punctuation.
    Keep professional terms, company names, and personal names in their original language.
    For specialized terms, provide Chinese translations in parentheses if needed.
    Preserve all formatting, including bullet points, numbering, and paragraph structure.
    Maintain all inline citations (e.g., [1], [2]) in their original positions.
    Return ONLY the translated text, without any comments, prefixes or explanatory text.
    """

    english_text = dspy.InputField(prefix="English text to translate:\n", format=str)
    chinese_text = dspy.OutputField(prefix="", format=str)


class TranslateModule(dspy.Module):
    """Module to translate text from English to Chinese."""
    
    def __init__(self, engine: dspy.LM):
        super().__init__()
        self.translate = dspy.Predict(TranslateText)
        self.engine = engine
        
    def forward(self, english_text: str):
        with dspy.settings.context(lm=self.engine):
            result = self.translate(english_text=english_text)
            return dspy.Prediction(chinese_text=result.chinese_text)


class ArticleTranslationModule:
    """
    Module for translating articles from English to Chinese.
    This module runs after article polishing to translate the final article using a single translator.
    """

    def __init__(
        self,
        translation_lm: dspy.LM,
    ):
        self.translation_lm = translation_lm
        self.translator = TranslateModule(engine=self.translation_lm)

    def translate_article(
        self, english_article: StormArticle
    ) -> StormArticle:
        """
        Translate an article from English to Chinese.

        Args:
            english_article (StormArticle): The English article to translate.

        Returns:
            StormArticle: The translated Chinese article.
        """
        try:
            article_text = english_article.to_string()
            if not article_text.strip():
                return english_article

            sections = ArticleTextProcessing.parse_article_into_dict(article_text)
            translated_sections = {}
            for section_name, section_content in sections.items():
                # Always translate the section name (heading)
                translated_section_name = self.translator(english_text=section_name).chinese_text
                if isinstance(section_content, dict):
                    translated_subsections = {}
                    for key, value in section_content.items():
                        if key == "content" and isinstance(value, str):
                            # Only translate content if it's non-empty
                            if value.strip():
                                translated_content = self.translator(english_text=value).chinese_text
                            else:
                                translated_content = value  # Keep empty content as is
                            translated_subsections[key] = translated_content
                        elif key == "subsections" and isinstance(value, dict):
                            # Recursively translate subsections
                            translated_subsections[key] = self._translate_nested_sections(value)
                        else:
                            translated_subsections[key] = value
                    translated_sections[translated_section_name] = translated_subsections
                else:
                    # Handle top-level content that’s a string (not a dict)
                    if section_content.strip():
                        translated_content = self.translator(english_text=section_content).chinese_text
                    else:
                        translated_content = section_content  # Keep empty content as is
                    translated_sections[translated_section_name] = translated_content

            translated_main_title = list(translated_sections.keys())[0]
            translated_article = StormArticle(topic_name=translated_main_title)
            translated_article.insert_or_create_section(article_dict=translated_sections)
            return translated_article
        except Exception as e:
            print(f"Error in translation process: {str(e)}")
            return english_article

    def _translate_nested_sections(self, section_dict):
        """Recursively translate nested sections."""
        translated_dict = {}
        for subsection_name, subsection_content in section_dict.items():
            # Always translate the subsection name (heading)
            translated_subsection_name = self.translator(english_text=subsection_name).chinese_text
            if isinstance(subsection_content, dict):
                content = subsection_content.get("content", "")
                # Only translate content if it's non-empty
                if content.strip():
                    translated_content = self.translator(english_text=content).chinese_text
                else:
                    translated_content = content  # Keep empty content as is
                subsections = subsection_content.get("subsections", {})
                translated_subsections = self._translate_nested_sections(subsections)
                translated_dict[translated_subsection_name] = {
                    "content": translated_content,
                    "subsections": translated_subsections
                }
            else:
                # Handle subsection content that’s a string
                if subsection_content.strip():
                    translated_content = self.translator(english_text=subsection_content).chinese_text
                else:
                    translated_content = subsection_content  # Keep empty content as is
                translated_dict[translated_subsection_name] = translated_content
        return translated_dict