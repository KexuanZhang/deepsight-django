"""
Custom DRF permission classes for the DeepSight application.
"""

from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user


class IsOwnerPermission(BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    """

    def has_object_permission(self, request, view, obj):
        # Only allow access to the owner of the object.
        return obj.user == request.user


class IsNotebookOwner(BasePermission):
    """
    Custom permission to check if user owns the notebook for nested resources.
    """

    def has_object_permission(self, request, view, obj):
        # For objects that have a notebook field
        if hasattr(obj, 'notebook'):
            return obj.notebook.user == request.user
        # For objects that are notebooks themselves
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsAuthenticatedAndNotebook(permissions.IsAuthenticated):
    """
    Custom permission that ensures the user is authenticated
    and has access to the specified notebook.
    """

    def has_permission(self, request, view):
        # First check if user is authenticated
        if not super().has_permission(request, view):
            return False
        
        # Check if notebook_id is in URL kwargs
        notebook_id = view.kwargs.get('notebook_id')
        if notebook_id:
            from notebooks.models import Notebook
            try:
                notebook = Notebook.objects.get(id=notebook_id, user=request.user)
                # Store notebook in request for later use
                request.notebook = notebook
                return True
            except Notebook.DoesNotExist:
                return False
        
        return True