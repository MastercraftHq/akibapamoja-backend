from enum import Enum

class PaymentMethod(Enum):
    MPESA = "mpesa"
    CASH = "cash"
    BANK = "bank"

    @classmethod
    def values(cls):
        return [pm.value for pm in cls]
