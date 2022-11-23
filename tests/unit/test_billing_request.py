"""
Tests related to billing request.
"""
import pytest
from brownie import network, BillingRequest, accounts
from brownie.network.account import Account

from scripts.contants import LOCAL_BLOCKCHAIN_ENVIRONMENTS


def test_GIVEN_billing_request_WHEN_deployed_THEN_deployment_succeeds(*args, **kwargs):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Not in a local blockchain environment.")

    account: Account = accounts[0]

    br = BillingRequest.deploy({"from": account})
    assert br.tx is not None



