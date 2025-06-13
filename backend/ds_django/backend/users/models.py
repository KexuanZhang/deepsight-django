from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    # override the parent m2m fields to avoid name collisions:
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",    # any unique name
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions_set",  # unique
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
        related_query_name="user",
    )
    # now you can still add extra fields if you want


class SearchHistory(models.Model):
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='search_histories'
    )
    search_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Search by {self.user.username}: {self.search_content[:30]}"

class ChatHistory(models.Model):
    notebook = models.ForeignKey(
        'notebooks.Notebook', on_delete=models.CASCADE, related_name='chat_histories'
    )
    chat_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ChatHistory for Notebook {self.notebook_id}"
