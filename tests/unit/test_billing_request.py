"""
Tests related to billing request.
"""
from typing import Tuple

import pytest
from brownie import network, BillingRequest, MyERC20, accounts
from brownie.exceptions import VirtualMachineError
from brownie.network.account import Account
from brownie.network.contract import ProjectContract
from brownie.network.transaction import TransactionReceipt, Status

from scripts.contants import LOCAL_BLOCKCHAIN_ENVIRONMENTS

# TODO: move to decorator/pytest groups
def skip_if_not_local_blockchain():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Not in a local blockchain environment.")


def test_GIVEN_billing_request_WHEN_deployed_THEN_deployment_succeeds(*args, **kwargs):
    skip_if_not_local_blockchain()

    account: Account = accounts[0]

    br = BillingRequest.deploy({"from": account})
    assert br.tx is not None
    assert br.tx.status == Status.Confirmed

def test_GIVEN_billing_request_creation_WHEN_no_prices_are_provided_THEN_billing_request_creation_fails(*args, **kwargs):
    OKEN_AMOUNT: int = 1
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    br: ProjectContract = BillingRequest.deploy({"from": deployer})
    erc20: ProjectContract = MyERC20.deploy("illya", "ILY", 1, {"from": deployer})

    # WHEN
    with pytest.raises(ValueError):
        br.create([], {"from": interactor})


