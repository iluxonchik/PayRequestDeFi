"""
Structures used for test run configuration. This code is used to configure test case runs.
"""
from enum import auto
from tests.types import MinMaxEnum

class PaymentPrecondition(MinMaxEnum):
    NONE = 0
    ONE_PURHASE_PER_ADDRESS = auto()
    NFT_OWNER = auto()

class TokenAmount(MinMaxEnum):
    STATIC = 0
    FIXED = auto()
    DISCOUNTED = auto()

    @classmethod
    def is_value_static_token_amount(cls, value: int):
        return cls.STATIC.value == value

class PostPaymentAction(MinMaxEnum):
    NONE = 0
    EMIT_EVENTS = auto()
    TRANSFER_NFT = auto()
    DISABLE_PAYMENT_REQUEST = auto()


class PaymentRequestConfiguration:
    def __init__(self, payment_precondition_id: int, token_amount_id: int, post_payment_action_id: int, static_token_amounts: list[int]):
        self._payment_precondition: PaymentPrecondition = PaymentPrecondition._value2member_map_[payment_precondition_id]
        self._token_amount: TokenAmount = TokenAmount._value2member_map_[token_amount_id]
        self._post_payment_action: PostPaymentAction = PostPaymentAction._value2member_map_[post_payment_action_id]
        self._static_token_amounts: list[int] = static_token_amounts

    @property
    def payment_precondition(self):
        return self._payment_precondition

    @property
    def token_amount(self):
        return self._token_amount

    @property
    def post_payment_action(self):
        return self._post_payment_action

    @property
    def static_token_amounts(self):
        return self._static_token_amounts

    def __str__(self):
        return str(self.__dict__)

class PaymentRequestBuilder:
    def __init__(self, configuration: PaymentRequestConfiguration):
        self._configuration = configuration