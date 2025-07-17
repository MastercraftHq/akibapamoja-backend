from enum import Enum



class MembershipRole(Enum):
    ADMIN = "admin"
    MEMBER = "member"

    @classmethod
    def choices(cls):
        return [(role.value, role.name.title()) for role in cls]


class MembershipStatus(Enum):
    ACTIVE = "active"
    INVITED = "invited"
    JOINED = "joined"
    REMOVED = "removed"

    @classmethod
    def choices(cls):
        return [(status.value, status.name.title()) for status in cls]
