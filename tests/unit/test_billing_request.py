"""
Tests related to payment request.

The tests in this test file are fully self-contained, do not assume any state properties of the underlying blockchain
environment and can run on either fresh or already existing blockchain state.
"""
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Tuple, OrderedDict, Optional, List, Dict, Type

from brownie.network.event import EventDict, _EventItem
from brownie.test import given, strategy
import pytest
from brownie import network, accounts
from brownie import PaymentRequest, MyERC20, MyERC721, Receipt, NFTOwnerPaymentPrecondition, FixedTokenAmountComputer, MyPostPaymentAction
from brownie.exceptions import VirtualMachineError
from brownie.network.account import Account
from brownie.network.contract import ProjectContract, Contract
from brownie.network.transaction import TransactionReceipt, Status
from hypothesis import example
from web3.constants import ADDRESS_ZERO

from scripts.utils.contants import LOCAL_BLOCKCHAIN_ENVIRONMENTS, Events
from scripts.utils.contract import ContractBuilder
from scripts.utils.types import NFTOwnerPaymentPreconditionMeta, NFTOwnerPaymentPreconditionWithMeta


# TODO: move to decorator/pytest groups
def skip_if_not_local_blockchain():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Not in a local blockchain environment.")

def assert_receipt_metadata_is_correct(*, receipt: Receipt, receipt_id: int, payment_request_addr: str, payment_request_id: int, token_addr: str, token_amount: int, payer_addr: str, payee_addr: str):
    assert receipt.receipt(receipt_id) == (payment_request_addr, payment_request_id, token_addr, token_amount, payer_addr, payee_addr)

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

    event_data: _EventItem = events[Events.DYNAMIC_TOKEN_AMOUNT_PPA_EXECUTED]
    assert event_data == {
        "receiptAddr": receipt_addr,
        "receiptId": receipt_id,
        "receiptTokenAddr": receipt_token_addr,
        "receiptTokenAmount": receipt_token_amount,
        "payer": payer,
        "payee": payee,
        "paymentPreconditionAddr": payment_precondition_addr,
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

    event_data: _EventItem = events[Events.STATIC_TOKEN_AMOUNT_PPA_EXECUTED]
    assert event_data == {
        "receiptAddr": receipt_addr,
        "receiptId": receipt_id,
        "receiptTokenAddr": receipt_token_addr,
        "receiptTokenAmount": receipt_token_amount,
        "payer": payer,
        "payee": payee,
        "paymentPreconditionAddr": payment_precondition_addr,
        "paymentRequestTokenAddr": payment_request_token_addr,
        "paymentRequestTokenAmount": payment_request_token_price,
    }


# Internal Structures Test
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

    erc20: ProjectContract = contract_builder.MyERC20

    # WHEN
    with pytest.raises(VirtualMachineError):
        pr.createWithStaticTokenAmount([], ADDRESS_ZERO, ADDRESS_ZERO, {"from": interactor})

@example(price_in_tokens=0)
@given(price_in_tokens=strategy("int256", min_value=0, max_value=99999))
def test_GIVEN_single_token_price_pair_from_non_deployer_account_WHEN_payment_request_created_THEN_internal_state_is_correct(price_in_tokens: int, *args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    payment_request: ProjectContract = contract_builder.PaymentRequest

    erc20: ProjectContract = contract_builder.MyERC20

    # WHEN
    STATIC_PRICES: List[Tuple[str, int]] = [(str(erc20.address), price_in_tokens)]
    token_addr: str = STATIC_PRICES[0][0]
    token_price: int = STATIC_PRICES[0][1]
    token_index: int = 0
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(STATIC_PRICES, ADDRESS_ZERO, ADDRESS_ZERO, {"from": interactor})
    assert tx.status == Status.Confirmed
    payment_request_id: int = tx.return_value

    # THEN
    assert payment_request.isTokenAmountStatic(payment_request_id)
    assert not payment_request.isTokenAmountDynamic(payment_request_id)

    assert payment_request.getNumberOfStaticTokens(payment_request_id) == len(STATIC_PRICES)
    assert payment_request.getStaticTokens(payment_request_id) == (token_addr,)
    assert payment_request.getStaticTokenAmountInfos(payment_request_id) == STATIC_PRICES

    assert payment_request.getStaticTokenAmountInfoByIndex(payment_request_id, token_index) == STATIC_PRICES[0]
    assert payment_request.getStaticTokenByIndex(payment_request_id, token_index) == token_addr
    assert payment_request.getStaticTokenAmountByIndex(payment_request_id, token_index) == token_price
    assert payment_request.getStaticTokenAmount(payment_request_id, token_addr) == token_price
    tx: TransactionReceipt = payment_request.getTokenAmount(payment_request_id, token_addr)
    assert tx.status == Status.Confirmed
    assert tx.return_value == token_price

    with pytest.raises(VirtualMachineError):
        payment_request.getDynamicTokenAmount(payment_request_id, token_addr)

    non_existing_index = token_index + 1
    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenAmountInfoByIndex(payment_request_id, non_existing_index)

    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenByIndex(payment_request_id, non_existing_index)

    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenAmountByIndex(payment_request_id, non_existing_index)

    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenAmountByIndex(payment_request_id, non_existing_index)

    assert payment_request.balanceOf(interactor.address) == 1
    assert payment_request.tokenOfOwnerByIndex(interactor.address, 0) == payment_request_id
    with pytest.raises(VirtualMachineError):
        # only one token created
        payment_request.tokenOfOwnerByIndex(interactor.address, 1)

    # interactor.address is not a token payment address that was added
    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenAmount(payment_request_id, interactor.address)

    with pytest.raises(VirtualMachineError):
        # only one price added
        payment_request.getStaticTokenAmountByIndex(0, 1)

    # test getters
    assert payment_request.getStaticTokenAmountInfos(payment_request_id) == STATIC_PRICES
    assert payment_request.getStaticTokenAmount(payment_request_id, erc20.address) == price_in_tokens

    assert payment_request.isTokenAmountStatic(payment_request_id) == True

    with pytest.raises(VirtualMachineError):
        payment_request.getDynamicTokenAmount(payment_request_id, erc20.address)


@given(num_tokens=strategy("int256", min_value=1, max_value=23), use_separate_account_for_pr_creation=strategy("bool"))
def test_GIVEN_multiple_token_price_pair_from_non_deployer_account_WHEN_payment_request_created_THEN_internal_state_is_correct(num_tokens: int, use_separate_account_for_pr_creation: bool, *args, **kwargs):
    skip_if_not_local_blockchain()

    @dataclass
    class ERC20Token:
        erc_20: ProjectContract
        price: int

    # GIVEN
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]
    pr_token_creator: Account = interactor if use_separate_account_for_pr_creation else deployer

    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    payment_request: ProjectContract = contract_builder.PaymentRequest

    erc_20_tokens: Dict[str, ERC20Token] = dict()
    static_prices: List[List[str, int]] = list()

    for i in range(num_tokens):
        dict_key: str = f"erc_20_{i}"
        erc_20: ProjectContract = contract_builder.MyERC20
        erc_20_price: int = random.randint(0, 101)

        erc_20_tokens[dict_key] = ERC20Token(erc_20=erc_20, price=erc_20_price)
        static_prices.append(
            [str(erc_20.address), erc_20_price]
        )

    # WHEN
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(static_prices,
                                        ADDRESS_ZERO,
                                        ADDRESS_ZERO,
                                       {"from": pr_token_creator})

    assert tx.status == Status.Confirmed
    payment_request_id: int = tx.return_value

    # THEN
    assert payment_request.balanceOf(pr_token_creator) == 1
    assert payment_request.tokenOfOwnerByIndex(pr_token_creator, 0) == 0

    with pytest.raises(VirtualMachineError):
        # only one token created
        payment_request.tokenOfOwnerByIndex(pr_token_creator, 1)

    # interactor.address is not a token payment address that was added
    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenAmount(payment_request_id, interactor.address)

    # token prices for payment request ID
    for index, key in enumerate(erc_20_tokens):
        erc_20_token_dt: ERC20Token = erc_20_tokens[key]
        assert payment_request.getStaticTokenAmountInfoByIndex(payment_request_id, index) == (erc_20_token_dt.erc_20.address, erc_20_token_dt.price)

    with pytest.raises(VirtualMachineError):
        # only len(erc_20_tokens) prices were added
        payment_request.getStaticTokenAmountInfoByIndex(payment_request_id, len(erc_20_tokens) + 1)

    # Test Getters
    assert payment_request.getStaticTokenAmountInfos(payment_request_id) == static_prices
    assert payment_request.isTokenAmountStatic(payment_request_id) == True

    for _, value in erc_20_tokens.items():
        assert payment_request.getStaticTokenAmount(payment_request_id, value.erc_20.address) == value.price


        with pytest.raises(VirtualMachineError):
            payment_request.getDynamicTokenAmount(payment_request_id, value.erc_20.address)


@given(num_deployers=strategy("uint256", min_value=2, max_value=10))
def test_GIVEN_multiple_token_price_pair_from_deployer_account_WHEN_payment_request_created_by_multiple_interactors_THEN_internal_state_is_correct(num_deployers: int, *args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN / WHEN
    @dataclass
    class ERC20Token:
        erc_20: ProjectContract
        price: int

    TokenAmountInfo = Tuple[str, int]
    TokenAmounts: Type = List[TokenAmountInfo]

    deployer: Account = accounts[0]
    deployer_accounts: List[Account] = [accounts[i] for i in range(num_deployers)]
    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    account_to_list_of_token_prices: Dict[int, List[TokenAmounts]] = defaultdict(list)
    payment_request: ProjectContract = contract_builder.PaymentRequest

    total_num_tokens: int = 0
    # For each one of the accounts, create between 1 and 101 PaymentRequests, with each PaymentRequest containing
    # between 1 and 1001 (token, token_price) pairs
    for i in range(num_deployers):
        num_payment_requests_for_account: int = random.randint(1, 5)

        for _ in range(num_payment_requests_for_account):
            tokens_for_account: List[ERC20Token] = list()
            # NOTE: large numbers here cause Read timeouts on ganache-cli
            num_tokens_for_payment_request: int = random.randint(1, 5)
            for _ in range(num_tokens_for_payment_request):
                erc_20: ProjectContract = contract_builder.MyERC20
                erc_20_price: int = random.randint(0, 2**32)
                tokens_for_account.append(ERC20Token(erc_20=erc_20, price=erc_20_price))

            token_prices: List[Tuple[str, int]] = [(erc20token.erc_20.address, erc20token.price) for erc20token in tokens_for_account]

            tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
                token_prices,
                ADDRESS_ZERO,
                ADDRESS_ZERO,
                {"from": deployer_accounts[i]}
            )
            assert tx.status == Status.Confirmed
            total_num_tokens += 1

            account_to_list_of_token_prices[i].append(token_prices)

    # THEN

    assert payment_request.totalSupply() == total_num_tokens

    # ensure number of created tokens correct for each account
    for account_index in range(len(deployer_accounts)):
        account: Account = deployer_accounts[account_index]
        num_payment_requests_created: int = payment_request.balanceOf(deployer_accounts[account_index].address)
        assert num_payment_requests_created == len(account_to_list_of_token_prices[account_index])

        for token_index in range(num_payment_requests_created):
            token_id: int = payment_request.tokenOfOwnerByIndex(account.address, token_index)
            expected_token_addrs_and_prices_for_index: TokenAmounts = account_to_list_of_token_prices[account_index][token_index]

            assert payment_request.isTokenAmountStatic(token_id)
            assert not payment_request.isTokenAmountDynamic(token_id)

            assert payment_request.getNumberOfStaticTokens(token_id) == len(expected_token_addrs_and_prices_for_index)
            assert payment_request.getStaticTokens(token_id) == [token[0] for token in expected_token_addrs_and_prices_for_index]
            assert payment_request.getStaticTokenAmountInfos(token_id) == expected_token_addrs_and_prices_for_index

            # non-registered token price get
            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenAmount(token_id, account.address)

            # assignments made to avoid linter warnings
            index: int = 0
            item: TokenAmountInfo
            for index, item in enumerate(expected_token_addrs_and_prices_for_index):
                token_addr: str = item[0]
                token_price: int = item[1]
                assert payment_request.getStaticTokenAmountInfoByIndex(token_id, index) == item
                assert payment_request.getStaticTokenByIndex(token_id, index) == token_addr
                assert payment_request.getStaticTokenAmountByIndex(token_id, index) == token_price
                assert payment_request.getStaticTokenAmount(token_id, token_addr) == token_price
                tx: TransactionReceipt = payment_request.getTokenAmount(token_id, token_addr)
                assert tx.status == Status.Confirmed
                assert tx.return_value == token_price

                with pytest.raises(VirtualMachineError):
                    payment_request.getDynamicTokenAmount(token_id, token_addr)

            non_existing_index = index + 1
            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenAmountInfoByIndex(token_id, non_existing_index)

            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenByIndex(token_id, non_existing_index)

            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenAmountByIndex(token_id, non_existing_index)

            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenAmountByIndex(token_id, non_existing_index)


# TODO: test with duplicate specifications of same token
# TODO: test internal structure for dynamic prices

def test_GIVEN_static_token_prices_with_duplicated_entry_WHEN_attempting_to_create_payment_request_THEN_error_is_raised(*args, **kwargs):
    pass

# Payment Request Enable/Disable Tests
def test_GIVEN_deployed_contract_WHEN_owner_attempting_to_disable_and_enable_THEN_it_succeeds_and_correct_events_are_emitted(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT: int = 6
    account: Account = accounts[0]
    contract_builder: ContractBuilder = ContractBuilder(account=account)

    pr: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = pr.createWithStaticTokenAmount([[str(pr.address), TOKEN_AMOUNT]],
                                       ADDRESS_ZERO,
                                       ADDRESS_ZERO,
                                       {"from": account})

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

def test_GIVEN_deployed_contract_WHEN_non_owner_attempting_to_disable_and_enable_THEN_it_fails(*args, **kwargs):
    skip_if_not_local_blockchain()

    # GIVEN
    TOKEN_AMOUNT: int = 6
    owner: Account = accounts[0]
    not_owner: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=owner)

    pr: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = pr.createWithStaticTokenAmount([[str(pr.address), TOKEN_AMOUNT]],
                                                      ADDRESS_ZERO,
                                                      ADDRESS_ZERO,
                                                      {"from": owner})

    assert tx.status == Status.Confirmed
    created_token_id: int = tx.return_value

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
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer}
    )
    created_token_id: int = tx.return_value

    non_exclusive_token.approve(payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": no_nft_or_pr})
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(created_token_id, non_exclusive_token.address, {"from": no_nft_or_pr})
        tx = TransactionReceipt(e.value.txid)
        assert tx.status == Status.Reverted
        assert "PaymentPreconditionPassed" not in tx.events

    exclusive_token.approve(payment_request.address, EXCLUSIVE_TOKEN_AMOUNT, {"from": no_nft_or_pr})
    with pytest.raises(VirtualMachineError):
        payment_request.pay(created_token_id, exclusive_token.address, {"from": no_nft_or_pr})
        tx = TransactionReceipt(e.value.txid)
        assert tx.status == Status.Reverted
        assert "PaymentPreconditionPassed" not in tx.events

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
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer}
    )
    created_token_id: int = tx.return_value

    non_exclusive_token.approve(payment_request.address, NON_EXCLUSIVE_TOKEN_AMOUNT, {"from": nft_no_pr})
    with pytest.raises(VirtualMachineError) as e:
        payment_request.pay(created_token_id, non_exclusive_token.address, {"from": nft_no_pr})
        tx = TransactionReceipt(e.value.txid)
        assert tx.status == Status.Reverted
        assert "PaymentPreconditionPassed" not in tx.events

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
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer}
    )

    created_token_id: int = tx.return_value

    # deploy payment for the Non-NFT, only Payment Request owner contract
    payment_request.createWithStaticTokenAmount(
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
        assert "PaymentPreconditionPassed" not in tx.events

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
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [non_exclusive_token.address, NON_EXCLUSIVE_TOKEN_AMOUNT],
            [exclusive_token.address, EXCLUSIVE_TOKEN_AMOUNT],
        ],
        precondition.address,
        ADDRESS_ZERO,
        {"from": deployer}
    )

    created_token_id: int = tx.return_value

    # deploy payment for the Non-NFT, only Payment Request owner contract
    payment_request.createWithStaticTokenAmount(
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

# Dynamic Amount Computer Test
@pytest.mark.parametrize("price_in_tokens", [0, random.randint(1, 999)])
def test_GIVEN_fixed_price_computer_function_WHEN_attempt_to_purchase_is_made_THEN_purchase_with_correct_amount_is_done(price_in_tokens: int, *args, **kwargs):
    # GIVEN
    deployer: Account = accounts[0]
    purchaser: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)

    price_computer: FixedTokenAmountComputer = contract_builder.get_fixed_token_amount_computer(
        price=price_in_tokens, account=deployer, force_deploy=True
    )
    assert price_in_tokens == price_computer.price()

    payment_request: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithDynamicTokenAmount(
        price_computer.address,
        ADDRESS_ZERO,
        ADDRESS_ZERO,
        {"from": deployer}
    )

    assert tx.status == Status.Confirmed
    pr_token_id: int = tx.return_value


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
        contract_builder.get_fixed_token_amount_computer(
            price=price_in_tokens, account=deployer, force_deploy=True
        )

