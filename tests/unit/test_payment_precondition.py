import pytest
from brownie import PaymentRequest, MyERC20, MyERC721
from brownie import accounts
from brownie.exceptions import VirtualMachineError
from brownie.network.account import Account
from brownie.network.transaction import TransactionReceipt, Status
from web3.constants import ADDRESS_ZERO

from scripts.utils.contants import EventName, PaymentFailedAt
from scripts.utils.contract import ContractBuilder
from scripts.utils.environment import is_local_blockchain_environment
from scripts.utils.types import NFTOwnerPaymentPreconditionWithMeta
from tests.asserters import (
    assert_expected_events_occurred_for_successful_transaction,
    assert_expected_events_occurred_for_failed_transaction,
)


@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass


def test_GIVEN_sample_nft_payment_precondition_WHEN_non_nft_owner_not_payment_creator_attempts_to_purchase_exclusive_token_THEN_error_occurs(
    *args, **kwargs
):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    no_nft_or_pr: Account = accounts[3]

    deployer_contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    precondition: NFTOwnerPaymentPreconditionWithMeta = (
        deployer_contract_builder.NFTOwnerPaymentPrecondition
    )

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(
        account=deployer, force_deploy=True
    )
    exclusive_token: MyERC20 = precondition.Meta.erc20

    # seed account with tokens
    non_exclusive_token.transfer(no_nft_or_pr.address, 100, {"from": deployer})
    exclusive_token.transfer(no_nft_or_pr.address, 100, {"from": deployer})

    # construct the main PaymentRequest
    payment_request: PaymentRequest = deployer_contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer},
    )
    payment_request_id: int = tx.return_value

    non_exclusive_token.approve(
        payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": no_nft_or_pr}
    )
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(
            payment_request_id, non_exclusive_token.address, {"from": no_nft_or_pr}
        )

    tx = TransactionReceipt(e.value.txid)
    assert tx.status == Status.Reverted
    assert_expected_events_occurred_for_failed_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
        failed_at=PaymentFailedAt.PP,
    )

    exclusive_token.approve(
        payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": no_nft_or_pr}
    )
    with pytest.raises(VirtualMachineError):
        payment_request.pay(
            payment_request_id, exclusive_token.address, {"from": no_nft_or_pr}
        )

    tx = TransactionReceipt(e.value.txid)
    assert tx.status == Status.Reverted
    assert EventName.PAYMENT_PRECONDITION_PASSED not in tx.events

    assert payment_request.isPaymentPreconditionSet(payment_request_id)
    assert not payment_request.isPaymentPostActionSet(payment_request_id)

    assert payment_request.getPostPaymentAction(payment_request_id) == ADDRESS_ZERO
    assert (
        payment_request.getPaymentPrecondition(payment_request_id)
        == precondition.address
    )
    assert payment_request.getDynamicTokenAmount(payment_request_id) == ADDRESS_ZERO


def test_GIVEN_sample_nft_payment_precondition_WHEN_nft_owner_not_payment_creator_attempts_to_purchase_exclusive_token_THEN_only_exclusive_token_purchase_is_allowed(
    *args, **kwargs
):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    nft_no_pr: Account = accounts[1]

    deployer_contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    precondition: NFTOwnerPaymentPreconditionWithMeta = (
        deployer_contract_builder.NFTOwnerPaymentPrecondition
    )

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(
        account=deployer, force_deploy=True
    )
    exclusive_token: MyERC20 = precondition.Meta.erc20
    exclusive_nft: MyERC721 = precondition.Meta.erc721

    # seed account with tokens
    non_exclusive_token.transfer(nft_no_pr.address, 100, {"from": deployer})
    exclusive_token.transfer(nft_no_pr.address, 100, {"from": deployer})

    exclusive_nft.create(nft_no_pr.address, {"from": nft_no_pr})

    # construct the main PaymentRequest
    payment_request: PaymentRequest = deployer_contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer},
    )
    payment_request_id: int = tx.return_value

    non_exclusive_token.approve(
        payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": nft_no_pr}
    )
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(
            payment_request_id, non_exclusive_token.address, {"from": nft_no_pr}
        )

    tx = TransactionReceipt(e.value.txid)
    assert tx.status == Status.Reverted
    assert_expected_events_occurred_for_failed_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
        failed_at=PaymentFailedAt.PP,
    )

    exclusive_token.approve(
        payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": nft_no_pr}
    )
    tx = payment_request.pay(
        payment_request_id, exclusive_token.address, {"from": nft_no_pr}
    )
    assert tx.status == Status.Confirmed
    assert_expected_events_occurred_for_successful_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
    )

    assert payment_request.isPaymentPreconditionSet(payment_request_id)
    assert not payment_request.isPaymentPostActionSet(payment_request_id)

    assert payment_request.getPostPaymentAction(payment_request_id) == ADDRESS_ZERO
    assert (
        payment_request.getPaymentPrecondition(payment_request_id)
        == precondition.address
    )
    assert payment_request.getDynamicTokenAmount(payment_request_id) == ADDRESS_ZERO


