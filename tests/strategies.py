from brownie.network.account import Account, Accounts, _PrivateKeyAccount
from hypothesis import strategies
from hypothesis.strategies import composite, SearchStrategy

from tests.configuration import (
    PaymentRequestConfiguration,
    PaymentPrecondition,
    TokenAmount,
    PostPaymentAction,
    PaymentRequestBuilder,
    PaymentRequestTestProxy,
)
from tests.integration.accounts import (
    DEPLOYER_ACCOUNT_INDEX_START,
    DEPLOYER_ACCOUNT_INDEX_END,
)

MAX_TOKEN_AMOUNT_VALUE: int = 100
MAX_NUM_STATIC_TOKENS: int = 11

def payment_request_test_proxy_strategy(
    payment_request_deployer_account_index: SearchStrategy[
        int
    ] = strategies.integers(min_value=DEPLOYER_ACCOUNT_INDEX_START, max_value=DEPLOYER_ACCOUNT_INDEX_END),
    payment_request_dependencies_deployer_account_index: SearchStrategy[
        int
    ] = strategies.integers(min_value=DEPLOYER_ACCOUNT_INDEX_START, max_value=DEPLOYER_ACCOUNT_INDEX_END),
    payment_request_creator_account_index: SearchStrategy[
        int
    ] = strategies.integers(min_value=DEPLOYER_ACCOUNT_INDEX_START, max_value=DEPLOYER_ACCOUNT_INDEX_END),
    precondition_id: SearchStrategy[int] = strategies.integers(
        min_value=PaymentPrecondition.min_value(),
        max_value=PaymentPrecondition.max_value(),
    ),
    token_amount_id: SearchStrategy[int] = strategies.integers(
        min_value=TokenAmount.min_value(), max_value=TokenAmount.max_value()
    ),
    post_payment_action_id: SearchStrategy[int] = strategies.integers(
        min_value=PostPaymentAction.min_value(), max_value=TokenAmount.max_value()
    ),
) -> SearchStrategy[PaymentRequestTestProxy]:
    static_token_amounts: list[int] = strategies.lists(
        elements=strategies.integers(min_value=0, max_value=MAX_TOKEN_AMOUNT_VALUE),
        max_size=MAX_NUM_STATIC_TOKENS,
    ).example()  # don't test with different token numbers for each PaymentRequest

    payment_request_configuration: SearchStrategy[
        PaymentRequestConfiguration
    ] = strategies.builds(
        PaymentRequestConfiguration,
        payment_precondition_id=precondition_id,
        token_amount_id=token_amount_id,
        post_payment_action_id=post_payment_action_id,
        static_token_amounts=strategies.just(static_token_amounts),
    )

    payment_request_builder: SearchStrategy[PaymentRequestBuilder] = strategies.builds(
        PaymentRequestBuilder,
        configuration=payment_request_configuration,
        payment_request_deployer_account_index=payment_request_deployer_account_index,
        payment_request_dependencies_deployer_account_index=payment_request_dependencies_deployer_account_index,
    )

    return strategies.builds(
        PaymentRequestTestProxy,
        payment_request_builder=payment_request_builder,
        creator_account_index=payment_request_creator_account_index,
    )
