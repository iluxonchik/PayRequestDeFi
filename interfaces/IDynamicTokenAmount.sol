pragma solidity ^0.8.0;

interface IDynamicTokenAmount {
    // For the case of dynamic payments, the communication about which token payments are accepted, is outside of
    // the scope of this interface. One idea that I have is to provide a isPaymentInTokenAccepted() function which
    // would return a boolean. However, this is not required for the functionality of the PaymentRequest. If desired,
    // it can be implemented as a part of a separate interface.

    /// @notice Returns the amount of tokens for a particular paymentRequest ID.
    function getAmountForToken(uint256 paymentRequestId, address token, address payer) external returns (uint256);
 }