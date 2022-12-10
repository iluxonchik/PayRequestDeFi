"""
Tests related to payment request.

The tests in this test file are fully self-contained, do not assume any state properties of the underlying blockchain
environment and can run on either fresh or already existing blockchain state.
"""
import random
from typing import Tuple

from brownie.test import given, strategy
import pytest
from brownie import network, accounts
from brownie import PaymentRequest, MyERC20, MyERC721, Receipt, NFTOwnerPaymentPrecondition, FixedPricePriceComputer
from brownie.exceptions import VirtualMachineError
from brownie.network.account import Account
from brownie.network.contract import ProjectContract, Contract
from brownie.network.transaction import TransactionReceipt, Status
from web3.constants import ADDRESS_ZERO

from scripts.utils.contants import LOCAL_BLOCKCHAIN_ENVIRONMENTS
from scripts.utils.contract import ContractBuilder
from scripts.utils.types import NFTOwnerPaymentPreconditionMeta, NFTOwnerPaymentPreconditionWithMeta


# TODO: move to decorator/pytest groups
def skip_if_not_local_blockchain():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Not in a local blockchain environment.")

def assert_receipt_metadata_is_correct(*, receipt: Receipt, receipt_id: int, payment_request_addr: str, payment_request_id: int, token_addr: str, token_amount: int, payer_addr: str, payee_addr: str):
    assert receipt.receipt(receipt_id) == (payment_request_addr, payment_request_id, token_addr, token_amount, payer_addr, payee_addr)

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

# Payment Request Enable/Disable Tests
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


# Payment Precondition Tests

