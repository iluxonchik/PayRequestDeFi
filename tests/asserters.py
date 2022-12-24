from typing import Optional, List

import pytest
from brownie import Receipt
from brownie.network.contract import ProjectContract
from brownie.network.event import EventDict, _EventItem
from brownie.network.transaction import TransactionReceipt

from scripts.utils.contants import EventName, ExpectedEventsFor


def assert_receipt_metadata_is_correct(*, receipt: Receipt, receipt_id: int, payment_request_addr: str, payment_request_id: int, token_addr: str, token_amount: int, payer_addr: str, payee_addr: str):
    assert receipt.getReceiptData(receipt_id) == (payment_request_addr, payment_request_id, token_addr, token_amount, payer_addr, payee_addr)

def assert_dynamic_token_amount_event_is_correct(*,
                                                 events: Optional[EventDict],
                                                 receipt_addr: str,
                                                 receipt_id: int,
                                                 receipt_token_addr: str,
                                                 receipt_token_amount: int,
                                                 payer: str, payee: str,
                                                 payment_precondition_addr: str):
    if not events:
        pytest.fail("Passed events are None or empty")

    event_data: _EventItem = events[EventName.DYNAMIC_TOKEN_AMOUNT_PPA_EXECUTED]
    assert event_data == {
        "receipt": receipt_addr,
        "receiptId": receipt_id,
        "receiptToken": receipt_token_addr,
        "receiptTokenAmount": receipt_token_amount,
        "payer": payer,
        "payee": payee,
        "paymentPrecondition": payment_precondition_addr,
    }
def assert_static_token_amount_event_is_correct(*,
                                                events: Optional[EventDict],
                                                receipt_addr: str,
                                                receipt_id: int,
                                                receipt_token_addr: str,
                                                receipt_token_amount: int,
                                                payer: str, payee: str,
                                                payment_precondition_addr: str,
                                                payment_request_token_addr: str,
                                                payment_request_token_price: int):
    if not events:
        pytest.fail("Passed events are None or empty")
    event_data: _EventItem = events[EventName.STATIC_TOKEN_AMOUNT_PPA_EXECUTED]
    assert event_data == {
        "receipt": receipt_addr,
        "receiptId": receipt_id,
        "receiptToken": receipt_token_addr,
        "receiptTokenAmount": receipt_token_amount,
        "payer": payer,
        "payee": payee,
        "paymentPrecondition": payment_precondition_addr,
        "paymentRequestToken": payment_request_token_addr,
        "paymentRequestTokenAmount": payment_request_token_price,
    }

def assert_expected_events_occurred_for_successful_transaction(*, payment_request: ProjectContract, payment_request_id: int, tx: TransactionReceipt) -> List[str]:
    PP_PPA_TO_EXPECTED_EVENTS: dict[tuple[bool, bool], list[str]] = {
        (True, False): ExpectedEventsFor.Success.PP.NoPPA,
        (True, True): ExpectedEventsFor.Success.PP.PPA,
        (False, False): ExpectedEventsFor.Success.NoPP.NoPPA,
        (False, True): ExpectedEventsFor.Success.NoPP.PPA,
    }
    is_payment_precondition_set: bool = payment_request.isPaymentPreconditionSet(payment_request_id)
    is_post_payment_action_set: bool = payment_request.isPaymentPostActionSet(payment_request_id)

    expected_events: List[str] = PP_PPA_TO_EXPECTED_EVENTS[(is_payment_precondition_set, is_post_payment_action_set)]

    for event in expected_events:
        assert event in tx.events, f"{event} not in {tx.events}"

    not_expected_events: List[str] = list( set(EventName.APP_SPECIFIC) - set(expected_events))
    for event in not_expected_events:
        assert event not in tx.events, f"{event} in {tx.events}"



def _get_expected_events_for_failure(is_payment_precondition_set: bool, is_post_payment_action_set: bool, failed_at: str) -> List[str]:
    PP_PPA_TO_EXPECTED_EVENTS: dict[tuple[bool, bool], type] = {
        (True, False): ExpectedEventsFor.Failure.PP.NoPPA.FailAt,
        (True, True): ExpectedEventsFor.Failure.PP.PPA.FailAt,
        (False, False): ExpectedEventsFor.Failure.NoPP.NoPPA.FailAt,
        (False, True): ExpectedEventsFor.Failure.NoPP.PPA.FailAt,
    }

    return getattr(PP_PPA_TO_EXPECTED_EVENTS[(is_payment_precondition_set, is_post_payment_action_set)], failed_at)

def assert_expected_events_occurred_for_failed_transaction(*, payment_request: ProjectContract, payment_request_id: int, tx: TransactionReceipt, failed_at: str):
    is_payment_precondition_set: bool = payment_request.isPaymentPreconditionSet(payment_request_id)
    is_post_payment_action_set: bool = payment_request.isPaymentPostActionSet(payment_request_id)

    expected_events: list[str] = _get_expected_events_for_failure(is_payment_precondition_set, is_post_payment_action_set, failed_at)

    for event in expected_events:
        assert event in tx.events, f"{event} not in {tx.events}"

    not_expected_events: List[str] = list( set(EventName.APP_SPECIFIC) - set(expected_events))
    for event in not_expected_events:
        assert event not in tx.events, f"{event} in {tx.events}"
