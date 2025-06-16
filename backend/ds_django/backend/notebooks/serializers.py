from rest_framework import serializers
from .models import Notebook

class NotebookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notebook
        fields = ('id', 'user', 'name', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')