def test_GIVEN_sample_nft_payment_precondition_WHEN_non_nft_owner_not_payment_creator_attempts_to_purchase_exclusive_token_THEN_error_occurs(*args, **kwargs):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    no_nft_or_pr: Account = accounts[3]

    deployer_contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
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
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(created_token_id, non_exclusive_token.address, {"from": no_nft_or_pr})
        tx = TransactionReceipt(e.value.txid)
        assert tx.status == Status.Reverted
        assert "PaymentPreconditionRejected" in tx.events

    exclusive_token.approve(payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": no_nft_or_pr})
    with pytest.raises(VirtualMachineError):
        payment_request.pay(created_token_id, exclusive_token.address, {"from": no_nft_or_pr})
        tx = TransactionReceipt(e.value.txid)
        assert tx.status == Status.Reverted
        assert "PaymentPreconditionRejected" in tx.events

def test_GIVEN_sample_nft_payment_precondition_WHEN_nft_owner_not_payment_creator_attempts_to_purchase_exclusive_token_THEN_only_exclusive_token_purchase_is_allowed(*args, **kwargs):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    nft_no_pr: Account = accounts[1]

    deployer_contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    precondition: NFTOwnerPaymentPreconditionWithMeta = deployer_contract_builder.NFTOwnerPaymentPrecondition

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(account=deployer, force_deploy=True)
    exclusive_token: MyERC20 = precondition.Meta.erc20
    exclusive_nft: MyERC721 = precondition.Meta.erc721

    # seed account with tokens
    non_exclusive_token.transfer(nft_no_pr.address, 100, {"from": deployer})
    exclusive_token.transfer(nft_no_pr.address, 100, {"from": deployer})

    exclusive_nft.create(nft_no_pr.address, {"from": nft_no_pr})

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

    non_exclusive_token.approve(payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": nft_no_pr})
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(created_token_id, non_exclusive_token.address, {"from": nft_no_pr})
        tx = TransactionReceipt(e.value.txid)
        assert tx.status == Status.Reverted
        assert "PaymentPreconditionRejected" in tx.events

    exclusive_token.approve(payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": nft_no_pr})
    tx = payment_request.pay(created_token_id, exclusive_token.address, {"from": nft_no_pr})
    assert tx.status == Status.Confirmed
    assert "PaymentPreconditionRejected" not in tx.events


def test_GIVEN_sample_nft_payment_precondition_WHEN_not_nft_owner_payment_creator_attempts_to_purchase_exclusive_token_THEN_only_non_exclusive_token_purchase_is_allowed(*args, **kwargs):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    pr_no_nft: Account = accounts[1]

    deployer_contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    precondition: NFTOwnerPaymentPreconditionWithMeta = deployer_contract_builder.NFTOwnerPaymentPrecondition

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(account=deployer, force_deploy=True)
    exclusive_token: MyERC20 = precondition.Meta.erc20

    # seed account with tokens
    non_exclusive_token.transfer(pr_no_nft.address, 100, {"from": deployer})
    exclusive_token.transfer(pr_no_nft.address, 100, {"from": deployer})

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

    # deploy payment for the Non-NFT, only Payment Request owner contract
    payment_request.createWithStaticPrice(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": pr_no_nft}
    )

    non_exclusive_token.approve(payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": pr_no_nft})
    payment_request.pay(created_token_id, non_exclusive_token.address, {"from": pr_no_nft})
    assert tx.status == Status.Confirmed
    assert "PaymentPreconditionRejected" not in tx.events

    exclusive_token.approve(payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": pr_no_nft})
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(created_token_id, exclusive_token.address, {"from": pr_no_nft})
        tx = TransactionReceipt(e.value.txid)
        assert tx.status == Status.Reverted
        assert "PaymentPreconditionRejected" in tx.events

def test_GIVEN_sample_nft_payment_precondition_WHEN_nft_owner_and_payment_creator_attempts_to_purchase_exclusive_token_THEN_both_token_purchases_are_allowed(*args, **kwargs):
    # GIVEN
    NON_EXCLUSIVE_TOKEN_AMOUNT: int = 10
    EXCLUSIVE_TOKEN_AMOUNT: int = 12

    deployer: Account = accounts[0]
    pr_and_nft: Account = accounts[1]

    deployer_contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    precondition: NFTOwnerPaymentPreconditionWithMeta = deployer_contract_builder.NFTOwnerPaymentPrecondition

    # ensure new contract, distinct from original
    non_exclusive_token: MyERC20 = deployer_contract_builder.get_my_erc20_contract(account=deployer, force_deploy=True)
    exclusive_token: MyERC20 = precondition.Meta.erc20
    exclusive_nft: MyERC721 = precondition.Meta.erc721

    # seed account with tokens
    non_exclusive_token.transfer(pr_and_nft.address, 100, {"from": deployer})
    exclusive_token.transfer(pr_and_nft.address, 100, {"from": deployer})
    exclusive_nft.create(pr_and_nft.address, {"from": deployer})

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

    # deploy payment for the Non-NFT, only Payment Request owner contract
    payment_request.createWithStaticPrice(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": pr_and_nft}
    )

    non_exclusive_token.approve(payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": pr_and_nft})
    payment_request.pay(created_token_id, non_exclusive_token.address, {"from": pr_and_nft})
    assert tx.status == Status.Confirmed
    assert "PaymentPreconditionRejected" not in tx.events

    exclusive_token.approve(payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": pr_and_nft})
    payment_request.pay(created_token_id, exclusive_token.address, {"from": pr_and_nft})
    assert tx.status == Status.Confirmed
    assert "PaymentPreconditionRejected" not in tx.events

# Dynamic Price Computer Test
@pytest.mark.parametrize("price_in_tokens", [0, random.randint(1, 999)])
def test_GIVEN_fixed_price_computer_function_WHEN_attempt_to_purchase_is_made_THEN_purchase_with_correct_amount_is_done(price_in_tokens: int, *args, **kwargs):
    # GIVEN
    deployer: Account = accounts[0]
    purchaser: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)

    price_computer: FixedPricePriceComputer = contract_builder.get_fixed_price_price_computer(
        price=price_in_tokens, account=deployer, force_deploy=True
    )
    assert price_in_tokens == price_computer.price()

    payment_request: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithDynamicPrice(
        price_computer.address,
        ADDRESS_ZERO,
        ADDRESS_ZERO,
        {"from": deployer}
    )

    assert tx.status == Status.Confirmed
    pr_token_id: int = tx.value


    erc_20: MyERC20 = contract_builder.MyERC20
    erc_20.transfer(
        purchaser.address,
        price_in_tokens,
        {"from": deployer}
    )

    if price_in_tokens > 0:
        erc_20.approve(payment_request.address, price_in_tokens, {"from": purchaser})

    # WHEN
    tx = payment_request.pay(
        pr_token_id,
        erc_20.address,
        {"from": purchaser}
    )

    # THEN
    assert tx.status == Status.Confirmed

    receipt_addr: str = payment_request.receipt()
    receipt: Receipt = Contract.from_abi("Receipt", receipt_addr, Receipt.abi)
    assert receipt.balanceOf(purchaser.address) == 1
    assert_receipt_metadata_is_correct(receipt=receipt,
                                              receipt_id=0,
                                              payment_request_addr=payment_request.address,
                                              payment_request_id=pr_token_id,
                                              token_addr=erc_20.address,
                                              token_amount=price_in_tokens,
                                              payer_addr=purchaser.address,
                                              payee_addr=deployer.address,
                                              )

@given(price_in_tokens=strategy("int256", max_value=-1, min_value=-99999))
def test_GIVEN_price_computer_returning_negative_price_WHEN_price_computer_is_instantiated_THEN_instantiation_fails(price_in_tokens: int, *args, **kwargs):
    # GIVEN
    deployer: Account = accounts[0]
    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    with pytest.raises(OverflowError):
        contract_builder.get_fixed_price_price_computer(
            price=price_in_tokens, account=deployer, force_deploy=True
        )

@given(price_in_tokens=strategy("uint256", min_value=1, max_value=9999))
def test_GIVEN_price_computer_WHEN_paying_and_approving_less_tokens_than_necessary_THEN_purchase_fails(price_in_tokens: int, *args, **kwargs):
    # GIVEN
    deployer: Account = accounts[0]
    purchaser: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)

    price_computer: FixedPricePriceComputer = contract_builder.get_fixed_price_price_computer(
        price=price_in_tokens, account=deployer, force_deploy=True
    )
    assert price_in_tokens == price_computer.price()
    tokens_to_approve: int = price_in_tokens - 1

    payment_request: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithDynamicPrice(
        price_computer.address,
        ADDRESS_ZERO,
        ADDRESS_ZERO,
        {"from": deployer}
    )

    assert tx.status == Status.Confirmed
    pr_token_id: int = tx.value

    erc_20: MyERC20 = contract_builder.MyERC20
    erc_20.transfer(
        purchaser.address,
        price_in_tokens,
        {"from": deployer}
    )

    erc_20.approve(payment_request.address, tokens_to_approve, {"from": purchaser})

    # WHEN / THEN
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(
            pr_token_id,
            erc_20.address,
            {"from": purchaser}
        )
        tx: TransactionReceipt = TransactionReceipt(e.value.txid)
        assert tx.status == Status.Reverted

    receipt_addr: str = payment_request.receipt()
    receipt: Receipt = Contract.from_abi("Receipt", receipt_addr, Receipt.abi)
    assert receipt.balanceOf(purchaser.address) == 0

def test_GIVEN_post_payment_action_WHEN_payment_is_succesfull_THEN_payment_action_is_executed(*args, **kwargs):
    pass