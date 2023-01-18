import pytest
from brownie import (
    PaymentRequest,
    MyERC20,
    FixedDynamicTokenAmount,
    MyPostPaymentAction,
)
from brownie import accounts
from brownie.network.account import Account
from brownie.network.transaction import TransactionReceipt, Status
from brownie.test import given, strategy
from hypothesis import example
from web3.constants import ADDRESS_ZERO

from scripts.utils.contract import ContractBuilder
from tests.asserters import assert_expected_events_occurred_for_successful_transaction, \
    assert_dynamic_token_amount_event_is_correct, assert_static_token_amount_event_is_correct


@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass

@example(price_in_tokens=0, use_separate_account_for_pay=True)
@example(price_in_tokens=0, use_separate_account_for_pay=False)
@given(
    price_in_tokens=strategy("uint256", min_value=0, max_value=9999),
    use_separate_account_for_pay=strategy("bool"),
)
def test_GIVEN_static_prices_and_post_payment_action_WHEN_payment_is_succesfull_THEN_payment_action_is_executed(
    price_in_tokens: int, use_separate_account_for_pay: bool, *args, **kwargs
):
    # GIVEN

    deployer: Account = accounts[0]
    payee: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    post_payment_action: MyPostPaymentAction = contract_builder.MyPostPaymentAction
    payment_request: PaymentRequest = contract_builder.PaymentRequest
    erc_20_first: MyERC20 = contract_builder.MyERC20
    erc_20_second: MyERC20 = contract_builder.MyERC20
    payee_from_account: Account = payee if use_separate_account_for_pay else deployer

    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [str(erc_20_first.address), price_in_tokens],
            [str(erc_20_second.address), price_in_tokens],
        ],
        ADDRESS_ZERO,
        post_payment_action.address,
    )
    assert tx.status == Status.Confirmed
    payment_request_id: int = tx.return_value

    # WHEN
    if use_separate_account_for_pay:
        erc_20_second.transfer(payee.address, price_in_tokens, {"from": deployer})

    erc_20_second.approve(
        payment_request.address, price_in_tokens, {"from": payee_from_account}
    )

    tx = payment_request.pay(
        payment_request_id, erc_20_second.address, {"from": payee_from_account}
    )

    # THEN
    assert tx.status == Status.Confirmed
    assert_expected_events_occurred_for_successful_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
    )

    receipt_id: int = tx.return_value
    receipt_addr: str = payment_request.receipt()

    assert_static_token_amount_event_is_correct(
        events=tx.events,
        receipt_addr=receipt_addr,
        receipt_id=receipt_id,
        receipt_token_addr=erc_20_second.address,
        receipt_token_amount=price_in_tokens,
        payer=payee_from_account.address,
        payee=deployer.address,
        beneficiary=deployer.address,
        payment_precondition_addr=ADDRESS_ZERO,
        payment_request_token_addr=erc_20_first,
        payment_request_token_price=price_in_tokens,
    )

    assert payment_request.isTokenAmountStatic(payment_request_id)
    assert not payment_request.isTokenAmountDynamic(payment_request_id)
    assert not payment_request.isPaymentPreconditionSet(payment_request_id)
    assert payment_request.isPaymentPostActionSet(payment_request_id)

    assert (
        payment_request.getPostPaymentAction(payment_request_id)
        == post_payment_action.address
    )
    assert (
        payment_request.getPaymentPrecondition(payment_request_id) == ADDRESS_ZERO
    )
    assert payment_request.getDynamicTokenAmount(payment_request_id) == ADDRESS_ZERO


@example(price_in_tokens=0, use_separate_account_for_pay=True)
@example(price_in_tokens=0, use_separate_account_for_pay=False)
@given(
    price_in_tokens=strategy("uint256", min_value=0, max_value=9999),
    use_separate_account_for_pay=strategy("bool"),
)
def test_GIVEN_dynamic_prices_and_post_payment_action_WHEN_payment_is_succesfull_THEN_payment_action_is_executed(
    price_in_tokens: int, use_separate_account_for_pay: bool, *args, **kwargs
):
    # GIVEN

    deployer: Account = accounts[0]
    payee: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    post_payment_action: MyPostPaymentAction = contract_builder.MyPostPaymentAction
    payment_request: PaymentRequest = contract_builder.PaymentRequest
    erc_20: MyERC20 = contract_builder.MyERC20
    payee_from_account: Account = payee if use_separate_account_for_pay else deployer

    price_computer: FixedDynamicTokenAmount = (
        contract_builder.get_fixed_token_amount_computer(
            price=price_in_tokens, account=deployer, force_deploy=True
        )
    )
    assert price_in_tokens == price_computer.price()

    tx: TransactionReceipt = payment_request.createWithDynamicTokenAmount(
        price_computer.address,
        ADDRESS_ZERO,
        post_payment_action.address,
    )

    assert tx.status == Status.Confirmed
    payment_request_id: int = tx.return_value

    # WHEN
    if use_separate_account_for_pay:
        erc_20.transfer(payee.address, price_in_tokens, {"from": deployer})

    erc_20.approve(
        payment_request.address, price_in_tokens, {"from": payee_from_account}
    )

    tx = payment_request.pay(
        payment_request_id, erc_20.address, {"from": payee_from_account}
    )

    # THEN
    assert tx.status == Status.Confirmed
    assert_expected_events_occurred_for_successful_transaction(
        payment_request=payment_request,
        payment_request_id=payment_request_id,
        tx=tx,
    )

    receipt_id: int = tx.return_value
    receipt_addr: str = payment_request.receipt()

    assert_dynamic_token_amount_event_is_correct(
        events=tx.events,
        receipt_addr=receipt_addr,
        receipt_id=receipt_id,
        receipt_token_addr=erc_20.address,
        receipt_token_amount=price_in_tokens,
        payer=payee_from_account.address,
        payee=deployer.address,
        beneficiary=deployer.address,
        payment_precondition_addr=ADDRESS_ZERO,
    )

    assert not payment_request.isTokenAmountStatic(payment_request_id)
    assert payment_request.isTokenAmountDynamic(payment_request_id)
    assert not payment_request.isPaymentPreconditionSet(payment_request_id)
    assert payment_request.isPaymentPostActionSet(payment_request_id)

    assert (
        payment_request.getPostPaymentAction(payment_request_id)
        == post_payment_action.address
    )
    assert (
        payment_request.getPaymentPrecondition(payment_request_id) == ADDRESS_ZERO
    )
    assert (
        payment_request.getDynamicTokenAmount(payment_request_id)
        == price_computer.address
    )
