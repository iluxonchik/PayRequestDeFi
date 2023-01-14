pragma solidity ^0.8.0;

import "interfaces/IPostPaymentAction.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "contracts/Receipt.sol";

contract TransferNFTPaymentPostAction is IPostPaymentAction {
    IERC721 public erc721;
    uint256 public erc721Id;


    constructor(address _erc721Contract, uint256 _erc721Id) {
        erc721 = IERC721(_erc721Contract);
        erc721Id = _erc721Id;
    }

    function onPostPayment(address receipt, uint256 receiptId) override external {
        // Transfer NFT under the control of this Smart Contract. As such, this particular smart contract requires
        // that the owner of the NFT approves transfers from their address into the address of this smart contract.
        // In the context of the PaymentRequest.pay(), if the token was not approved, the whole payment will be
        // reverted.

        address owner = erc721.ownerOf(erc721Id);
        erc721.transferFrom(owner, address(this), erc721Id);

        // Now, transfer the NFT from this contract to the payer's contract
        Receipt receiptContract = Receipt(receipt);
        ReceiptData memory receiptData = receiptContract.getReceiptData(receiptId);
        erc721.safeTransferFrom(address(this), receiptData.payer, erc721Id);
    }
}
