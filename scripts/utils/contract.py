from brownie.network.account import Account
from brownie.network.contract import ContractContainer, ProjectContract
from brownie import PaymentRequest, Receipt


def force_deploy_contract_instance(contract_cls: ContractContainer, account: Account, *deploy_args) -> ProjectContract:
    deploy_args += ({"from": account},)
    return contract_cls.deploy(*deploy_args)


def get_or_create_deployed_instance(contract_cls: ContractContainer, account: Account, *deploy_args) -> ProjectContract:
    try:
        return contract_cls[0]
    except IndexError:
        return force_deploy_contract_instance(contract_cls, account, *deploy_args)

class ContractBuilder:

    def __init__(self, *, account: Account, force_deploy: bool = False):
        self._account = account
        self._force_deploy = force_deploy


    @staticmethod
    def get_receipt_contract(*, account: Account, force_deploy: bool = False) -> Receipt:
        args: tuple = (Receipt, account, "Receipt", "RCT")
        return force_deploy_contract_instance(*args) if force_deploy else get_or_create_deployed_instance(*args)

    @staticmethod
    def get_payment_request_contract(*, receipt: Receipt, account: Account, force_deploy: bool = False) -> PaymentRequest:
        args: tuple = (PaymentRequest, account, "PaymentRequest", "PRQ", receipt)
        return force_deploy_contract_instance(*args) if force_deploy else get_or_create_deployed_instance(*args)


    @property
    def account(self) -> Account:
        return self._account

    @property
    def is_force_deploy(self) -> bool:
        return self._account

    @property
    def Receipt(self) -> Receipt:
        return self.get_receipt_contract(account=self._account, force_deploy=self._force_deploy)

    @property
    def PaymentRequest(self) -> PaymentRequest:
        receipt: Receipt = self.get_receipt_contract(account=self.account, force_deploy=self._force_deploy)
        return self.get_payment_request_contract(receipt=receipt, account=self._account, force_deploy=self._force_deploy)
