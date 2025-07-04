import concurrent.futures
import logging
import os
from concurrent.futures import as_completed
from typing import Union, List, Tuple, Optional, Dict

import dspy

from .callback import BaseCallbackHandler
from .persona_generator import StormPersonaGenerator
from .storm_dataclass import DialogueTurn, StormInformationTable
from ...interface import KnowledgeCurationModule, Retriever, Information
from ...utils import ArticleTextProcessing
from prompts import import_prompts

script_dir = os.path.dirname(os.path.abspath(__file__))


class ConvSimulator(dspy.Module):
    def __init__(
        self,
        topic_expert_engine: Union[dspy.dsp.LM, dspy.dsp.HFModel],
        question_asker_engine: Union[dspy.dsp.LM, dspy.dsp.HFModel],
        retriever: Retriever,
        max_search_queries_per_turn: int,
        search_top_k: int,
        max_turn: int,
    ):
        super().__init__()
        self.wiki_writer = WikiWriter(engine=question_asker_engine)
        self.topic_expert = TopicExpert(
            engine=topic_expert_engine,
            max_search_queries=max_search_queries_per_turn,
            search_top_k=search_top_k,
            retriever=retriever,
        )
        self.max_turn = max_turn

    def forward(
        self,
        text_input: str,
        persona: str,
        ground_truth_url: str,
        callback_handler: BaseCallbackHandler,
        topic: Optional[str] = None,
        old_outline: Optional[str] = None,
    ):
        dlg_history: List[DialogueTurn] = []

        # Add an initial turn to gather data and figures related to the topic
        initial_question = (
            f"Can you find any data and quantitative information about {topic}?"
        )
        expert_output = self.topic_expert(
            text_input=text_input,
            question=initial_question,
            ground_truth_url=ground_truth_url,
            old_outline=old_outline,
        )
        initial_turn = DialogueTurn(
            agent_utterance=expert_output.answer,
            user_utterance=initial_question,
            search_queries=expert_output.queries,
            search_results=expert_output.searched_results,
        )
        dlg_history.append(initial_turn)
        callback_handler.on_dialogue_turn_end(dlg_turn=initial_turn)

        for _ in range(self.max_turn):
            user_utterance = self.wiki_writer(
                text_input=text_input,
                persona=persona,
                dialogue_turns=dlg_history,
                topic=topic,
                old_outline=old_outline,
            ).question
            if user_utterance == "":
                logging.error("Simulated writer utterance is empty.")
                break
            if user_utterance.startswith("Thank you so much for your help!"):
                break
            expert_output = self.topic_expert(
                text_input=text_input,
                question=user_utterance,
                ground_truth_url=ground_truth_url,
                old_outline=old_outline,
            )
            dlg_turn = DialogueTurn(
                agent_utterance=expert_output.answer,
                user_utterance=user_utterance,
                search_queries=expert_output.queries,
                search_results=expert_output.searched_results,
            )
            dlg_history.append(dlg_turn)
            callback_handler.on_dialogue_turn_end(dlg_turn=dlg_turn)
        return dspy.Prediction(dlg_history=dlg_history)


class WikiWriter(dspy.Module):
    def __init__(self, engine: Union[dspy.dsp.LM, dspy.dsp.HFModel]):
        super().__init__()
        self.ask_question_with_persona = dspy.ChainOfThought(AskQuestionWithPersona)
        self.ask_question = dspy.ChainOfThought(AskQuestion)
        self.engine = engine

    def forward(
        self,
        text_input: str,
        persona: str,
        dialogue_turns: List[DialogueTurn],
        draft_page=None,
        topic: Optional[str] = None,
        old_outline: Optional[str] = None,
    ):
        conv = []
        for turn in dialogue_turns[:-4]:
            conv.append(
                f"You: {turn.user_utterance}\nExpert: omit the answer here due to space limit."
            )
        for turn in dialogue_turns[-4:]:
            conv.append(
                f"You: {turn.user_utterance}\nExpert: {ArticleTextProcessing.remove_citations(turn.agent_utterance)}"
            )
        conv = "\n".join(conv)
        conv = conv.strip() or "N/A"
        conv = ArticleTextProcessing.limit_word_count_preserve_newline(conv, 5000)
        with dspy.settings.context(lm=self.engine):
            if persona is not None and len(persona.strip()) > 0:
                question = self.ask_question_with_persona(
                    text_input=text_input,
                    persona=persona,
                    conv=conv,
                    topic=topic,
                    old_outline=old_outline,
                ).question
            else:
                question = self.ask_question(
                    text_input=text_input,
                    conv=conv,
                    topic=topic,
                    old_outline=old_outline,
                ).question
        return dspy.Prediction(question=question)


