pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "interfaces/IPaymentPrecondition.sol";

/// @notice Sample payment precondition contract that allows payment in a particular token, only if the payee owns a particular NFT.
/// For all other tokens, onlly allow payment if the payee has created a PaymentRequest from the sending contract.
contract NFTOwnerPaymentPrecondition is IPaymentPrecondition {
    address public requiredERC721;
    address public exclusivePaymentToken;

    constructor(address _exclusivePaymentToken, address _requiredERC721) {
        exclusivePaymentToken = _exclusivePaymentToken;
        requiredERC721 = _requiredERC721;
    }

    function isPaymentPreconditionMet(uint256 paymentRequestId, address payer, address token) external override returns(bool) {
        address erc721;
        if (token == exclusivePaymentToken) {
            erc721 = requiredERC721;
        } else {
            // assumes that message sending contract is an ERC721. in a real-world application you may find
            // address whitelisting desired
            erc721 = msg.sender;
        }

        ERC721 NFTContract = ERC721(erc721);
        uint256 balance = NFTContract.balanceOf(payer);
        return balance > 0;
    }
}