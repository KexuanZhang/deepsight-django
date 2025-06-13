from rest_framework.routers import DefaultRouter
from .views import UserViewSet, SearchHistoryViewSet, ChatHistoryViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'search-history', SearchHistoryViewSet, basename='search-history')
router.register(r'chat-history', ChatHistoryViewSet, basename='chat-history')

urlpatterns = router.urls
