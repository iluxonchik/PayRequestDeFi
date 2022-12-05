pragma solidity ^0.8.0;

interface IPriceComputer {
    // For the case of dynamic payments, the communication about which token payments are accepted, is outside of
    // the scope of this interface. One idea that I have is to provide a isPaymentInTokenAccepted() function which
    // would return a boolean. However, this is not required for the functionality of the PaymetRequest. If desired,
    // it can be implemeted as a part of a separate interface.

    /// @notice Returns the price for a given TokenID.
    function getPriceForToken(uint256 paymentRequestId, address tokenAddr, address payer) external returns (uint256);
 }