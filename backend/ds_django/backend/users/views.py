from rest_framework import viewsets, permissions
from .models import User, SearchHistory, ChatHistory
from .serializers import UserSerializer, SearchHistorySerializer, ChatHistorySerializer

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve users.
    (You can add create/update if you want self-signup endpoints.)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class SearchHistoryViewSet(viewsets.ModelViewSet):
    queryset = SearchHistory.objects.all()
    serializer_class = SearchHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ChatHistoryViewSet(viewsets.ModelViewSet):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
