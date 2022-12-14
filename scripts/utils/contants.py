from typing import List

LOCAL_BLOCKCHAIN_ENVIRONMENTS: List[str] = [
    "ganache-gui",
    "ganache-local",
    "development",
]

class Events:
    STATIC_TOKEN_AMOUNT_PPA_EXECUTED: str = "StaticTokenAmountPPAExecuted"
    DYNAMIC_TOKEN_AMOUNT_PPA_EXECUTED: str = "DynamicTokenAmountPPAExecuted"
