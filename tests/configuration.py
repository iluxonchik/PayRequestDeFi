"""
Structures used for test run configuration. This code is used to configure test case runs.
"""
from enum import auto
from typing import Optional, cast

from brownie.network.account import Accounts, Account
from brownie.network.contract import ProjectContract

from scripts.utils.contract import ContractBuilder
from tests.exceptions import InvalidChoiceException
from tests.types import MinMaxEnum, StaticTokenAmounts


class PaymentPrecondition(MinMaxEnum):
    NONE = 0
    NFT_OWNER = auto()
    ONE_PURCHASE_PER_ADDRESS = auto()


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
    def __init__(
        self,
        payment_precondition_id: int,
        token_amount_id: int,
        post_payment_action_id: int,
        static_token_amounts: list[int],
    ):
        self._payment_precondition: PaymentPrecondition = cast(
            PaymentPrecondition,
            PaymentPrecondition._value2member_map_[payment_precondition_id],
        )
        self._token_amount: TokenAmount = cast(
            TokenAmount, TokenAmount._value2member_map_[token_amount_id]
        )
        self._post_payment_action: PostPaymentAction = cast(
            PostPaymentAction,
            PostPaymentAction._value2member_map_[post_payment_action_id],
        )
        self._static_token_amounts: list[int] = static_token_amounts

    @property
    def payment_precondition(self) -> PaymentPrecondition:
        return self._payment_precondition

    @property
    def token_amount(self) -> TokenAmount:
        return self._token_amount

    @property
    def post_payment_action(self) -> PostPaymentAction:
        return self._post_payment_action

    @property
    def static_token_amounts(self) -> list[int]:
        return self._static_token_amounts

    def __str__(self):
        return str(self.__dict__)


class PaymentRequestBuilder:
    def __init__(
        self,
        configuration: PaymentRequestConfiguration,
        accounts: Accounts,
        deployer_account: Account,
    ):
        self._configuration: PaymentRequestConfiguration = configuration
        self._accounts: Accounts = accounts
        self._deployer_account: Account = deployer_account

        self._payment_precondition: Optional[ProjectContract] = None
        self._dynamic_token_amount: Optional[ProjectContract] = None
        self._static_token_amount: Optional[StaticTokenAmounts] = None
        self._post_payment_action: Optional[ProjectContract] = None

    def _setup_required_state(self) -> None:
        self._payment_precondition = self._deploy_payment_precondition_or_none()
        # TODO: fill below
        self._dynamic_token_amount: Optional[ProjectContract] = None
        self._static_token_amount: Optional[StaticTokenAmounts] = None
        self._post_payment_action: Optional[ProjectContract] = None

    @property
    def contract_builder(self) -> ContractBuilder:
        return ContractBuilder(account=self._deployer_account, force_deploy=True)

    def _deploy_payment_precondition_or_none(self):
        if self._configuration.payment_precondition == PaymentPrecondition.NONE:
            return None

        if self._configuration.payment_precondition == PaymentPrecondition.NFT_OWNER:
            return self.contract_builder.NFTOwnerPaymentPrecondition

        if (
            self._configuration.payment_precondition
            == PaymentPrecondition.ONE_PURCHASE_PER_ADDRESS
        ):
            # TODO: implement in contract builder
            raise NotImplemented()

        raise InvalidChoiceException(
            f"{self._configuration.payment_precondition=} is not a valid choice."
        )
