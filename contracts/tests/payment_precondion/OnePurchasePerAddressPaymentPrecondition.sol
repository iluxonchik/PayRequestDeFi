pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "interfaces/IPaymentPrecondition.sol";
import "contracts/PaymentRequest.sol";

/// @notice Sample payment precondition contract that allows payment in a particular token only if the address has not purchased
/// the paymentRequestId in question.
contract OnePurchasePerAddressPaymentPrecondition is IPaymentPrecondition {

    function isPaymentAllowed(uint256 paymentRequestId, address token, address payer, address beneficiary) external override returns(bool) {
        PaymentRequest paymentRequest = PaymentRequest(msg.sender);
        Receipt receipt = paymentRequest.receipt();

    }
}