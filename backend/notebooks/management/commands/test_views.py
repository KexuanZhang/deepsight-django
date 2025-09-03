"""
Test command to verify view imports and basic functionality
"""
from django.core.management.base import BaseCommand
from django.test import RequestFactory
# Legacy views no longer available - using services directly
from notebooks.services import URLService
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Test view imports and basic functionality'

    def handle(self, *args, **options):
        self.stdout.write("Testing service functionality...")
        
        try:
            # Test service import
            self.stdout.write(f"URLService class: {URLService}")
            self.stdout.write(f"URLService module: {URLService.__module__}")
            self.stdout.write(f"URLService methods: {[m for m in dir(URLService) if not m.startswith('_')]}")
            
            # Test instantiation
            service = URLService()
            self.stdout.write(f"URLService instance: {service}")
            self.stdout.write(f"Has handle methods: {hasattr(service, 'handle_single_url_parse')}")
            
            self.stdout.write(self.style.SUCCESS("All service imports and instantiation successful!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()