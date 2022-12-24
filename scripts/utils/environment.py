from brownie import network

from scripts.utils.contants import LOCAL_BLOCKCHAIN_ENVIRONMENTS


def is_local_blockchain_environment() -> bool:
    return network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS
