from enum import Enum

class UserRole(Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    TREASURER = "TREASURER"

    @classmethod
    def choices(cls):
        return [(role.value, role.name.capitalize()) for role in cls]