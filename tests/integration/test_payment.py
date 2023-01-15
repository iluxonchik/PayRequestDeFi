import pytest
from brownie import accounts
from hypothesis import given
from web3.constants import ADDRESS_ZERO

from scripts.utils.environment import is_local_blockchain_environment
from tests.configuration import PaymentRequestConfiguration
from tests.strategies import payment_request_configuration_strategy


@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass



@given(configuration=payment_request_configuration_strategy())
def test_GIVEN_payment_request_configuration_WHEN_payment_request_is_attempted_with_correct_parameters_THEN_expected_effects_are_observed(configuration: PaymentRequestConfiguration, *args, **kwargs):
    pass
