"""
Structures used for test run configuration. This code is used to configure test case runs.
"""
import random
from dataclasses import dataclass
from enum import auto
from typing import Optional, cast

from brownie import MyERC20

from brownie.network.account import Accounts, Account
from brownie.network.contract import ProjectContract
from brownie.network.transaction import TransactionReceipt, Status

from scripts.utils.contract import ContractBuilder
from scripts.utils.types import TransferNFTPaymentPostActionWithMeta
from tests.exceptions import InvalidChoiceException, InvalidTestStateException
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
    DISABLE_PAYMENT_REQUEST = auto()
    TRANSFER_NFT = auto()


@dataclass
class PaymentToken:
    address: str
    amount: int
    contract: ProjectContract


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
        payment_request_dependencies_deployer_account: Account,
        payment_request_deployer_account: Account,
    ):
        self._payment_request_configuration: PaymentRequestConfiguration = configuration
        self._accounts: Accounts = accounts
        self._payment_request_dependencies_deployer_account: Account = payment_request_dependencies_deployer_account
        self._payment_request_deployer_account: Account = (
            payment_request_deployer_account
        )

        self._payment_request: ProjectContract = (
            self.contract_builder.get_payment_request_contract(
                account=self._payment_request_deployer_account
            )
        )

        self._payment_precondition: Optional[ProjectContract] = None
        self._dynamic_token_amount: Optional[ProjectContract] = None
        self._tokens_for_dynamic_payment: Optional[ProjectContract] = None
        self._static_token_amounts: Optional[StaticTokenAmounts] = None
        self._post_payment_action: Optional[ProjectContract] = None

        self._setup_required_state()

    def _setup_required_state(self) -> None:
        self._payment_precondition = self._deploy_payment_precondition_or_none()
        self._dynamic_token_amount: Optional[
            ProjectContract
        ] = self._deploy_dynamic_token_amount_or_none()
        self._tokens_for_dynamic_token_amount_payment: Optional[list[ProjectContract]] = self._get_tokens_for_dynamic_token_amount_payment_or_none()
        self._static_token_amounts: Optional[
            StaticTokenAmounts
        ] = self._deploy_static_token_amount_or_none()
        self._post_payment_action: Optional[
            ProjectContract
        ] = self._deploy_payment_post_action_or_none()

    @property
    def contract_builder(self) -> ContractBuilder:
        return ContractBuilder(account=self._payment_request_dependencies_deployer_account, force_deploy=True)

    @property
    def payment_request_dependencies_deployer_account(self) -> Account:
        return self._payment_request_dependencies_deployer_account

    @property
    def accounts(self) -> Accounts:
        return self._accounts

    @property
    def payment_request(self) -> ProjectContract:
        return self._payment_request

    @property
    def payment_precondition(self) -> Optional[ProjectContract]:
        return self._payment_precondition

    @property
    def token_amount_option(self) -> TokenAmount:
        return self._payment_request_configuration.token_amount

    @property
    def tokens_for_dynamic_token_amount_payment(self) -> list[ProjectContract]:
        return self._tokens_for_dynamic_token_amount_payment

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
        return self._payment_request_configuration.token_amount == TokenAmount.STATIC

    @property
    def payment_request_deployer_account(self) -> Account:
        return self._payment_request_deployer_account

    def transfer_erc20_to_address(self, *, erc20: ProjectContract, to: Account, amount: int):
        erc20.transfer(to.address, amount, {"from": self._payment_request_dependencies_deployer_account})

    def approve_tokens_for_payment_request(self, *, erc20: ProjectContract, from_account: Account, amount: int):
        erc20.approve(self.payment_request.address, amount, {"from": from_account})

    def _deploy_payment_precondition_or_none(self) -> Optional[ProjectContract]:
        if self._payment_request_configuration.payment_precondition == PaymentPrecondition.NONE:
            return None

        if self._payment_request_configuration.payment_precondition == PaymentPrecondition.NFT_OWNER:
            return self.contract_builder.NFTOwnerPaymentPrecondition

        if (
            self._payment_request_configuration.payment_precondition
            == PaymentPrecondition.ONE_PURCHASE_PER_ADDRESS
        ):
            return self.contract_builder.OnePurchasePerAddressPaymentPrecondition

        raise InvalidChoiceException(
            f"{self._payment_request_configuration.payment_precondition=} is not a valid choice."
        )

    def _deploy_dynamic_token_amount_or_none(self) -> Optional[ProjectContract]:
        if self.is_token_amount_static:
            return None

        if self._payment_request_configuration.token_amount == TokenAmount.FIXED:
            # use .price() to get the required price
            return self.contract_builder.FixedPricePaymentComputer

        if self._payment_request_configuration.token_amount == TokenAmount.DISCOUNTED:
            return self.contract_builder.DiscountedTokenAmountForFirst100Customers

        raise InvalidChoiceException(
            f"{self._payment_request_configuration.token_amount=} is not a valid choice."
        )

    def _deploy_static_token_amount_or_none(self) -> Optional[StaticTokenAmounts]:
        if self.is_token_amount_static:
            static_token_amounts: StaticTokenAmounts = []

            token_amount: int
            for token_amount in self._payment_request_configuration.static_token_amounts:
                erc20: ProjectContract = self.contract_builder.MyERC20
                static_token_amounts.append((erc20.address, token_amount))

            return static_token_amounts

    def _get_tokens_for_dynamic_token_amount_payment_or_none(self) -> Optional[list[ProjectContract]]:
        # create 5 tokens for now, add more tokens if needed later
        if self.is_token_amount_static:
            return
        else:
            return [
                self.contract_builder.MyERC20 for _ in range(3)
            ]

    def _deploy_payment_post_action_or_none(self) -> Optional[ProjectContract]:
        if self._payment_request_configuration.post_payment_action == PostPaymentAction.NONE:
            return None

        if self._payment_request_configuration.post_payment_action == PostPaymentAction.EMIT_EVENTS:
            return self.contract_builder.MyPostPaymentAction

        if (
            self._payment_request_configuration.post_payment_action
            == PostPaymentAction.DISABLE_PAYMENT_REQUEST
        ):
            return self.contract_builder.DisablePaymentRequestPaymentPostAction

        if self._payment_request_configuration.post_payment_action == PostPaymentAction.TRANSFER_NFT:
            transfer_nft_contract: TransferNFTPaymentPostActionWithMeta = (
                self.contract_builder.TransferNFTPaymentPostAction
            )
            erc721: ProjectContract = transfer_nft_contract.Meta.erc721
            erc721_id: int = transfer_nft_contract.Meta.erc721_id

            erc721.approve(
                self._payment_request.address,
                erc721_id,
                {"from": self.contract_builder.account},
            )
            return transfer_nft_contract

        raise InvalidChoiceException(
            f"{self._payment_request_configuration.post_payment_action=} is not a valid choice."
        )