@given(price_in_tokens=strategy("uint256", min_value=1, max_value=9999))
def test_GIVEN_price_computer_WHEN_paying_and_approving_less_tokens_than_necessary_THEN_purchase_fails(price_in_tokens: int, *args, **kwargs):
    # GIVEN
    deployer: Account = accounts[0]
    purchaser: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)

    price_computer: FixedTokenAmountComputer = contract_builder.get_fixed_token_amount_computer(
        price=price_in_tokens, account=deployer, force_deploy=True
    )
    assert price_in_tokens == price_computer.price()
    tokens_to_approve: int = price_in_tokens - 1

    payment_request: PaymentRequest = contract_builder.PaymentRequest
    tx: TransactionReceipt = payment_request.createWithDynamicTokenAmount(
        price_computer.address,
        ADDRESS_ZERO,
        ADDRESS_ZERO,
        {"from": deployer}
    )

    assert tx.status == Status.Confirmed
    pr_token_id: int = tx.return_value

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

# Payment Post Action Test
@example(price_in_tokens=0, use_separate_account_for_pay=True)
@example(price_in_tokens=0, use_separate_account_for_pay=False)
@given(price_in_tokens=strategy("uint256", min_value=0, max_value=9999), use_separate_account_for_pay=strategy("bool"))
def test_GIVEN_static_prices_and_post_payment_action_WHEN_payment_is_succesfull_THEN_payment_action_is_executed(price_in_tokens: int, use_separate_account_for_pay: bool, *args, **kwargs):
    # GIVEN

    deployer: Account = accounts[0]
    payee: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    post_payment_action: MyPostPaymentAction = contract_builder.MyPostPaymentAction
    payment_request: PaymentRequest = contract_builder.PaymentRequest
    erc_20_first: MyERC20 = contract_builder.MyERC20
    erc_20_second: MyERC20 = contract_builder.MyERC20
    payee_from_account: Account = payee if use_separate_account_for_pay else deployer

    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        [
            [str(erc_20_first.address), price_in_tokens],
            [str(erc_20_second.address), price_in_tokens]
        ],
        ADDRESS_ZERO,
        post_payment_action.address,
    )
    assert tx.status == Status.Confirmed

    payment_request_id: int = tx.return_value

    # WHEN
    if use_separate_account_for_pay:
        erc_20_second.transfer(payee.address, price_in_tokens, {"from": deployer})

    erc_20_second.approve(payment_request.address, price_in_tokens, {"from": payee_from_account})

    tx = payment_request.pay(
        payment_request_id,
        erc_20_second.address,
        {"from": payee_from_account}
    )

    # THEN
    assert tx.status == Status.Confirmed
    assert Events.STATIC_TOKEN_AMOUNT_PPA_EXECUTED in tx.events
    assert Events.DYNAMIC_TOKEN_AMOUNT_PPA_EXECUTED not in tx.events

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
        payment_precondition_addr=ADDRESS_ZERO,
        payment_request_token_addr=erc_20_first,
        payment_request_token_price=price_in_tokens,
    )


