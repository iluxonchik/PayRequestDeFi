import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Tuple, List, Dict, Type

import pytest
from brownie import PaymentRequest, MyERC20, Receipt
from brownie import accounts
from brownie.exceptions import VirtualMachineError
from brownie.network.account import Account
from brownie.network.contract import ProjectContract
from brownie.network.transaction import TransactionReceipt, Status
from brownie.test import given, strategy
from hypothesis import example
from web3.constants import ADDRESS_ZERO

from scripts.utils.contract import ContractBuilder
from scripts.utils.environment import is_local_blockchain_environment

if not is_local_blockchain_environment():
    pytest.skip(f"Skipping tests from {__file__} as a non-local blockchain environment is used.", allow_module_level=True)

@pytest.fixture(autouse=True)
def shared_setup(fn_isolation):
    pass

def test_GIVEN_payment_request_WHEN_deployed_THEN_deployment_succeeds(*args, **kwargs):
    account: Account = accounts[0]
    contract_builder: ContractBuilder = ContractBuilder(
        account=account, force_deploy=True
    )
    rc: Receipt = ContractBuilder.get_receipt_contract(
        account=account, force_deploy=True
    )
    pr: ProjectContract = contract_builder.get_payment_request_contract(
        receipt=rc, account=account, force_deploy=True
    )

    assert rc.tx is not None, "Receipt failed to deploy"
    assert rc.tx.status == Status.Confirmed

    assert pr.tx is not None, "PaymentRequest failed to deploy"
    assert pr.tx.status == Status.Confirmed


def test_GIVEN_payment_request_creation_WHEN_no_prices_are_provided_THEN_payment_request_creation_fails(
    *args, **kwargs
):
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    pr: ProjectContract = contract_builder.PaymentRequest

    erc20: ProjectContract = contract_builder.MyERC20

    # WHEN
    with pytest.raises(VirtualMachineError):
        pr.createWithStaticTokenAmount(
            [], ADDRESS_ZERO, ADDRESS_ZERO, {"from": interactor}
        )


@example(price_in_tokens=0)
@given(price_in_tokens=strategy("int256", min_value=0, max_value=99999))
def test_GIVEN_single_token_price_pair_from_non_deployer_account_WHEN_payment_request_created_THEN_internal_state_is_correct(
    price_in_tokens: int, *args, **kwargs
):

    # GIVEN
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]

    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    payment_request: ProjectContract = contract_builder.PaymentRequest

    erc20: ProjectContract = contract_builder.MyERC20

    # WHEN
    STATIC_PRICES: List[Tuple[str, int]] = [(str(erc20.address), price_in_tokens)]
    token_addr: str = STATIC_PRICES[0][0]
    token_price: int = STATIC_PRICES[0][1]
    token_index: int = 0
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        STATIC_PRICES, ADDRESS_ZERO, ADDRESS_ZERO, {"from": interactor}
    )
    assert tx.status == Status.Confirmed
    payment_request_id: int = tx.return_value

    # THEN
    assert payment_request.isTokenAmountStatic(payment_request_id)
    assert not payment_request.isTokenAmountDynamic(payment_request_id)

    assert payment_request.getNumberOfStaticTokens(payment_request_id) == len(
        STATIC_PRICES
    )
    assert payment_request.getStaticTokens(payment_request_id) == (token_addr,)
    assert (
        payment_request.getStaticTokenAmountInfos(payment_request_id) == STATIC_PRICES
    )

    assert (
        payment_request.getStaticTokenAmountInfoByIndex(payment_request_id, token_index)
        == STATIC_PRICES[0]
    )
    assert (
        payment_request.getStaticTokenByIndex(payment_request_id, token_index)
        == token_addr
    )
    assert (
        payment_request.getStaticTokenAmountByIndex(payment_request_id, token_index)
        == token_price
    )
    assert (
        payment_request.getStaticAmountForToken(payment_request_id, token_addr)
        == token_price
    )

    assert not payment_request.isPaymentPreconditionSet(payment_request_id)
    assert not payment_request.isPaymentPostActionSet(payment_request_id)

    assert payment_request.getPostPaymentActionAddr(payment_request_id) == ADDRESS_ZERO
    assert (
        payment_request.getPaymentPreconditionAddr(payment_request_id) == ADDRESS_ZERO
    )
    assert payment_request.getDynamicTokenAmountAddr(payment_request_id) == ADDRESS_ZERO

    tx: TransactionReceipt = payment_request.getAmountForToken(
        payment_request_id, token_addr
    )
    assert tx.status == Status.Confirmed
    assert tx.return_value == token_price

    with pytest.raises(VirtualMachineError):
        payment_request.getDynamicAmountForToken(payment_request_id, token_addr)

    non_existing_index = token_index + 1
    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenAmountInfoByIndex(
            payment_request_id, non_existing_index
        )

    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenByIndex(payment_request_id, non_existing_index)

    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenAmountByIndex(
            payment_request_id, non_existing_index
        )

    with pytest.raises(VirtualMachineError):
        payment_request.getStaticTokenAmountByIndex(
            payment_request_id, non_existing_index
        )

    assert payment_request.balanceOf(interactor.address) == 1
    assert (
        payment_request.tokenOfOwnerByIndex(interactor.address, 0) == payment_request_id
    )
    with pytest.raises(VirtualMachineError):
        # only one token created
        payment_request.tokenOfOwnerByIndex(interactor.address, 1)

    # interactor.address is not a token payment address that was added
    with pytest.raises(VirtualMachineError):
        payment_request.getStaticAmountForToken(payment_request_id, interactor.address)

    with pytest.raises(VirtualMachineError):
        # only one price added
        payment_request.getStaticTokenAmountByIndex(0, 1)

    # test getters
    assert (
        payment_request.getStaticTokenAmountInfos(payment_request_id) == STATIC_PRICES
    )
    assert (
        payment_request.getStaticAmountForToken(payment_request_id, erc20.address)
        == price_in_tokens
    )

    assert payment_request.isTokenAmountStatic(payment_request_id) == True

    with pytest.raises(VirtualMachineError):
        payment_request.getDynamicAmountForToken(payment_request_id, erc20.address)


