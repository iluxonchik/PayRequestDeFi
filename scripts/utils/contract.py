import random
from typing import cast

from brownie import PaymentRequest, Receipt, MyERC20, NFTOwnerPaymentPrecondition, MyERC721, FixedTokenAmountComputer, MyPostPaymentAction
from brownie.network.account import Account
from brownie.network.contract import ContractContainer, ProjectContract

from scripts.utils.types import NFTOwnerPaymentPreconditionMeta, NFTOwnerPaymentPreconditionWithMeta


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

    @staticmethod
    def get_my_erc20_contract(*, account: Account, force_deploy: bool = False) -> MyERC20:
        args: tuple = (MyERC20, account, "Jasmine", "JSM", 1999999)
        return force_deploy_contract_instance(*args) if force_deploy else get_or_create_deployed_instance(*args)

    @staticmethod
    def get_my_erc_721_contract(*, account: Account, force_deploy: bool = False) -> MyERC721:
        args: tuple = (MyERC721, account, "JasmineBut721", "JSM721")
        return force_deploy_contract_instance(*args) if force_deploy else get_or_create_deployed_instance(*args)

    @staticmethod
    def get_nft_owner_payment_precondition(*, erc20TokenAddr: str, erc721TokenAddr: str, account: Account, force_deploy: bool = False) -> NFTOwnerPaymentPrecondition:
        args: tuple = (NFTOwnerPaymentPrecondition, account, erc20TokenAddr, erc721TokenAddr)
        return force_deploy_contract_instance(*args) if force_deploy else get_or_create_deployed_instance(*args)

    @staticmethod
    def get_fixed_token_amount_computer(*, price: int, account: Account, force_deploy: bool = False) -> FixedTokenAmountComputer:
        args: tuple = (FixedTokenAmountComputer, account, price)
        return force_deploy_contract_instance(*args) if force_deploy else get_or_create_deployed_instance(*args)

    @staticmethod
    def get_my_post_payment_action(*, account: Account, force_deploy: bool = False) -> MyPostPaymentAction:
        args: tuple = (MyPostPaymentAction, account)
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
    @property
    def MyERC20(self) -> MyERC20:
        return self.get_my_erc20_contract(account=self._account, force_deploy=self._force_deploy)

    @property
    def MyERC721(self) -> MyERC721:
        return self.get_my_erc_721_contract(account=self._account, force_deploy=self._force_deploy)

    @property
    def NFTOwnerPaymentPrecondition(self) -> NFTOwnerPaymentPreconditionWithMeta:
        erc20: MyERC20 = self.MyERC20
        erc721: MyERC721 = self.MyERC721

        precondition: NFTOwnerPaymentPrecondition = self.get_nft_owner_payment_precondition(
            erc20TokenAddr=erc20.address,
            erc721TokenAddr=erc721.address,
            account=self._account,
            force_deploy=self._force_deploy,
        )

        # Meta attribute attached, type is now changed
        precondition.Meta = NFTOwnerPaymentPreconditionMeta(erc20=erc20, erc721=erc721)
        precondition = cast(NFTOwnerPaymentPreconditionWithMeta, precondition)

        return precondition

    @property
    def FixedPricePaymentComputer(self) -> FixedTokenAmountComputer:
        price: int = random.randint(1, 99)
        return self.get_fixed_token_amount_computer(
            price=price,
            account=self._account,
            force_deploy=self._force_deploy,
        )

    @property
    def MyPostPaymentAction(self) -> MyPostPaymentAction:
        return self.get_my_post_payment_action(
            account=self._account,
            force_deploy=self._force_deploy,
        )
