"""
Test command to verify view imports and basic functionality
"""
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from notebooks.views import URLParseView, SimpleTestView
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Test view imports and basic functionality'

    def handle(self, *args, **options):
        self.stdout.write("Testing view imports...")
        
        try:
            # Test import
            self.stdout.write(f"URLParseView class: {URLParseView}")
            self.stdout.write(f"URLParseView module: {URLParseView.__module__}")
            self.stdout.write(f"URLParseView methods: {[m for m in dir(URLParseView) if not m.startswith('_')]}")
            
            # Test instantiation
            view = URLParseView()
            self.stdout.write(f"URLParseView instance: {view}")
            self.stdout.write(f"Has post method: {hasattr(view, 'post')}")
            self.stdout.write(f"HTTP method names: {getattr(view, 'http_method_names', 'not set')}")
            
            # Test SimpleTestView
            simple_view = SimpleTestView()
            self.stdout.write(f"SimpleTestView instance: {simple_view}")
            self.stdout.write(f"SimpleTestView has post: {hasattr(simple_view, 'post')}")
            
            self.stdout.write(self.style.SUCCESS("All view imports and instantiation successful!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()