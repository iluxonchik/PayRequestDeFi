from brownie import network
from brownie.network import Accounts, accounts

breakpoint()
network.connect('development')

breakpoint()
integration_test_accounts: Accounts = accounts
deployer_or_creator_accounts: Accounts = integration_test_accounts[:3]
interactor_accounts: Accounts = integration_test_accounts[len(deployer_or_creator_accounts):]

DEPLOYER_ACCOUNTS_START_INDEX: int = 0
DEPLOYER_ACCOUNTS_END_INDEX: int = len(deployer_or_creator_accounts) - 1

INTERACTOR_ACCOUNTS_START_INDEX: int = 0
INTERACTOR_ACCOUNTS_END_INDEX: int = len(interactor_accounts) - 1

