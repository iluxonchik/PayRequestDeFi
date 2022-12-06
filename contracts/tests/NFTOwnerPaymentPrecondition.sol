pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "interfaces/IPaymentPrecondition.sol";

/// @notice Sample payment precondition contract that allows payment in a particular token, only if the payee owns a particular NFT.
/// For all other tokens, onlly allow payment if the payee has created a PaymentRequest from the sending contract.
contract NFTOwnerPaymentPrecondition is IPaymentPrecondition {
    address public requiredERC721;
    address public exclusivePaymentToken;

    constructor(address exclusivePaymentToken, address requiredERC721) {
        exclusivePaymentToken = exclusivePaymentToken;
        requiredERC721 = requiredERC721;
    }

    function isPaymentPreconditionMet(uint256 paymentRequestId, address payee, address token) external returns(bool) {
        address erc721;
        if (token == exclusivePaymentToken) {
            erc721 = token;
        } else {
            // assumes that message sending contract is an ERC721. in a real-world application you may find
            // address whitelisting desired
            erc721 = msg.sender;
        }

        ERC721 NFTContract = ERC721(erc721);
        return NFTContract.balanceOf(payee) > 0;
    }
}