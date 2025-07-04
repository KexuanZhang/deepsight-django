import logging
import re
from typing import Union, List, Optional

import dspy
from prompts import import_prompts


class FindRelatedTopic(dspy.Signature):
    __doc__ = import_prompts().FindRelatedTopic_docstring
    text_input = dspy.InputField(prefix="The relevant text: ", format=str)
    topic = dspy.InputField(prefix="Topic to focus on: ", format=str, required=False)
    old_outline = dspy.InputField(
        prefix="Existing outline to guide the search: ", format=str, required=False
    )
    related_topics = dspy.OutputField(format=str)


class GenPersona(dspy.Signature):
    __doc__ = import_prompts().GenPersona_docstring
    text_input = dspy.InputField(
        prefix="The relevant text (or 'N/A' if not available): ", format=str
    )
    topic = dspy.InputField(prefix="Topic to focus on: ", format=str, required=False)
    old_outline = dspy.InputField(
        prefix="Existing outline to guide persona creation: ",
        format=str,
        required=False,
    )
    personas = dspy.OutputField(format=str)


class CreateWriterWithPersona(dspy.Module):
    """Discover different perspectives of researching the topic by reading Wikipedia pages of related topics."""

    def __init__(self, engine: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        super().__init__()
        self.find_related_topic = dspy.ChainOfThought(FindRelatedTopic)
        self.gen_persona = dspy.ChainOfThought(GenPersona)
        self.engine = engine

    def forward(
        self,
        text_input: str,
        topic: Optional[str] = None,
        old_outline: Optional[str] = None,
        draft=None,
    ):
        with dspy.settings.context(lm=self.engine):
            related_topics = self.find_related_topic(
                text_input=text_input, topic=topic, old_outline=old_outline
            ).related_topics
            gen_persona_output = self.gen_persona(
                text_input=text_input, topic=topic, old_outline=old_outline
            ).personas
        personas = [
            match.group(1)
            for s in gen_persona_output.split("\n")
            if (match := re.search(r"\d+\.\s*(.*)", s))
        ]
        return dspy.Prediction(
            personas=personas,
            raw_personas_output=personas,
            related_topics=related_topics,
        )


class StormPersonaGenerator:
    """
    A generator class for creating personas based on a given text and optional topic.
    """

    def __init__(self, lm_config: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        self.create_writer_with_persona = CreateWriterWithPersona(engine=lm_config)

    def generate_persona(
        self,
        text_input: str,
        max_num_persona: int = 3,
        topic: Optional[str] = None,
        old_outline: Optional[str] = None,
    ) -> List[str]:
        """
        Generates a list of personas based on the provided text and optional topic.

        Args:
            text_input (str): The text for which personas are to be generated.
            max_num_persona (int): The maximum number of personas to generate.
            topic (Optional[str]): An optional topic to guide persona generation.
            old_outline: An optional old outline from a previous run to guide persona generation.

        Returns:
            List[str]: A list of persona descriptions.
        """
        personas = self.create_writer_with_persona(
            text_input=text_input, topic=topic, old_outline=old_outline
        )
        default_persona = "Technical report writer: Focuses on the technical details, such as system design, model architecture, and implementation methods. Prioritizes clarity and depth for a technical audience, rather than general overviews."
        considered_personas = [default_persona] + personas.personas[:max_num_persona]
        return considered_personas