@given(
    num_tokens=strategy("int256", min_value=1, max_value=23),
    use_separate_account_for_pr_creation=strategy("bool"),
)
def test_GIVEN_multiple_token_price_pair_from_non_deployer_account_WHEN_payment_request_created_THEN_internal_state_is_correct(
    num_tokens: int, use_separate_account_for_pr_creation: bool, *args, **kwargs
):
    @dataclass
    class ERC20Token:
        erc_20: ProjectContract
        price: int

    # GIVEN
    deployer: Account = accounts[0]
    interactor: Account = accounts[1]
    pr_token_creator: Account = (
        interactor if use_separate_account_for_pr_creation else deployer
    )

    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
    payment_request: ProjectContract = contract_builder.PaymentRequest

    erc_20_tokens: Dict[str, ERC20Token] = dict()
    static_prices: List[List[str, int]] = list()

    for i in range(num_tokens):
        dict_key: str = f"erc_20_{i}"
        erc_20: ProjectContract = contract_builder.MyERC20
        erc_20_price: int = random.randint(0, 101)

        erc_20_tokens[dict_key] = ERC20Token(erc_20=erc_20, price=erc_20_price)
        static_prices.append([str(erc_20.address), erc_20_price])

    # WHEN
    tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
        static_prices, ADDRESS_ZERO, ADDRESS_ZERO, {"from": pr_token_creator}
    )

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
        payment_request.getStaticAmountForToken(payment_request_id, interactor.address)

    # token prices for payment request ID
    for index, key in enumerate(erc_20_tokens):
        erc_20_token_dt: ERC20Token = erc_20_tokens[key]
        assert payment_request.getStaticTokenAmountInfoByIndex(
            payment_request_id, index
        ) == (erc_20_token_dt.erc_20.address, erc_20_token_dt.price)

    with pytest.raises(VirtualMachineError):
        # only len(erc_20_tokens) prices were added
        payment_request.getStaticTokenAmountInfoByIndex(
            payment_request_id, len(erc_20_tokens) + 1
        )

    # Test Getters
    assert not payment_request.isPaymentPreconditionSet(payment_request_id)
    assert not payment_request.isPaymentPostActionSet(payment_request_id)

    assert payment_request.getPostPaymentActionAddr(payment_request_id) == ADDRESS_ZERO
    assert (
        payment_request.getPaymentPreconditionAddr(payment_request_id) == ADDRESS_ZERO
    )
    assert payment_request.getDynamicTokenAmountAddr(payment_request_id) == ADDRESS_ZERO

    assert (
        payment_request.getStaticTokenAmountInfos(payment_request_id) == static_prices
    )
    assert payment_request.isTokenAmountStatic(payment_request_id) == True

    for _, value in erc_20_tokens.items():
        assert (
            payment_request.getStaticAmountForToken(
                payment_request_id, value.erc_20.address
            )
            == value.price
        )

        with pytest.raises(VirtualMachineError):
            payment_request.getDynamicAmountForToken(
                payment_request_id, value.erc_20.address
            )


