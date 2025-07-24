from django.apps import AppConfig


class NotebooksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notebooks"
    
    def ready(self):
        """Import signals when app is ready"""
        import notebooks.signals