class PaymentRequestTestProxy:
    """
    Proxy for interacting with a Payment Request. This class is to be used by a test runner, that actually
    decides on the tests that shold be run.
    """

    def __init__(
        self, *,
        payment_request_builder: PaymentRequestBuilder,
        creator_account: Account,
    ):
        self._payment_request_builder: PaymentRequestBuilder = payment_request_builder
        self._creator_account: Account = creator_account

    def create_payment_request_for(
        self, *, for_account: Account, perform_assertions: bool = True
    ):
        raise NotImplementedError()

    def create_payment_request(self) -> int:
        # Decide whether to use createWithStaticTokenAmount() or createDynamicTokenAmount()
        tx: TransactionReceipt = (
            self._payment_request_builder.payment_request.createWithStaticTokenAmount(
                self._payment_request_builder.static_token_amounts,
                self._payment_request_builder.payment_precondition,
                self._payment_request_builder.post_payment_action,
                {"from": self._creator_account},
            )
            if self._payment_request_builder.is_token_amount_static
            else self._payment_request_builder.payment_request.createWithDynamicTokenAmount(
                self._payment_request_builder.dynamic_token_amount,
                self._payment_request_builder.payment_precondition,
                self._payment_request_builder.post_payment_action,
                {"from": self._creator_account},
            )
        )

        assert tx.status == Status.Confirmed

        payment_request_id: int = int(tx.return_value)

        assert (
            self._payment_request_builder.payment_request.ownerOf(payment_request_id)
            == self._creator_account.address
        )
        assert self._payment_request_builder.payment_request.isEnabled(payment_request_id) == True

        # TODO: assert receipt has no entries for this ID, assert dynamic part addresses are correct
        return payment_request_id

    def _get_random_token_addr_and_amount_to_pay(self, payment_request_id: int, payer: Account) -> PaymentToken:
        if self._payment_request_builder.is_token_amount_static:
            static_tokens: StaticTokenAmounts
            if static_tokens := self._payment_request_builder.static_token_amounts:
                selected_payment_token: tuple[str, int] = random.choice(static_tokens)
                return PaymentToken(
                    address=selected_payment_token[0],
                    amount=selected_payment_token[1],
                    contract=MyERC20.from_abi("MyERC20", selected_payment_token[0], MyERC20.abi),
                )
            else:
                raise InvalidTestStateException(
                    "The PaymentRequest is static, but no static token amounts found."
                )
        else:
            # dynamic token amount. With the test contracts, payments in any token are
            # accepted
            selected_token_for_payment: ProjectContract = random.choice(self._payment_request_builder.tokens_for_dynamic_token_amount_payment)

            tx: TransactionReceipt = self._payment_request_builder.payment_request.getAmountForToken(
                payment_request_id,
                selected_token_for_payment.address,
                payer.address,
                payer.address,
            )
            assert tx.status == Status.Confirmed
            token_amount: int = int(tx.return_value)

            return PaymentToken(
                address=selected_token_for_payment.address,
                amount=token_amount,
                contract=selected_token_for_payment,
            )

    def pay_for_payment_request_with_success(
        self, payment_request_id: int, payer: Account
    ):
        """
        Pay for payment request with the provided payment_request_id.
        """
        payment_request: ProjectContract = self._payment_request_builder.payment_request
        # 1. Identify how many tokens need to be paid, ensure payer has them and approved
        payment_token: PaymentToken = self._get_random_token_addr_and_amount_to_pay(
            payment_request_id,
            payer,
        )

        self._payment_request_builder.transfer_erc20_to_address(
            erc20=payment_token.contract,
            to=payer,
            amount=payment_token.amount,
        )

        self._payment_request_builder.approve_tokens_for_payment_request(
            erc20=payment_token.contract,
            from_account=payer,
            amount=payment_token.amount
        )

        # 2. Identify if there are preconditions that need to be met
        # TODO: first, only testing the simple case

        # 3. Perform payment + Assertions
        tx: TransactionReceipt = payment_request.pay(
            payment_request_id,
            payment_token.address,
            {"from": payer}
        )
        assert tx.status == Status.Confirmed
        receipt_id: int = int(tx.return_value)

        # TODO: receipt assertions

        # 4. Check Payment-Post-Action, If Any + Assertions
        # TODO: first, only testing the simple case
