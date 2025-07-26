from enum import Enum

class MembershipRole(Enum):
    ADMIN = 'admin'
    MEMBER = 'member'
    TREASURER = 'treasurer'

    @classmethod
    def choices(cls):
        return [(role.value, role.name.capitalize()) for role in cls]
    
class MembershipStatus(Enum):
    INVITED = 'invited'
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    REMOVED = 'removed'

    @classmethod
    def choices(cls):
        return [(status.value, status.name.capitalize()) for status in cls]
