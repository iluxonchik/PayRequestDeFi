pragma solidity ^0.8.0;

interface IPostPaymentActionWithData {
    /// @notice Executes the post-payment action. The address and the token ID of the receipt are passed as arguments.
    /// From those two values, all of the necessary information about the bill can be obtained.
    /// Since the receipt address is passed alongside its ID, the post-payment action can operate with multiple distinct
    /// receipt contracts, which means it can operate with distinct PaymentRequest contract implementations, which also
    /// allows it to function on contract upgrades.
    function onPostPayment(address receipt, uint256 receiptId, address data, uint256 dataId) external;
}