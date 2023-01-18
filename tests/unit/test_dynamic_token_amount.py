import random

import pytest
from brownie import PaymentRequest, MyERC20, Receipt, FixedDynamicTokenAmount
from brownie import accounts
from brownie.exceptions import VirtualMachineError
from brownie.network.account import Account
from brownie.network.contract import Contract
from brownie.network.transaction import TransactionReceipt, Status
from brownie.test import given, strategy
from web3.constants import ADDRESS_ZERO

from scripts.utils.contants import PaymentFailedAt
from scripts.utils.contract import ContractBuilder
from scripts.utils.environment import is_local_blockchain_environment
from tests.asserters import (
    assert_expected_events_occurred_for_successful_transaction,
    assert_expected_events_occurred_for_failed_transaction, assert_receipt_metadata_is_correct,
)
from tests.dto import IntegerValue, IntegerValueRange, ValueRange

@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass

@pytest.mark.parametrize("price_in_tokens_integer_range", [IntegerValue(value=0), IntegerValueRange(min_value=1, max_value=999)])
def test_GIVEN_fixed_price_computer_function_WHEN_attempt_to_purchase_is_made_THEN_purchase_with_correct_amount_is_done(
    price_in_tokens_integer_range: ValueRange, *args, **kwargs
):
    # GIVEN
    # python-xdist does not function correctly when random values in pytest parameterization are used
    price_in_tokens: list[int] = random.randint(price_in_tokens_integer_range.min_value, price_in_tokens_integer_range.max_value)
    deployer: Account = accounts[0]
    purchaser: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )

    price_computer: FixedDynamicTokenAmount = (
        contract_builder.get_fixed_token_amount_computer(
            price=price_in_tokens, account=deployer, force_deploy=True
        )
    )
    assert price_in_tokens == price_computer.price()

    payment_request: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithDynamicTokenAmount(
        price_computer.address, ADDRESS_ZERO, ADDRESS_ZERO, {"from": deployer}
    )

    assert tx.status == Status.Confirmed
    payment_request_id: int = tx.return_value

    erc_20: MyERC20 = contract_builder.MyERC20
    erc_20.transfer(purchaser.address, price_in_tokens, {"from": deployer})

    if price_in_tokens > 0:
        erc_20.approve(payment_request.address, price_in_tokens, {"from": purchaser})

    # WHEN
    tx = payment_request.pay(payment_request_id, erc_20.address, {"from": purchaser})

    # THEN
    assert tx.status == Status.Confirmed
    assert_expected_events_occurred_for_successful_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
    )

    receipt_addr: str = payment_request.receipt()
    receipt: Receipt = Contract.from_abi("Receipt", receipt_addr, Receipt.abi)
    assert receipt.balanceOf(purchaser.address) == 1
    assert_receipt_metadata_is_correct(
        receipt=receipt,
        receipt_id=0,
        payment_request_addr=payment_request.address,
        payment_request_id=payment_request_id,
        token_addr=erc_20.address,
        token_amount=price_in_tokens,
        payer_addr=purchaser.address,
        payee_addr=deployer.address,
        beneficiary_addr=purchaser.address,
    )
    assert not payment_request.isTokenAmountStatic(payment_request_id)
    assert payment_request.isTokenAmountDynamic(payment_request_id)
    assert not payment_request.isPaymentPreconditionSet(payment_request_id)
    assert not payment_request.isPaymentPostActionSet(payment_request_id)

    assert payment_request.getPostPaymentAction(payment_request_id) == ADDRESS_ZERO
    assert (
        payment_request.getPaymentPrecondition(payment_request_id) == ADDRESS_ZERO
    )
    assert (
        payment_request.getDynamicTokenAmount(payment_request_id)
        == price_computer.address
    )

@given(price_in_tokens=strategy("int256", max_value=-1, min_value=-99999))
def test_GIVEN_price_computer_returning_negative_price_WHEN_price_computer_is_instantiated_THEN_instantiation_fails(
    price_in_tokens: int, *args, **kwargs
):
    # GIVEN
    deployer: Account = accounts[0]
    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    with pytest.raises(OverflowError):
        contract_builder.get_fixed_token_amount_computer(
            price=price_in_tokens, account=deployer, force_deploy=True
        )


@given(price_in_tokens=strategy("uint256", min_value=1, max_value=9999))
def test_GIVEN_price_computer_WHEN_paying_and_approving_less_tokens_than_necessary_THEN_purchase_fails(
    price_in_tokens: int, *args, **kwargs
):
    # GIVEN
    deployer: Account = accounts[0]
    purchaser: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )

    price_computer: FixedDynamicTokenAmount = (
        contract_builder.get_fixed_token_amount_computer(
            price=price_in_tokens, account=deployer, force_deploy=True
        )
    )
    assert price_in_tokens == price_computer.price()
    tokens_to_approve: int = price_in_tokens - 1

    payment_request: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithDynamicTokenAmount(
        price_computer.address, ADDRESS_ZERO, ADDRESS_ZERO, {"from": deployer}
    )

    assert tx.status == Status.Confirmed
    payment_request_id: int = tx.return_value

    erc_20: MyERC20 = contract_builder.MyERC20
    erc_20.transfer(purchaser.address, price_in_tokens, {"from": deployer})

    erc_20.approve(payment_request.address, tokens_to_approve, {"from": purchaser})

    # WHEN / THEN
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(payment_request_id, erc_20.address, {"from": purchaser})

    tx: TransactionReceipt = TransactionReceipt(e.value.txid)
    assert tx.status == Status.Reverted
    assert_expected_events_occurred_for_failed_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
        failed_at=PaymentFailedAt.TOKEN_BALANCE_OR_APPROVAL,
    )

    receipt_addr: str = payment_request.receipt()
    receipt: Receipt = Contract.from_abi("Receipt", receipt_addr, Receipt.abi)
    assert receipt.balanceOf(purchaser.address) == 0
