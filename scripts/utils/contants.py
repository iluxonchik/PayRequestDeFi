from typing import List

LOCAL_BLOCKCHAIN_ENVIRONMENTS: List[str] = [
    "ganache-gui",
    "ganache-local",
    "development",
]

class EventName:
    STATIC_TOKEN_AMOUNT_PPA_EXECUTED: str = "StaticTokenAmountPPAExecuted"
    DYNAMIC_TOKEN_AMOUNT_PPA_EXECUTED: str = "DynamicTokenAmountPPAExecuted"

    PAYMENT_PRECONDITION_PASSED: str = "PaymentPreconditionPassed"
    TOKEN_AMOUNT_OBTAINED: str = "TokenAmountObtained"
    POST_PAYMENT_ACTION_EXECUTED: str = "PostPaymentActionExecuted"
    PAYMENT_REQUEST_PAID: str = "PaymentRequestPaid"

    APP_SPECIFIC: List[str] = [
        PAYMENT_PRECONDITION_PASSED,
        TOKEN_AMOUNT_OBTAINED,
        POST_PAYMENT_ACTION_EXECUTED,
        PAYMENT_REQUEST_PAID,
    ]
class ExpectedEventsFor:
    class Success:
        class PP:
            NoPPA: List[str] = [
                EventName.PAYMENT_PRECONDITION_PASSED,
                EventName.TOKEN_AMOUNT_OBTAINED,
                EventName.PAYMENT_REQUEST_PAID,
            ]

            PPA: List[str] = [
                EventName.PAYMENT_PRECONDITION_PASSED,
                EventName.TOKEN_AMOUNT_OBTAINED,
                EventName.POST_PAYMENT_ACTION_EXECUTED,
                EventName.PAYMENT_REQUEST_PAID,
            ]

        class NoPP:
            NoPPA: List[str] = [
                EventName.TOKEN_AMOUNT_OBTAINED,
                EventName.PAYMENT_REQUEST_PAID,
            ]

            PPA: List[str] = [
                EventName.TOKEN_AMOUNT_OBTAINED,
                EventName.POST_PAYMENT_ACTION_EXECUTED,
                EventName.PAYMENT_REQUEST_PAID,
            ]

    class Failure:
        class PP:
            class NoPPA:
                class FailAt:
                    PP: List[str] = []
                    TA: List[str] = PP + [
                        EventName.PAYMENT_PRECONDITION_PASSED,
                    ]
                    PR: List[str] = TA + [
                        EventName.TOKEN_AMOUNT_OBTAINED,
                    ]
            class PPA:
                class FailAt:
                    PP: List[str] = []
                    TA: List[str] = PP + [
                        EventName.PAYMENT_PRECONDITION_PASSED,
                    ]
                    PPA: List[str] = TA + [
                        EventName.TOKEN_AMOUNT_OBTAINED,
                    ]
                    PR: List[str] = PPA + [
                        EventName.PAYMENT_REQUEST_PAID,
                    ]
        class NoPP:
            class NoPPA:
                class FailAt:
                    TA: List[str] = []
                    PR: List [str] = TA + [
                        EventName.TOKEN_AMOUNT_OBTAINED,
                    ]

            class PPA:
                class FailAt:
                    TA: List[str] = []
                    PPA: List[str] = TA + [
                        EventName.TOKEN_AMOUNT_OBTAINED,
                    ]
                    PR: List[str] = PPA + [
                        EventName.POST_PAYMENT_ACTION_EXECUTED,
                    ]


