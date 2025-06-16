from rest_framework import generics, permissions
from .models import Notebook
from .serializers import NotebookSerializer

class NotebookListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/notebooks/       → list only notebooks of request.user
    POST /api/notebooks/       → create new notebook for request.user
    """
    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotebookDetailAPIView(generics.RetrieveAPIView):
    """
    GET  /api/notebooks/{pk}/  → retrieve a single notebook if it belongs to request.user
    """
    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ensures 404 if someone tries to fetch another user’s notebook
        return Notebook.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        # Optional: if you need to do cleanup or soft-delete, override here
        instance.delete()
