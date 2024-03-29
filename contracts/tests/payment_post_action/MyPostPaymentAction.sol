pragma solidity ^0.8.0;
import "interfaces/IPostPaymentAction.sol";
import "contracts/PaymentRequest.sol";
import "contracts/Receipt.sol";

contract MyPostPaymentAction is IPostPaymentAction {
    event DynamicTokenAmountPPAExecuted(
        address receipt,
        uint256 receiptId,
        address receiptToken,
        uint256 receiptTokenAmount,
        address payer,
        address payee
    );
    event StaticTokenAmountPPAExecuted(
        address receipt,
        uint256 receiptId,
        address receiptToken,
        uint256 receiptTokenAmount,
        address payer,
        address payee,
        address paymentRequestToken,
        uint256 paymentRequestTokenAmount
    );


    function onPostPayment(address receipt, uint256 receiptId) override external {
        Receipt receiptContract = Receipt(receipt);
        ReceiptData memory receiptMetadata  = receiptContract.getReceiptData(receiptId);
        address token = receiptMetadata.token;
        uint256 tokenAmount = receiptMetadata.tokenAmount;
        address payer = receiptMetadata.payer;
        address payee = receiptMetadata.payee;

        address paymentRequestAddr = receiptMetadata.paymentRequest;
        uint256 paymentRequestId = receiptMetadata.paymentRequestId;
        PaymentRequest paymentRequest = PaymentRequest(paymentRequestAddr);

        if (paymentRequest.isTokenAmountStatic(paymentRequestId)) {
            TokenAmountInfo[] memory tokenAmounts = paymentRequest.getStaticTokenAmountInfos(paymentRequestId);
            address firstToken = tokenAmounts[0].token;
            uint256 tokenAmountStatic = paymentRequest.getStaticAmountForToken(paymentRequestId, firstToken);
            emit StaticTokenAmountPPAExecuted(receipt, receiptId, token, tokenAmount, payer, payee, firstToken, tokenAmountStatic);
        } else {
            emit DynamicTokenAmountPPAExecuted(receipt, receiptId, token, tokenAmount, payer, payee);
        }

    }
}