class AskQuestion(dspy.Signature):
    __doc__ = import_prompts().AskQuestion_docstring
    text_input = dspy.InputField(
        prefix="The relevant text (or 'N/A' if not available): ", format=str
    )
    conv = dspy.InputField(prefix="Conversation history:\n", format=str)
    topic = dspy.InputField(prefix="Topic to focus on: ", format=str)
    old_outline = dspy.InputField(
        prefix="Existing outline to help guide questions: ", format=str, required=False
    )
    question = dspy.OutputField(format=str)


class AskQuestionWithPersona(dspy.Signature):
    __doc__ = import_prompts().AskQuestionWithPersona_docstring
    text_input = dspy.InputField(
        prefix="The relevant text (or 'N/A' if not available): ", format=str
    )
    persona = dspy.InputField(
        prefix="Your persona besides being a report writer: ", format=str
    )
    conv = dspy.InputField(prefix="Conversation history:\n", format=str)
    topic = dspy.InputField(prefix="Topic to focus on: ", format=str)
    old_outline = dspy.InputField(
        prefix="Existing outline to help guide questions: ", format=str, required=False
    )
    question = dspy.OutputField(format=str)


class QuestionToQuery(dspy.Signature):
    __doc__ = import_prompts().QuestionToQuery_docstring
    text_input = dspy.InputField(prefix="The relevant text: ", format=str)
    question = dspy.InputField(prefix="Question you want to answer: ", format=str)
    old_outline = dspy.InputField(
        prefix="Existing outline to help guide search: ", format=str, required=False
    )
    queries = dspy.OutputField(format=str)


class AnswerQuestion(dspy.Signature):
    __doc__ = import_prompts().AnswerQuestion_docstring
    text_input = dspy.InputField(prefix="The relevant text: ", format=str)
    conv = dspy.InputField(prefix="Question:\n", format=str)
    info = dspy.InputField(prefix="Gathered information:\n", format=str)
    old_outline = dspy.InputField(
        prefix="Existing outline to help guide the answer: ", format=str, required=False
    )
    answer = dspy.OutputField(prefix="Now give your response.\n", format=str)


class TopicExpert(dspy.Module):
    def __init__(
        self,
        engine: Union[dspy.dsp.LM, dspy.dsp.HFModel],
        max_search_queries: int,
        search_top_k: int,
        retriever: Retriever,
    ):
        super().__init__()
        self.generate_queries = dspy.Predict(QuestionToQuery)
        self.retriever = retriever
        self.answer_question = dspy.Predict(AnswerQuestion)
        self.engine = engine
        self.max_search_queries = max_search_queries
        self.search_top_k = search_top_k

    def forward(
        self,
        text_input: str,
        question: str,
        ground_truth_url: str,
        old_outline: Optional[str] = None,
    ):
        with dspy.settings.context(lm=self.engine, show_guidelines=False):
            queries = self.generate_queries(
                text_input=text_input, question=question, old_outline=old_outline
            ).queries
            queries = [
                q.replace("-", "").strip().strip('"').strip('"').strip()
                for q in queries.split("\n")
            ]
            queries = queries[: self.max_search_queries]
            searched_results: List[Information] = self.retriever.retrieve(
                list(set(queries)), exclude_urls=[ground_truth_url]
            )
            if len(searched_results) > 0:
                info = ""
                for n, r in enumerate(searched_results):
                    info += "\n".join(f"[{n + 1}]: {s}" for s in r.snippets[:1])
                    info += "\n\n"
                info = ArticleTextProcessing.limit_word_count_preserve_newline(
                    info, 5000
                )
                try:
                    answer = self.answer_question(
                        text_input=text_input,
                        conv=question,
                        info=info,
                        old_outline=old_outline,
                    ).answer
                    answer = ArticleTextProcessing.remove_uncompleted_sentences_with_citations(
                        answer
                    )
                except Exception as e:
                    logging.error(f"Error occurs when generating answer: {e}")
                    answer = "Sorry, I cannot answer this question. Please ask another question."
            else:
                answer = "Sorry, I cannot find information for this question. Please ask another question."
        return dspy.Prediction(
            queries=queries, searched_results=searched_results, answer=answer
        )


