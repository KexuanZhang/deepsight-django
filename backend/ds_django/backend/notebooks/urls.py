from django.urls import path
from .views import NotebookListCreateAPIView, NotebookDetailAPIView

urlpatterns = [
    path('', NotebookListCreateAPIView.as_view(), name='notebook-list-create'),
    path('<int:pk>/', NotebookDetailAPIView.as_view(), name='notebook-detail'),
]
