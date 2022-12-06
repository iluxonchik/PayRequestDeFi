from __future__ import annotations

from dataclasses import dataclass

from brownie.network.contract import ProjectContract


@dataclass
class NFTOwnerPaymentPreconditionMeta:
    erc20: ProjectContract
    erc721: ProjectContract


class NFTOwnerPaymentPreconditionWithMeta(ProjectContract):
    Meta = NFTOwnerPaymentPreconditionMeta