def test_GIVEN_single_token_price_pair_from_non_deployer_account_WHEN_billing_request_created_THEN_internal_state_is_correct(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT: int = 1
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    br: ProjectContract = BillingRequest.deploy({"from": deployer})
    erc20: ProjectContract = MyERC20.deploy("illya", "ILY", 1, {"from": deployer})

    # WHEN
    tx: TransactionReceipt = br.create([[str(erc20.address), TOKEN_AMOUNT]], {"from": interactor})
    assert tx.status == Status.Confirmed

    # THEN
    assert br.tokenIdsCreatedByAddr(interactor.address, 0) == 0
    with pytest.raises(ValueError):
        # only one token created
        br.tokenIdsCreatedByAddr(interactor.address, 1)

    EXPECTED_PRICE_STRUCT: Tuple[int, bool] = (TOKEN_AMOUNT, True)
    assert br.tokenIdToPriceMap(0, erc20.address) == EXPECTED_PRICE_STRUCT
    # interactor.address is not a token payment address that was added
    assert br.tokenIdToPriceMap(0, interactor.address) == (0, False)
    # price 0 for tokenId 0
    assert br.tokenIdToPriceArray(0, 0) == (erc20.address, TOKEN_AMOUNT)

    with pytest.raises(ValueError):
        # only one price added
        br.tokenIdToPriceArray(0, 1)

def test_GIVEN_multiple_token_price_pair_from_non_deployer_account_WHEN_billing_request_created_THEN_internal_state_is_correct(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT_ONE: int = 1
    TOKEN_AMOUNT_TWO: int = 1
    TOKEN_AMOUNT_THREE: int = 1
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    br: ProjectContract = BillingRequest.deploy({"from": deployer})
    erc20_one: ProjectContract = MyERC20.deploy("illya", "ILY", 123, {"from": deployer})
    erc20_two: ProjectContract = MyERC20.deploy("not illya", "NOTILY", 321, {"from": deployer})
    erc20_three: ProjectContract = MyERC20.deploy("maybe illya", "MAYBEILY", 213, {"from": deployer})

    # WHEN
    tx: TransactionReceipt = br.create([[str(erc20_one.address), TOKEN_AMOUNT_ONE],
                                        [str(erc20_two.address), TOKEN_AMOUNT_TWO],
                                        [str(erc20_three.address), TOKEN_AMOUNT_THREE]],
                                       {"from": interactor})
    assert tx.status == Status.Confirmed

    # THEN
    assert br.tokenIdsCreatedByAddr(interactor.address, 0) == 0

    with pytest.raises(ValueError):
        # only one token created
        br.tokenIdsCreatedByAddr(interactor.address, 1)

    EXPECTED_PRICE_STRUCT_ONE: Tuple[int, bool] = (TOKEN_AMOUNT_ONE, True)
    EXPECTED_PRICE_STRUCT_TWO: Tuple[int, bool] = (TOKEN_AMOUNT_TWO, True)
    EXPECTED_PRICE_STRUCT_THREE: Tuple[int, bool] = (TOKEN_AMOUNT_THREE, True)
    assert br.tokenIdToPriceMap(0, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE
    assert br.tokenIdToPriceMap(0, erc20_two.address) == EXPECTED_PRICE_STRUCT_TWO
    assert br.tokenIdToPriceMap(0, erc20_three.address) == EXPECTED_PRICE_STRUCT_THREE

    # interactor.address is not a token payment address that was added
    assert br.tokenIdToPriceMap(0, interactor.address) == (0, False)

    # price 0 for tokenId 0
    assert br.tokenIdToPriceArray(0, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)
    assert br.tokenIdToPriceArray(0, 1) == (erc20_two.address, TOKEN_AMOUNT_TWO)
    assert br.tokenIdToPriceArray(0, 2) == (erc20_three.address, TOKEN_AMOUNT_THREE)

    with pytest.raises(ValueError):
        # only 3 prices were added
        br.tokenIdToPriceArray(0, 3)

def test_GIVEN_multiple_token_price_pair_from_deployer_account_WHEN_billing_request_created_by_multiple_interactors_THEN_internal_state_is_correct(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT_ONE: int = 1
    TOKEN_AMOUNT_TWO: int = 1
    TOKEN_AMOUNT_THREE: int = 1
    deployer: Account = accounts[0]
    interactor_one: Account = accounts[1]
    interactor_two: Account = accounts[2]
    interactor_three: Account = accounts[3]

    br: ProjectContract = BillingRequest.deploy({"from": deployer})
    erc20_one: ProjectContract = MyERC20.deploy("illya", "ILY", 123, {"from": deployer})
    erc20_two: ProjectContract = MyERC20.deploy("not illya", "NOTILY", 321, {"from": deployer})
    erc20_three: ProjectContract = MyERC20.deploy("maybe illya", "MAYBEILY", 213, {"from": deployer})

    # WHEN

    ## first interactor
    tx1: TransactionReceipt = br.create([[str(erc20_one.address), TOKEN_AMOUNT_ONE],
                                        [str(erc20_two.address), TOKEN_AMOUNT_TWO],
                                        [str(erc20_three.address), TOKEN_AMOUNT_THREE]],
                                        {"from": interactor_one})

    assert tx1.status == Status.Confirmed

    ## second intreactor
    tx2: TransactionReceipt = br.createWithCustomPayee([[str(erc20_one.address), TOKEN_AMOUNT_ONE]], interactor_two.address, {"from": interactor_two})
    assert tx2.status == Status.Confirmed

    ### second interactor creates one more billing request, same as above
    tx2 = br.create([[str(erc20_one.address), TOKEN_AMOUNT_ONE]], {"from": interactor_two})
    assert tx2.status == Status.Confirmed

    tx3: TransactionReceipt = br.createWithCustomPayee([
        [str(erc20_one.address), TOKEN_AMOUNT_ONE],
        [str(erc20_three.address), TOKEN_AMOUNT_THREE],
    ], interactor_three.address, {"from": interactor_two})

    assert tx3.status == Status.Confirmed


    # THEN
    EXPECTED_PRICE_STRUCT_ONE: Tuple[int, bool] = (TOKEN_AMOUNT_ONE, True)
    EXPECTED_PRICE_STRUCT_TWO: Tuple[int, bool] = (TOKEN_AMOUNT_TWO, True)
    EXPECTED_PRICE_STRUCT_THREE: Tuple[int, bool] = (TOKEN_AMOUNT_THREE, True)

    ## checks for first interactor
    assert br.tokenIdsCreatedByAddr(interactor_one.address, 0) == 0

    with pytest.raises(ValueError):
        # only one token created
        br.tokenIdsCreatedByAddr(interactor_one.address, 1)

    assert br.tokenIdToPriceMap(0, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE
    assert br.tokenIdToPriceMap(0, erc20_two.address) == EXPECTED_PRICE_STRUCT_TWO
    assert br.tokenIdToPriceMap(0, erc20_three.address) == EXPECTED_PRICE_STRUCT_THREE

    # interactor.address is not a token payment address that was added
    assert br.tokenIdToPriceMap(0, interactor_one.address) == (0, False)

    # price 0 for tokenId 0
    assert br.tokenIdToPriceArray(0, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)
    assert br.tokenIdToPriceArray(0, 1) == (erc20_two.address, TOKEN_AMOUNT_TWO)
    assert br.tokenIdToPriceArray(0, 2) == (erc20_three.address, TOKEN_AMOUNT_THREE)

    with pytest.raises(ValueError):
        # only 3 prices were added
        br.tokenIdToPriceArray(0, 3)

    ## checks for second interactor
    assert br.tokenIdsCreatedByAddr(interactor_two.address, 0) == 1
    # second interactor created one more NFT for itself
    assert br.tokenIdsCreatedByAddr(interactor_two.address, 1) == 2
    # second interactor created one token for interactor 3
    assert br.tokenIdsCreatedByAddr(interactor_two.address, 2) == 3

    with pytest.raises(ValueError):
        # only threes tokens created
        br.tokenIdsCreatedByAddr(interactor_one.address, 3)
    # token IDs created by interactor 2: 1, 2, 3
    # token IDs owned by interactor 2: 1, 2 | both contain the same price
    assert br.tokenIdToPriceMap(1, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE
    assert br.tokenIdToPriceMap(2, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE

    # erc20_two.address is not a token payment address that was added
    assert br.tokenIdToPriceMap(1, erc20_two.address) == (0, False)

    # prices 0 tokenId 1 and 2
    assert br.tokenIdToPriceArray(1, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)
    assert br.tokenIdToPriceArray(2, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)

    with pytest.raises(ValueError):
        # only 1 price was added to token 1
        br.tokenIdToPriceArray(1, 1)

    with pytest.raises(ValueError):
        # only 1 price was added to token 2
        br.tokenIdToPriceArray(2, 1)

    ## checks for third interactor
    with pytest.raises(ValueError):
        # the token was created by second interactor
        br.tokenIdsCreatedByAddr(interactor_three.address, 0)

    # token IDs created by interactor 3: _
    # token IDs owned by interactor 3: 3
    assert br.tokenIdToPriceMap(3, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE
    assert br.tokenIdToPriceMap(3, erc20_three.address) == EXPECTED_PRICE_STRUCT_THREE

    # erc20_two.address is not a token payment address that was added
    assert br.tokenIdToPriceMap(3, erc20_two.address) == (0, False)

    # prices 0 and 1 of tokenId 3
    assert br.tokenIdToPriceArray(3, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)
    assert br.tokenIdToPriceArray(3, 1) == (erc20_three.address, TOKEN_AMOUNT_THREE)

    with pytest.raises(ValueError):
        # only 2 price were added for token 3
        br.tokenIdToPriceArray(3, 2)
