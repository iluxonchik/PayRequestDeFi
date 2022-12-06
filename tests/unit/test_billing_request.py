"""
Tests related to payment request.

The tests in this test file are fully self-contained, do not assume any state properties of the underlying blockchain
environment and can run on either fresh or already existing blockchain state.
"""
from typing import Tuple

import pytest
from brownie import network, accounts
from brownie import PaymentRequest, MyERC20, MyERC721, Receipt, NFTOwnerPaymentPrecondition
from brownie.exceptions import VirtualMachineError
from brownie.network.account import Account
from brownie.network.contract import ProjectContract
from brownie.network.transaction import TransactionReceipt, Status
from web3.constants import ADDRESS_ZERO

from scripts.utils.contants import LOCAL_BLOCKCHAIN_ENVIRONMENTS
from scripts.utils.contract import ContractBuilder
from scripts.utils.types import NFTOwnerPaymentPreconditionMeta, NFTOwnerPaymentPreconditionWithMeta


# TODO: move to decorator/pytest groups
def skip_if_not_local_blockchain():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Not in a local blockchain environment.")


def test_GIVEN_payment_request_WHEN_deployed_THEN_deployment_succeeds(*args, **kwargs):
    skip_if_not_local_blockchain()

    account: Account = accounts[0]
    contract_builder: ContractBuilder = ContractBuilder(account=account, force_deploy=True)
    rc: Receipt = ContractBuilder.get_receipt_contract(account=account, force_deploy=True)
    pr: ProjectContract = contract_builder.get_payment_request_contract(receipt=rc, account=account, force_deploy=True)

    assert rc.tx is not None, "Receipt failed to deploy"
    assert rc.tx.status == Status.Confirmed

    assert pr.tx is not None, "PaymentRequest failed to deploy"
    assert pr.tx.status == Status.Confirmed

def test_GIVEN_payment_request_creation_WHEN_no_prices_are_provided_THEN_payment_request_creation_fails(*args, **kwargs):
    OKEN_AMOUNT: int = 1
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    pr: ProjectContract = contract_builder.PaymentRequest

    erc20: ProjectContract = MyERC20.deploy("illya", "ILY", 1, {"from": deployer})

    # WHEN
    with pytest.raises(VirtualMachineError):
        pr.createWithStaticPrice([], ADDRESS_ZERO, ADDRESS_ZERO, {"from": interactor})