@given(num_deployers=strategy("uint256", min_value=2, max_value=10))
def test_GIVEN_multiple_token_price_pair_from_deployer_account_WHEN_payment_request_created_by_multiple_interactors_THEN_internal_state_is_correct(
    num_deployers: int, *args, **kwargs
):
    # GIVEN / WHEN
    @dataclass
    class ERC20Token:
        erc_20: ProjectContract
        price: int

    TokenAmountInfo = Tuple[str, int]
    TokenAmounts: Type = List[TokenAmountInfo]

    deployer: Account = accounts[0]
    deployer_accounts: List[Account] = [accounts[i] for i in range(num_deployers)]
    contract_builder: ContractBuilder = ContractBuilder(
        account=deployer, force_deploy=True
    )
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

            token_prices: List[Tuple[str, int]] = [
                (erc20token.erc_20.address, erc20token.price)
                for erc20token in tokens_for_account
            ]

            tx: TransactionReceipt = payment_request.createWithStaticTokenAmount(
                token_prices, ADDRESS_ZERO, ADDRESS_ZERO, {"from": deployer_accounts[i]}
            )
            assert tx.status == Status.Confirmed
            total_num_tokens += 1

            account_to_list_of_token_prices[i].append(token_prices)

    # THEN
    assert payment_request.totalSupply() == total_num_tokens

    # ensure number of created tokens correct for each account
    for account_index in range(len(deployer_accounts)):
        account: Account = deployer_accounts[account_index]
        num_payment_requests_created: int = payment_request.balanceOf(
            deployer_accounts[account_index].address
        )
        assert num_payment_requests_created == len(
            account_to_list_of_token_prices[account_index]
        )

        for token_index in range(num_payment_requests_created):
            token_id: int = payment_request.tokenOfOwnerByIndex(
                account.address, token_index
            )
            expected_token_addrs_and_prices_for_index: TokenAmounts = (
                account_to_list_of_token_prices[account_index][token_index]
            )

            assert payment_request.isTokenAmountStatic(token_id)
            assert not payment_request.isTokenAmountDynamic(token_id)

            assert payment_request.getNumberOfStaticTokens(token_id) == len(
                expected_token_addrs_and_prices_for_index
            )
            assert payment_request.getStaticTokens(token_id) == [
                token[0] for token in expected_token_addrs_and_prices_for_index
            ]
            assert (
                payment_request.getStaticTokenAmountInfos(token_id)
                == expected_token_addrs_and_prices_for_index
            )

            # non-registered token price get
            with pytest.raises(VirtualMachineError):
                payment_request.getStaticAmountForToken(token_id, account.address)

            # assignments made to avoid linter warnings
            index: int = 0
            item: TokenAmountInfo
            for index, item in enumerate(expected_token_addrs_and_prices_for_index):
                token_addr: str = item[0]
                token_price: int = item[1]
                assert (
                    payment_request.getStaticTokenAmountInfoByIndex(token_id, index)
                    == item
                )
                assert (
                    payment_request.getStaticTokenByIndex(token_id, index) == token_addr
                )
                assert (
                    payment_request.getStaticTokenAmountByIndex(token_id, index)
                    == token_price
                )
                assert (
                    payment_request.getStaticAmountForToken(token_id, token_addr)
                    == token_price
                )
                tx: TransactionReceipt = payment_request.getAmountForToken(
                    token_id, token_addr
                )
                assert tx.status == Status.Confirmed
                assert tx.return_value == token_price

                with pytest.raises(VirtualMachineError):
                    payment_request.getDynamicAmountForToken(token_id, token_addr)

            non_existing_index = index + 1
            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenAmountInfoByIndex(
                    token_id, non_existing_index
                )

            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenByIndex(token_id, non_existing_index)

            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenAmountByIndex(
                    token_id, non_existing_index
                )

            with pytest.raises(VirtualMachineError):
                payment_request.getStaticTokenAmountByIndex(
                    token_id, non_existing_index
                )


@given(num_duplicated_token_pairs=strategy("uint256", min_value=1, max_value=5))
@given(num_non_duplicated_tokens=strategy("uint256", min_value=0, max_value=5))
@given(include_payment_precondition=strategy("bool"))
@given(include_payment_post_action=strategy("bool"))
def test_GIVEN_static_token_prices_with_duplicated_entry_WHEN_attempting_to_create_payment_request_THEN_error_is_raised(
    num_duplicated_token_pairs: int,
    num_non_duplicated_tokens: int,
    include_payment_precondition: bool,
    include_payment_post_action: bool,
    *args,
    **kwargs,
):
    # GIVEN
    account: Account = accounts[0]
    contract_builder: ContractBuilder = ContractBuilder(account=account)
    token_contract_builder: ContractBuilder = ContractBuilder(
        account=account, force_deploy=True
    )

    tokens: list[list[str, int]] = []
    erc_20: MyERC20

    for _ in range(num_duplicated_token_pairs):
        erc_20 = token_contract_builder.MyERC20
        num_token_occurrences: int = random.randint(2, 7)

        tokens.extend(
            [erc_20.address, random.randint(0, 101)]
            for _ in range(num_token_occurrences)
        )
    for _ in range(num_non_duplicated_tokens):
        erc_20 = token_contract_builder.MyERC20
        tokens.append([erc_20.address, random.randint(0, 101)])

    random.shuffle(tokens)

    pr: PaymentRequest = contract_builder.PaymentRequest

    payment_precondition_addr: str = (
        contract_builder.NFTOwnerPaymentPrecondition.address
        if include_payment_precondition
        else ADDRESS_ZERO
    )
    payment_post_action_addr: str = (
        contract_builder.MyPostPaymentAction.address
        if include_payment_post_action
        else ADDRESS_ZERO
    )
    with pytest.raises(VirtualMachineError) as e:
        pr.createWithStaticTokenAmount(
            tokens,
            payment_precondition_addr,
            payment_post_action_addr,
            {"from": account},
        )

    tx = TransactionReceipt(e.value.txid)
    assert tx.status == Status.Reverted
