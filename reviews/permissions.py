
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    يسمح للمستخدم بتعديل أو حذف مراجعته فقط.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
