from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated as DRFIsAuthenticated

class BaseRolePermission(BasePermission):

    required_role = None 

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False  # First check if user is authenticated
        
        return request.user.role == self.required_role  # Then check role


class IsManager(BaseRolePermission):
    required_role = 'manager'

class IsCandidate(BaseRolePermission):
    required_role = 'candidate'

class IsRecruiter(BaseRolePermission):
    required_role = 'recruiter'

class IsClient(BaseRolePermission):
    required_role = 'client'

class IsInterviewer(BaseRolePermission):
    required_role = 'interviewer'

class IsAdmin(BaseRolePermission):
    required_role = 'admin'
