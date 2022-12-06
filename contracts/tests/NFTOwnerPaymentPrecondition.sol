pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./interfaces/IPaymentPrecondition.sol";

/// @notice Sample payment precondition contract that allows payment in a particular token, only if the payee owns a particular NFT.
/// For all other tokens, onlly allow payment if the payee has created a PaymentRequest from the sending contract.
contract NFTOwnerPaymentPrecondition is IPaymentPrecondition {
    address public requiredERC721;
    address public exclusivePaymentToken;

    constructor(address exclusivePaymenttoken, address requiredERC721) {
        exclusivePaymentToken = exclusivePaymentToken;
        requiredERC721 = requiredERC721;
    }

    function isPaymentPreconditionMet(uint256 paymentRequestId, address payee, address token) external returns(bool) {
        // assumes that message sending contract is an ERC721. in a real-world application you may find address whitelisting desired
        ERC721 NFTContract = ERC721(token) ? token == exclusivePaymentToken : msg.sender;
        return NFTContract.balanceOf(payee) > 0;
    }
}