pragma solidity ^0.8.0;

import "interfaces/IPostPaymentAction.sol";
import "contracts/Receipt.sol";
import "contracts/PaymentRequest.sol";

contract DisablePaymentRequestPaymentPostAction is IPostPaymentAction {
    function onPostPayment(address receipt, uint256 receiptId) override external {
        // This PostPaymentAction requires the ownership of a PaymentRequest. As such, the PaymentRequest should
        // be created using either createWithStaticTokenAmountFor() or createWithDynamicTokenAmountFor()
        Receipt receiptContract = Receipt(receipt);
        ReceiptData memory receiptData = receiptContract.getReceiptData(receiptId);

        PaymentRequest paymentRequest = PaymentRequest(receiptData.paymentRequest);
        paymentRequest.disable(receiptData.paymentRequestId);
    }
}
