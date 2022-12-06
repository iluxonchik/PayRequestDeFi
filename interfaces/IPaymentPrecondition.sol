pragma solidity ^0.8.0;

interface IPaymentPrecondition {
    /// @notice Function that checks whether the payment for a particular payment request is allowed for the payer.
    /// To allow the payment request processing to proceed true should be returned.
    /// To disallow the payment request processing to proceed, either false should be returned, or a revert should be done.
    /// Performing a revert is useful if your goal is to provide the caller with a detailed error message. Returning false
    /// is desirable if your goal is to display a generic error message. The returning of the false value could be particulary
    /// useful in Zero-Knowledge type of computations, where you may not want to expose the specific conidtion which was not
    /// met by the caller.
    function isPaymentPreconditionMet(uint256 paymentRequestId, address payer, address token) external returns(bool);
}