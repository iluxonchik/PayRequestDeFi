"""
Structures used for test run configuration. This code is used to configure test case runs.
"""
from enum import auto
from typing import Optional, cast

from brownie.network.account import Accounts, Account
from brownie.network.contract import ProjectContract
from brownie.network.transaction import TransactionReceipt, Status

from scripts.utils.contract import ContractBuilder
from scripts.utils.types import TransferNFTPaymentPostActionWithMeta
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
        payment_request_deployer_account: Account,
    ):
        self._configuration: PaymentRequestConfiguration = configuration
        self._accounts: Accounts = accounts
        self._deployer_account: Account = deployer_account
        self._payment_request_deployer_account: Account = payment_request_deployer_account

        self._payment_request: ProjectContract = self.contract_builder.get_payment_request_contract(account=self._payment_request_deployer_account)

        self._payment_precondition: Optional[ProjectContract] = None
        self._dynamic_token_amount: Optional[ProjectContract] = None
        self._static_token_amounts: Optional[StaticTokenAmounts] = None
        self._post_payment_action: Optional[ProjectContract] = None

    def _setup_required_state(self) -> None:
        self._payment_precondition = self._deploy_payment_precondition_or_none()
        self._dynamic_token_amount: Optional[ProjectContract] = self._deploy_dynamic_token_amount_or_none()
        self._static_token_amounts: Optional[StaticTokenAmounts] = self._deploy_static_token_amount_or_none()
        self._post_payment_action: Optional[ProjectContract] = self._deploy_payment_post_action_or_none()

    @property
    def contract_builder(self) -> ContractBuilder:
        return ContractBuilder(account=self._deployer_account, force_deploy=True)

    @property
    def deployer_account(self) -> Account:
        return self._deployer_account

    @property
    def payment_request(self) -> ProjectContract:
        return self._payment_request

    @property
    def payment_precondition(self) -> Optional[ProjectContract]:
        return self._payment_precondition
    @property
    def dynamic_token_amount(self) -> Optional[ProjectContract]:
        return self._dynamic_token_amount

    @property
    def static_token_amounts(self) -> Optional[StaticTokenAmounts]:
        return self._static_token_amounts

    @property
    def post_payment_action(self) -> Optional[ProjectContract]:
        return self._post_payment_action
    @property
    def is_token_amount_static(self) -> bool:
        return self._configuration.token_amount == TokenAmount.STATIC

    @property
    def payment_request_deployer_account(self) -> Account:
        return self._payment_request_deployer_account

    def _deploy_payment_precondition_or_none(self) -> Optional[ProjectContract]:
        if self._configuration.payment_precondition == PaymentPrecondition.NONE:
            return None

        if self._configuration.payment_precondition == PaymentPrecondition.NFT_OWNER:
            return self.contract_builder.NFTOwnerPaymentPrecondition

        if (
            self._configuration.payment_precondition
            == PaymentPrecondition.ONE_PURCHASE_PER_ADDRESS
        ):
            return self.contract_builder.OnePurchasePerAddressPaymentPrecondition

        raise InvalidChoiceException(
            f"{self._configuration.payment_precondition=} is not a valid choice."
        )

    def _deploy_dynamic_token_amount_or_none(self) -> Optional[ProjectContract]:
        if self.is_token_amount_static:
            return None

        if self._configuration.token_amount == TokenAmount.FIXED:
            # use .price() to get the required price
            return self.contract_builder.FixedPricePaymentComputer

        if self._configuration.token_amount == TokenAmount.DISCOUNTED:
            return self.contract_builder.DiscountedTokenAmountForFirst100Customers

        raise InvalidChoiceException(
            f"{self._configuration.token_amount=} is not a valid choice."
        )

    def _deploy_static_token_amount_or_none(self) -> Optional[StaticTokenAmounts]:
        if self.is_token_amount_static:
            static_token_amounts: StaticTokenAmounts = []

            token_amount: int
            for token_amount in self._configuration.static_token_amounts:
                erc20: ProjectContract = self.contract_builder.MyERC20
                static_token_amounts.append([erc20.address, token_amount])

            return static_token_amounts

    def _deploy_payment_post_action_or_none(self) -> Optional[ProjectContract]:
        if self._configuration.post_payment_action == PostPaymentAction.NONE:
            return None

        if self._configuration.post_payment_action == PostPaymentAction.EMIT_EVENTS:
            return self.contract_builder.MyPostPaymentAction

        if self._configuration.post_payment_action == PostPaymentAction.DISABLE_PAYMENT_REQUEST:
            return self.contract_builder.DisablePaymentRequestPaymentPostAction

        if self._configuration.post_payment_action == PostPaymentAction.TRANSFER_NFT:
            transfer_nft_contract: TransferNFTPaymentPostActionWithMeta = self.contract_builder.TransferNFTPaymentPostAction
            erc721: ProjectContract = transfer_nft_contract.Meta.erc721
            erc721_id: int = transfer_nft_contract.Meta.erc721_id

            erc721.approve(self._payment_request.address, erc721_id, {"from": self.contract_builder.account})
            return transfer_nft_contract

        raise InvalidChoiceException(
            f"{self._configuration.post_payment_action=} is not a valid choice."
        )
class PaymentRequestTestProxy:
    def __init__(self, *, configuration: PaymentRequestBuilder, creator_account: Account):
        self._configuration: PaymentRequestBuilder = configuration
        self._creator_account: Account = creator_account
    def create_payment_request_for(self, *, for_account: Account, perform_assertions: bool = True):
        raise NotImplementedError()
    def create_payment_request(self) -> int:
        # Decide whether to use createWithStaticTokenAmount() or createDynamicTokenAmount()
        tx: TransactionReceipt = self._configuration.payment_request.createWithStaticTokenAmount(
                self._configuration.static_token_amounts,
                self._configuration.payment_precondition,
                self._configuration.post_payment_action,
                {"from": self._creator_account}
            ) if self._configuration.is_token_amount_static else self._configuration.payment_request.createWithDynamicTokenAmount(
                self._configuration.dynamic_token_amount,
                self._configuration.payment_precondition,
                self._configuration.post_payment_action,
                {"from": self._creator_account}
            )

        assert tx.status == Status.Confirmed

        payment_request_id: int = int(tx.return_value)

        assert self._configuration.payment_request.ownerOf(payment_request_id) == self._creator_account.address
        assert self._configuration.payment_request.isEnabled(payment_request_id) == True

        # TODO: assert receipt has no entries for this ID, assert dynamic part addresses are correct
        return payment_request_id












