@example(price_in_tokens=0, use_separate_account_for_pay=True)
@example(price_in_tokens=0, use_separate_account_for_pay=False)
@given(price_in_tokens=strategy("uint256", min_value=0, max_value=9999), use_separate_account_for_pay=strategy("bool"))
def test_GIVEN_dynamic_prices_and_post_payment_action_WHEN_payment_is_succesfull_THEN_payment_action_is_executed(price_in_tokens: int, use_separate_account_for_pay: bool, *args, **kwargs):
    # GIVEN

    deployer: Account = accounts[0]
    payee: Account = accounts[1]
    contract_builder: ContractBuilder = ContractBuilder(account=deployer, force_deploy=True)
    post_payment_action: MyPostPaymentAction = contract_builder.MyPostPaymentAction
    payment_request: PaymentRequest = contract_builder.PaymentRequest
    erc_20: MyERC20 = contract_builder.MyERC20
    payee_from_account: Account = payee if use_separate_account_for_pay else deployer

    price_computer: FixedTokenAmountComputer = contract_builder.get_fixed_token_amount_computer(
        price=price_in_tokens, account=deployer, force_deploy=True
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

    erc_20.approve(payment_request.address, price_in_tokens, {"from": payee_from_account})

    tx = payment_request.pay(
        payment_request_id,
        erc_20.address,
        {"from": payee_from_account}
    )

    # THEN
    assert tx.status == Status.Confirmed
    assert Events.STATIC_TOKEN_AMOUNT_PPA_EXECUTED not in tx.events
    assert Events.DYNAMIC_TOKEN_AMOUNT_PPA_EXECUTED in tx.events

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
        payment_precondition_addr=ADDRESS_ZERO,
    )

