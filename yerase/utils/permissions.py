from rest_framework.permissions import BasePermission
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

class RoleBasedPermission(BasePermission):
    """
    Custom permission to allow access only to users with specific roles.
    """

    allowed_roles = []  # This will be dynamically assigned by the decorator

    def has_permission(self, request, view=None):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated("Please log in")

        # Check if the user has one of the allowed roles
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied("Access denied: Insufficient permissions")

        return True


def role_required(roles):
    """
    Function to create a permission class with specific role access.
    This function returns a permission class that checks the role.
    """
    class CustomRolePermission(RoleBasedPermission):
        allowed_roles = roles  # Dynamically assign the allowed roles

    return CustomRolePermission
