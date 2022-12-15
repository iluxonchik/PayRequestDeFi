pragma solidity ^0.8.0;

interface ITokenAmountComputer {
    // For the case of dynamic payments, the communication about which token payments are accepted, is outside of
    // the scope of this interface. One idea that I have is to provide a isPaymentInTokenAccepted() function which
    // would return a boolean. However, this is not required for the functionality of the PaymentRequest. If desired,
    // it can be implemented as a part of a separate interface.

    /// @notice Returns the amount for a given TokenID.
    function getAmountForToken(uint256 paymentRequestId, address tokenAddr, address payer) external returns (uint256);
 }