import pytest
from brownie import accounts
from brownie.network.account import Account
from hypothesis import given, strategies
from brownie.test import strategy


from tests.configuration import (
    PaymentPrecondition,
    PaymentRequestTestProxy,
)
from tests.integration.accounts import INTERACTOR_ACCOUNT_INDEX_START, INTERACTOR_ACCOUNT_INDEX_END
from tests.strategies import (
    payment_request_test_proxy_strategy,
)


@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass

@given(
    test_proxy=payment_request_test_proxy_strategy(
        precondition_id=strategies.just(
            PaymentPrecondition.NONE.value
        ),  # TODO: limited temporarily
        post_payment_action_id=strategies.integers(
            min_value=0,
            max_value=1,
        ),  # TODO: limited temporarily
    ),
    interactor_account_index=strategies.integers(min_value=INTERACTOR_ACCOUNT_INDEX_START, max_value=INTERACTOR_ACCOUNT_INDEX_END),
)
def test_GIVEN_payment_request_configuration_WHEN_payment_request_is_attempted_with_correct_parameters_THEN_expected_effects_are_observed(
    test_proxy: PaymentRequestTestProxy, interactor_account_index: int, *args, **kwargs
):
    interactor_account: Account = accounts[interactor_account_index]
    payment_request_id: int = test_proxy.create_payment_request()
    test_proxy.pay_for_payment_request_with_success(
        payment_request_id,
        interactor_account,
    )

