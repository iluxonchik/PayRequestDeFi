from hypothesis import strategies
from hypothesis.strategies import composite

from tests.configuration import (
    PaymentRequestConfiguration,
    PaymentPrecondition,
    TokenAmount,
    PostPaymentAction,
)

MAX_TOKEN_AMOUNT_VALUE: int = 100
MAX_NUM_STATIC_TOKENS: int = 11

def payment_request_configuration_strategy(
    precondition_id=strategies.integers(
        min_value=PaymentPrecondition.min_value(),
        max_value=PaymentPrecondition.max_value(),
    ),
    token_amount_id=strategies.integers(
        min_value=TokenAmount.min_value(), max_value=TokenAmount.max_value()
    ),
    post_payment_action_id=strategies.integers(
        min_value=PostPaymentAction.min_value(), max_value=TokenAmount.max_value()
    ),
):
    static_token_amounts = (
        []
        if TokenAmount.is_value_static_token_amount(token_amount_id)
        else strategies.lists(
            elements=strategies.integers(min_value=0, max_value=MAX_TOKEN_AMOUNT_VALUE),
            max_size=MAX_NUM_STATIC_TOKENS,
        ).example() # don't test with different token numbers for each PaymentRequest
    )

    return strategies.builds(PaymentRequestConfiguration,
        payment_precondition_id=precondition_id,
        token_amount_id=token_amount_id,
        post_payment_action_id=post_payment_action_id,
        static_token_amounts=strategies.just(static_token_amounts),
    )
