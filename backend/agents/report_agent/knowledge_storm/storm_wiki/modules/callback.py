from contextlib import contextmanager


class BaseCallbackHandler:
    """Base callback handler that can be used to handle callbacks from the STORM pipeline."""

    @contextmanager
    def event(self, event_name: str):
        """Context manager for tracking events during pipeline execution."""
        yield

    def on_identify_perspective_start(self, **kwargs):
        """Run when the perspective identification starts."""
        pass

    def on_identify_perspective_end(self, perspectives: list[str], **kwargs):
        """Run when the perspective identification finishes."""
        pass

    def on_information_gathering_start(self, **kwargs):
        """Run when the information gathering starts."""
        pass

    def on_conversation_turn_start(self, **kwargs):
        """Run when a conversation turn starts."""
        pass

    def on_conversation_ask(self, turn, question, asker_persona=None, **kwargs):
        """Run when a question is asked in a conversation turn."""
        pass

    def on_conversation_response(self, turn, response, searched_results=None, **kwargs):
        """Run when a response is provided in a conversation turn."""
        pass

    def on_conversation_turn_end(self, dlg_history, **kwargs):
        """Run when a conversation turn ends."""
        pass

    def on_dialogue_turn_end(self, dlg_turn, **kwargs):
        """Run when a question asking and answering turn finishes."""
        pass

    def on_information_gathering_end(self, **kwargs):
        """Run when the information gathering finishes."""
        pass

    def on_information_organization_start(self, **kwargs):
        """Run when the information organization starts."""
        pass

    def on_outline_generation_start(self, **kwargs):
        """Run when the outline generation starts."""
        pass

    def on_direct_outline_generation_end(self, outline: str, **kwargs):
        """Run when the direct outline generation finishes."""
        pass

    def on_outline_refinement_end(self, outline: str, **kwargs):
        """Run when the outline refinement finishes."""
        pass
