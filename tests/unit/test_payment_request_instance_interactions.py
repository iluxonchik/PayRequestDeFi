import pytest
from brownie import PaymentRequest, MyERC20
from brownie import accounts
from brownie.exceptions import VirtualMachineError
from brownie.network.account import Account
from brownie.network.transaction import TransactionReceipt, Status
from web3.constants import ADDRESS_ZERO

from scripts.utils.contract import ContractBuilder

@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass

# Payment Request Enable/Disable Tests
def test_GIVEN_deployed_contract_WHEN_owner_attempting_to_disable_and_enable_THEN_it_succeeds_and_correct_events_are_emitted(
    *args, **kwargs
):
    # GIVEN
    TOKEN_AMOUNT: int = 6
    account: Account = accounts[0]
    contract_builder: ContractBuilder = ContractBuilder(account=account)
    erc_20: MyERC20 = contract_builder.MyERC20

    pr: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = pr.createWithStaticTokenAmount(
        [[str(erc_20.address), TOKEN_AMOUNT]],
        ADDRESS_ZERO,
        ADDRESS_ZERO,
        {"from": account},
    )

    assert tx.status == Status.Confirmed
    created_token_id: int = tx.return_value
    assert pr.isEnabled(created_token_id, {"from": account}) == True

    # WHEN/THEN
    tx = pr.disable(created_token_id, {"from": account})
    assert pr.isEnabled(created_token_id, {"from": account}) == False
    assert "PaymentRequestDisabled" in tx.events

    # intentional duplicate disable, ensure event not emitted
    tx = pr.disable(created_token_id, {"from": account})
    assert pr.isEnabled(created_token_id, {"from": account}) == False
    assert "PaymentRequestEnabled" not in tx.events

    tx = pr.enable(created_token_id, {"from": account})
    assert pr.isEnabled(created_token_id, {"from": account}) == True
    assert "PaymentRequestEnabled" in tx.events

    # intentional duplicate enable, ensure event not emitted
    tx = pr.enable(created_token_id, {"from": account})
    assert pr.isEnabled(created_token_id, {"from": account}) == True
    assert "PaymentRequestEnabled" not in tx.events


def test_GIVEN_deployed_contract_WHEN_non_owner_attempting_to_disable_and_enable_THEN_it_fails(
    *args, **kwargs
):
    # GIVEN
    TOKEN_AMOUNT: int = 6
    owner: Account = accounts[0]
    not_owner: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=owner)

    pr: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = pr.createWithStaticTokenAmount(
        [[str(pr.address), TOKEN_AMOUNT]], ADDRESS_ZERO, ADDRESS_ZERO, {"from": owner}
    )

    assert tx.status == Status.Confirmed
    created_token_id: int = tx.return_value

    # WHEN/THEN
    with pytest.raises(VirtualMachineError):
        pr.enable(created_token_id, {"from": not_owner})

    with pytest.raises(VirtualMachineError):
        pr.disable(created_token_id, {"from": not_owner})