class StormKnowledgeCurationModule(KnowledgeCurationModule):
    def __init__(
        self,
        retriever: Retriever,
        persona_generator: Optional[StormPersonaGenerator],
        conv_simulator_lm: Union[dspy.dsp.LM, dspy.dsp.HFModel],
        question_asker_lm: Union[dspy.dsp.LM, dspy.dsp.HFModel],
        max_search_queries_per_turn: int,
        search_top_k: int,
        max_conv_turn: int,
        max_thread_num: int,
    ):
        self.retriever = retriever
        self.persona_generator = persona_generator
        self.conv_simulator_lm = conv_simulator_lm
        self.search_top_k = search_top_k
        self.max_thread_num = max_thread_num
        self.retriever = retriever
        self.conv_simulator = ConvSimulator(
            topic_expert_engine=conv_simulator_lm,
            question_asker_engine=question_asker_lm,
            retriever=retriever,
            max_search_queries_per_turn=max_search_queries_per_turn,
            search_top_k=search_top_k,
            max_turn=max_conv_turn,
        )

    def _get_considered_personas(
        self,
        text_input: str,
        max_num_persona,
        topic: Optional[str] = None,
        old_outline: Optional[str] = None,
    ) -> List[str]:
        return self.persona_generator.generate_persona(
            text_input=text_input,
            max_num_persona=max_num_persona,
            topic=topic,
            old_outline=old_outline,
        )

    def _run_conversation(
        self,
        conv_simulator,
        text_input,
        ground_truth_url,
        considered_personas,
        callback_handler: BaseCallbackHandler,
        topic: Optional[str] = None,
        old_outline: Optional[str] = None,
    ) -> List[Tuple[str, List[DialogueTurn]]]:
        conversations = []

        def run_conv(persona):
            return conv_simulator(
                text_input=text_input,
                ground_truth_url=ground_truth_url,
                persona=persona,
                callback_handler=callback_handler,
                topic=topic,
                old_outline=old_outline,
            )

        max_workers = min(self.max_thread_num, len(considered_personas))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_persona = {
                executor.submit(run_conv, persona): persona
                for persona in considered_personas
            }
            for future in as_completed(future_to_persona):
                persona = future_to_persona[future]
                conv = future.result()
                conversations.append(
                    (persona, ArticleTextProcessing.clean_up_citation(conv).dlg_history)
                )
        return conversations

    def research(
        self,
        text_input: str,
        ground_truth_url: str,
        callback_handler: BaseCallbackHandler,
        max_perspective: int = 0,
        disable_perspective: bool = True,
        return_conversation_log=False,
        topic: Optional[str] = None,
        old_outline: Optional[str] = None,
    ) -> Union[StormInformationTable, Tuple[StormInformationTable, Dict]]:
        callback_handler.on_identify_perspective_start()
        considered_personas = []
        if disable_perspective:
            considered_personas = [""]
        else:
            considered_personas = self._get_considered_personas(
                text_input=text_input,
                max_num_persona=max_perspective,
                topic=topic,
                old_outline=old_outline,
            )
        callback_handler.on_identify_perspective_end(perspectives=considered_personas)
        callback_handler.on_information_gathering_start()
        conversations = self._run_conversation(
            conv_simulator=self.conv_simulator,
            text_input=text_input,
            ground_truth_url=ground_truth_url,
            considered_personas=considered_personas,
            callback_handler=callback_handler,
            topic=topic,
            old_outline=old_outline,
        )
        information_table = StormInformationTable(conversations)
        callback_handler.on_information_gathering_end()
        if return_conversation_log:
            return information_table, StormInformationTable.construct_log_dict(
                conversations
            )
        return information_table
