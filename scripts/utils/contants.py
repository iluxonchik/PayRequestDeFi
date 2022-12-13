from typing import List

LOCAL_BLOCKCHAIN_ENVIRONMENTS: List[str] = [
    "ganache-gui",
    "ganache-local",
    "development",
]

class Events:
    STATIC_PRICE_PPA_EXECUTED: str = "StaticPricePPAExecuted"
    DYNAMIC_PRICE_PPA_EXECUTED: str = "DynamicPricePPAExecuted"