def test_GIVEN_single_token_price_pair_from_non_deployer_account_WHEN_payment_request_created_THEN_internal_state_is_correct(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT: int = 1
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    pr: ProjectContract = contract_builder.PaymentRequest

    erc20: ProjectContract = MyERC20.deploy("illya", "ILY", 1, {"from": deployer})

    # WHEN
    tx: TransactionReceipt = pr.createWithStaticPrice([[str(erc20.address), TOKEN_AMOUNT]], ADDRESS_ZERO, ADDRESS_ZERO, {"from": interactor})
    assert tx.status == Status.Confirmed

    # THEN
    assert pr.tokenIdsCreatedByAddr(interactor.address, 0) == 0
    with pytest.raises(VirtualMachineError):
        # only one token created
        pr.tokenIdsCreatedByAddr(interactor.address, 1)

    EXPECTED_PRICE_STRUCT: Tuple[int, bool] = (TOKEN_AMOUNT, True)
    assert pr.tokenIdToPriceMap(0, erc20.address) == EXPECTED_PRICE_STRUCT
    # interactor.address is not a token payment address that was added
    assert pr.tokenIdToPriceMap(0, interactor.address) == (0, False)
    # price 0 for tokenId 0
    assert pr.tokenIdToPriceArray(0, 0) == (erc20.address, TOKEN_AMOUNT)

    with pytest.raises(VirtualMachineError):
        # only one price added
        pr.tokenIdToPriceArray(0, 1)

def test_GIVEN_multiple_token_price_pair_from_non_deployer_account_WHEN_payment_request_created_THEN_internal_state_is_correct(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT_ONE: int = 1
    TOKEN_AMOUNT_TWO: int = 1
    TOKEN_AMOUNT_THREE: int = 1
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    pr: ProjectContract = contract_builder.PaymentRequest

    erc20_one: ProjectContract = MyERC20.deploy("illya", "ILY", 123, {"from": deployer})
    erc20_two: ProjectContract = MyERC20.deploy("not illya", "NOTILY", 321, {"from": deployer})
    erc20_three: ProjectContract = MyERC20.deploy("maybe illya", "MAYBEILY", 213, {"from": deployer})

    # WHEN
    tx: TransactionReceipt = pr.createWithStaticPrice([[str(erc20_one.address), TOKEN_AMOUNT_ONE],
                                        [str(erc20_two.address), TOKEN_AMOUNT_TWO],
                                        [str(erc20_three.address), TOKEN_AMOUNT_THREE]],
                                        ADDRESS_ZERO,
                                        ADDRESS_ZERO,
                                       {"from": interactor})
    assert tx.status == Status.Confirmed

    # THEN
    assert pr.tokenIdsCreatedByAddr(interactor.address, 0) == 0

    with pytest.raises(VirtualMachineError):
        # only one token created
        pr.tokenIdsCreatedByAddr(interactor.address, 1)

    EXPECTED_PRICE_STRUCT_ONE: Tuple[int, bool] = (TOKEN_AMOUNT_ONE, True)
    EXPECTED_PRICE_STRUCT_TWO: Tuple[int, bool] = (TOKEN_AMOUNT_TWO, True)
    EXPECTED_PRICE_STRUCT_THREE: Tuple[int, bool] = (TOKEN_AMOUNT_THREE, True)
    assert pr.tokenIdToPriceMap(0, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE
    assert pr.tokenIdToPriceMap(0, erc20_two.address) == EXPECTED_PRICE_STRUCT_TWO
    assert pr.tokenIdToPriceMap(0, erc20_three.address) == EXPECTED_PRICE_STRUCT_THREE

    # interactor.address is not a token payment address that was added
    assert pr.tokenIdToPriceMap(0, interactor.address) == (0, False)

    # price 0 for tokenId 0
    assert pr.tokenIdToPriceArray(0, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)
    assert pr.tokenIdToPriceArray(0, 1) == (erc20_two.address, TOKEN_AMOUNT_TWO)
    assert pr.tokenIdToPriceArray(0, 2) == (erc20_three.address, TOKEN_AMOUNT_THREE)

    with pytest.raises(VirtualMachineError):
        # only 3 prices were added
        pr.tokenIdToPriceArray(0, 3)

def test_GIVEN_multiple_token_price_pair_from_deployer_account_WHEN_payment_request_created_by_multiple_interactors_THEN_internal_state_is_correct(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT_ONE: int = 1
    TOKEN_AMOUNT_TWO: int = 1
    TOKEN_AMOUNT_THREE: int = 1
    deployer: Account = accounts[0]
    interactor_one: Account = accounts[1]
    interactor_two: Account = accounts[2]
    interactor_three: Account = accounts[3]

    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    pr: ProjectContract = contract_builder.PaymentRequest

    erc20_one: ProjectContract = MyERC20.deploy("illya", "ILY", 123, {"from": deployer})
    erc20_two: ProjectContract = MyERC20.deploy("not illya", "NOTILY", 321, {"from": deployer})
    erc20_three: ProjectContract = MyERC20.deploy("maybe illya", "MAYBEILY", 213, {"from": deployer})

    # WHEN

    ## first interactor
    tx1: TransactionReceipt = pr.createWithStaticPrice([[str(erc20_one.address), TOKEN_AMOUNT_ONE],
                                        [str(erc20_two.address), TOKEN_AMOUNT_TWO],
                                        [str(erc20_three.address), TOKEN_AMOUNT_THREE]],
                                        ADDRESS_ZERO,
                                        ADDRESS_ZERO,
                                        {"from": interactor_one})

    assert tx1.status == Status.Confirmed

    ## second intreactor
    tx2: TransactionReceipt = pr.createWithStaticPriceFor([[str(erc20_one.address), TOKEN_AMOUNT_ONE]],
                                        interactor_two.address,
                                        ADDRESS_ZERO,
                                        ADDRESS_ZERO,
                                        {"from": interactor_two})
    assert tx2.status == Status.Confirmed

    ### second interactor creates one more payment request, same as above
    tx2 = pr.createWithStaticPrice([[str(erc20_one.address), TOKEN_AMOUNT_ONE]],
                    ADDRESS_ZERO,
                    ADDRESS_ZERO,
                    {"from": interactor_two})
    assert tx2.status == Status.Confirmed

    tx3: TransactionReceipt = pr.createWithStaticPriceFor([
        [str(erc20_one.address), TOKEN_AMOUNT_ONE],
        [str(erc20_three.address), TOKEN_AMOUNT_THREE],
        ],
        interactor_three.address,
        ADDRESS_ZERO,
        ADDRESS_ZERO,
        {"from": interactor_two}
    )

    assert tx3.status == Status.Confirmed


    # THEN
    EXPECTED_PRICE_STRUCT_ONE: Tuple[int, bool] = (TOKEN_AMOUNT_ONE, True)
    EXPECTED_PRICE_STRUCT_TWO: Tuple[int, bool] = (TOKEN_AMOUNT_TWO, True)
    EXPECTED_PRICE_STRUCT_THREE: Tuple[int, bool] = (TOKEN_AMOUNT_THREE, True)

    ## checks for first interactor
    assert pr.tokenIdsCreatedByAddr(interactor_one.address, 0) == 0

    with pytest.raises(VirtualMachineError):
        # only one token created
        pr.tokenIdsCreatedByAddr(interactor_one.address, 1)

    assert pr.tokenIdToPriceMap(0, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE
    assert pr.tokenIdToPriceMap(0, erc20_two.address) == EXPECTED_PRICE_STRUCT_TWO
    assert pr.tokenIdToPriceMap(0, erc20_three.address) == EXPECTED_PRICE_STRUCT_THREE

    # interactor.address is not a token payment address that was added
    assert pr.tokenIdToPriceMap(0, interactor_one.address) == (0, False)

    # price 0 for tokenId 0
    assert pr.tokenIdToPriceArray(0, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)
    assert pr.tokenIdToPriceArray(0, 1) == (erc20_two.address, TOKEN_AMOUNT_TWO)
    assert pr.tokenIdToPriceArray(0, 2) == (erc20_three.address, TOKEN_AMOUNT_THREE)

    with pytest.raises(VirtualMachineError):
        # only 3 prices were added
        pr.tokenIdToPriceArray(0, 3)

    ## checks for second interactor
    assert pr.tokenIdsCreatedByAddr(interactor_two.address, 0) == 1
    # second interactor created one more NFT for itself
    assert pr.tokenIdsCreatedByAddr(interactor_two.address, 1) == 2
    # second interactor created one token for interactor 3
    assert pr.tokenIdsCreatedByAddr(interactor_two.address, 2) == 3

    with pytest.raises(VirtualMachineError):
        # only threes tokens created
        pr.tokenIdsCreatedByAddr(interactor_one.address, 3)
    # token IDs created by interactor 2: 1, 2, 3
    # token IDs owned by interactor 2: 1, 2 | both contain the same price
    assert pr.tokenIdToPriceMap(1, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE
    assert pr.tokenIdToPriceMap(2, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE

    # erc20_two.address is not a token payment address that was added
    assert pr.tokenIdToPriceMap(1, erc20_two.address) == (0, False)

    # prices 0 tokenId 1 and 2
    assert pr.tokenIdToPriceArray(1, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)
    assert pr.tokenIdToPriceArray(2, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)

    with pytest.raises(VirtualMachineError):
        # only 1 price was added to token 1
        pr.tokenIdToPriceArray(1, 1)

    with pytest.raises(VirtualMachineError):
        # only 1 price was added to token 2
        pr.tokenIdToPriceArray(2, 1)

    ## checks for third interactor
    with pytest.raises(VirtualMachineError):
        # the token was created by second interactor
        pr.tokenIdsCreatedByAddr(interactor_three.address, 0)

    # token IDs created by interactor 3: _
    # token IDs owned by interactor 3: 3
    assert pr.tokenIdToPriceMap(3, erc20_one.address) == EXPECTED_PRICE_STRUCT_ONE
    assert pr.tokenIdToPriceMap(3, erc20_three.address) == EXPECTED_PRICE_STRUCT_THREE

    # erc20_two.address is not a token payment address that was added
    assert pr.tokenIdToPriceMap(3, erc20_two.address) == (0, False)

    # prices 0 and 1 of tokenId 3
    assert pr.tokenIdToPriceArray(3, 0) == (erc20_one.address, TOKEN_AMOUNT_ONE)
    assert pr.tokenIdToPriceArray(3, 1) == (erc20_three.address, TOKEN_AMOUNT_THREE)

    with pytest.raises(VirtualMachineError):
        # only 2 price were added for token 3
        pr.tokenIdToPriceArray(3, 2)

def test_GIVEN_deployed_contract_WHEN_owner_attempting_to_disable_and_enable_THEN_it_succeeds_and_correct_events_are_emitted(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT: int = 6
    account: Account = accounts[0]
    contract_builder: ContractBuilder = ContractBuilder(account=account)

    pr: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = pr.createWithStaticPrice([[str(pr.address), TOKEN_AMOUNT]],
                                       ADDRESS_ZERO,
                                       ADDRESS_ZERO,
                                       {"from": account})

    assert tx.status == Status.Confirmed
    created_token_id: int = tx.value
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


def test_GIVEN_deployed_contract_WHEN_non_owner_attempting_to_disable_and_enable_THEN_it_fails(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT: int = 6
    owner: Account = accounts[0]
    not_owner: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=owner)

    pr: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = pr.createWithStaticPrice([[str(pr.address), TOKEN_AMOUNT]],
                                                      ADDRESS_ZERO,
                                                      ADDRESS_ZERO,
                                                      {"from": owner})

    assert tx.status == Status.Confirmed
    created_token_id: int = tx.value

    # WHEN/THEN
    with pytest.raises(VirtualMachineError):
        pr.enable(created_token_id, {"from": not_owner})

    with pytest.raises(VirtualMachineError):
        pr.disable(created_token_id, {"from": not_owner})

def atest_GIVEN_sample_nft_payment_precondition_WHEN_non_nft_owner_not_payment_creator_attempts_to_purchase_exclusive_token_THEN_error_occurs(*args, **kwargs):
    # GIVEN

    deployer: Account = accounts[0]
    pr_no_nft: Account = accounts[1]
    nft_no_pr: Account = accounts[2]
    no_nft_or_pr: Account = accounts[3]
    nft_and_pr: Account = accounts[4]

    deployer_contract_builder: ContractBuilder = ContractBuilder(account=deployer)
    precondition: NFTOwnerPaymentPreconditionWithMeta = deployer_contract_builder.NFTOwnerPaymentPrecondition

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(account=deployer, force_deploy=True)
    exclusive_token: MyERC20 = precondition.erc20
    exclusive_nft: MyERC721 = precondition.erc721

    # construct the main PaymentRequest
    payment_request: PaymentRequest = deployer_contract_builder.PaymentRequest
    payment_request.createWithStaticPrice(
        [
            [non_exclusive_token.address, 10],
            [exclusive_token.address, 12],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer}
    )

    # setup no NFT account
    payment_request.createWithStaticPrice(
        [
            [non_exclusive_token, 10],
        ],
        ADDRESS_ZERO,
        ADDRESS_ZERO,
        {"from": pr_no_nft}
    )

    # setup account with both, NFT and PR
    exclusive_nft.create(nft_no_pr.address, {"from": nft_no_pr})
    payment_request.createWithStaticPrice(
        [
            [non_exclusive_token, 10],
        ],
        ADDRESS_ZERO,
        ADDRESS_ZERO,
        {"from": nft_and_pr}
    )

    exclusive_nft.create(nft_no_pr.address, {"from": nft_and_pr})


def test_GIVEN_sample_nft_payment_precondition_WHEN_non_nft_owner_not_payment_creator_attempts_to_purchase_exclusive_token_THEN_error_occurs(*args, **kwargs):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    no_nft_or_pr: Account = accounts[3]

    deployer_contract_builder: ContractBuilder = ContractBuilder(account=deployer)
    precondition: NFTOwnerPaymentPreconditionWithMeta = deployer_contract_builder.NFTOwnerPaymentPrecondition

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(account=deployer, force_deploy=True)
    exclusive_token: MyERC20 = precondition.Meta.erc20

    # seed account with tokens
    non_exclusive_token.transfer(no_nft_or_pr.address, 100, {"from": deployer})
    exclusive_token.transfer(no_nft_or_pr.address, 100, {"from": deployer})

    # construct the main PaymentRequest
    payment_request: PaymentRequest = deployer_contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithStaticPrice(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer}
    )
    created_token_id: int = tx.value

    non_exclusive_token.approve(payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": no_nft_or_pr})
    with pytest.raises(VirtualMachineError):
        payment_request.pay(created_token_id, non_exclusive_token.address, {"from": no_nft_or_pr})

    exclusive_token.approve(payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": no_nft_or_pr})
    with pytest.raises(VirtualMachineError):
        payment_request.pay(created_token_id, non_exclusive_token.address, {"from": no_nft_or_pr})
