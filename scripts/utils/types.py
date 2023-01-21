from __future__ import annotations

from dataclasses import dataclass

from brownie.network.contract import ProjectContract


@dataclass
class NFTOwnerPaymentPreconditionMeta:
    erc20: ProjectContract
    erc721: ProjectContract


class NFTOwnerPaymentPreconditionWithMeta(ProjectContract):
    Meta = NFTOwnerPaymentPreconditionMeta


@dataclass
class TransferNFTPaymentPostActionMeta:
    erc721: ProjectContract
    erc721_id: int


class TransferNFTPaymentPostActionWithMeta(ProjectContract):
    Meta = TransferNFTPaymentPostActionMeta