def test_GIVEN_sample_nft_payment_precondition_WHEN_not_nft_owner_payment_creator_attempts_to_purchase_exclusive_token_THEN_only_non_exclusive_token_purchase_is_allowed(
    *args, **kwargs
):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    pr_no_nft: Account = accounts[1]

    deployer_contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    precondition: NFTOwnerPaymentPreconditionWithMeta = (
        deployer_contract_builder.NFTOwnerPaymentPrecondition
    )

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(
        account=deployer, force_deploy=True
    )
    exclusive_token: MyERC20 = precondition.Meta.erc20

    # seed account with tokens
    non_exclusive_token.transfer(pr_no_nft.address, 100, {"from": deployer})
    exclusive_token.transfer(pr_no_nft.address, 100, {"from": deployer})

    # construct the main PaymentRequest
    payment_request: PaymentRequest = deployer_contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            (non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT),
            (exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT),
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer},
    )

    payment_request_id: int = tx.return_value

    # deploy payment for the Non-NFT, only Payment Request owner contract
    payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": pr_no_nft},
    )
    assert tx.status == Status.Confirmed

    non_exclusive_token.approve(
        payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": pr_no_nft}
    )
    tx = payment_request.pay(
        payment_request_id, non_exclusive_token.address, {"from": pr_no_nft}
    )
    assert tx.status == Status.Confirmed

    assert_expected_events_occurred_for_successful_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
    )

    # WHEN / THEN
    exclusive_token.approve(
        payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": pr_no_nft}
    )
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(
            payment_request_id, exclusive_token.address, {"from": pr_no_nft}
        )

    tx = TransactionReceipt(e.value.txid)
    assert tx.status == Status.Reverted
    assert_expected_events_occurred_for_failed_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
        failed_at=PaymentFailedAt.PP,
    )

    assert not payment_request.isTokenAmountDynamic(payment_request_id)
    assert payment_request.isTokenAmountStatic(payment_request_id)
    assert payment_request.isPaymentPreconditionSet(payment_request_id)
    assert not payment_request.isPaymentPostActionSet(payment_request_id)

    assert payment_request.getPostPaymentAction(payment_request_id) == ADDRESS_ZERO
    assert (
        payment_request.getPaymentPrecondition(payment_request_id)
        == precondition.address
    )
    assert payment_request.getDynamicTokenAmount(payment_request_id) == ADDRESS_ZERO


def test_GIVEN_sample_nft_payment_precondition_WHEN_nft_owner_and_payment_creator_attempts_to_purchase_exclusive_token_THEN_both_token_purchases_are_allowed(
    *args, **kwargs
):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    pr_and_nft: Account = accounts[1]

    deployer_contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    precondition: NFTOwnerPaymentPreconditionWithMeta = (
        deployer_contract_builder.NFTOwnerPaymentPrecondition
    )

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(
        account=deployer, force_deploy=True
    )
    exclusive_token: MyERC20 = precondition.Meta.erc20
    exclusive_nft: MyERC721 = precondition.Meta.erc721

    # seed account with tokens
    non_exclusive_token.transfer(pr_and_nft.address, 100, {"from": deployer})
    exclusive_token.transfer(pr_and_nft.address, 100, {"from": deployer})
    exclusive_nft.create(pr_and_nft.address, {"from": deployer})

    # construct the main PaymentRequest
    payment_request: PaymentRequest = deployer_contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer},
    )

    payment_request_id: int = tx.return_value

    # deploy payment for the Non-NFT, only Payment Request owner contract
    payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": pr_and_nft},
    )

    # WHEN/THEN
    non_exclusive_token.approve(
        payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": pr_and_nft}
    )
    tx = payment_request.pay(
        payment_request_id, non_exclusive_token.address, {"from": pr_and_nft}
    )
    assert tx.status == Status.Confirmed
    assert_expected_events_occurred_for_successful_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
    )

    exclusive_token.approve(
        payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": pr_and_nft}
    )
    tx = payment_request.pay(
        payment_request_id, exclusive_token.address, {"from": pr_and_nft}
    )
    assert tx.status == Status.Confirmed
    assert_expected_events_occurred_for_successful_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
    )

    assert payment_request.isTokenAmountStatic(payment_request_id)
    assert not payment_request.isTokenAmountDynamic(payment_request_id)
    assert payment_request.isPaymentPreconditionSet(payment_request_id)
    assert not payment_request.isPaymentPostActionSet(payment_request_id)

    assert payment_request.getPostPaymentAction(payment_request_id) == ADDRESS_ZERO
    assert (
        payment_request.getPaymentPrecondition(payment_request_id)
        == precondition.address
    )
    assert payment_request.getDynamicTokenAmount(payment_request_id) == ADDRESS_ZERO
