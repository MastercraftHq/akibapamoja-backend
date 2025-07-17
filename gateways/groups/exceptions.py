from rest_framework.exceptions import APIException
from rest_framework import status


class RegistrationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Registration failed. Please check the provided information."
    default_code = "registration_failed"


class AuthenticationError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Invalid credentials. Please try again."
    default_code = "authentication_failed"


class UpdateError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Update failed. Please check the submitted data."
    default_code = "update_failed"


class PermissionDeniedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class UserNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested user was not found."
    default_code = "user_not_found"


class InvalidGroupCodeError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid or expired group invitation code."
    default_code = "invalid_group_code"
    
class AlreadyMemberError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "User is already a member of this group."
    default_code = "already_member"
    
class GroupNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested group was not found."
    default_code = "group_not_found"


class NotGroupMemberError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You must be a member of the group to perform this action."
    default_code = "not_group_member"


class GroupPermissionDeniedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to manage this group."
    default_code = "group_permission_denied"


class MembershipAlreadyExistsError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This user is already a member of the group."
    default_code = "membership_already_exists"
    
class CannotLeaveAsOnlyAdminError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "You are the only admin. Assign another admin before leaving."
    default_code = "cannot_leave_as_only_admin"
    
class MembershipNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Membership not found."
    default_code = "membership-not_found"

