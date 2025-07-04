from django.apps import AppConfig


class RagConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rag'

    def ready(self):
        # build the chain once at startup
        from . import engine
        engine.RAG_CHAIN = engine.build_rag_chain()
