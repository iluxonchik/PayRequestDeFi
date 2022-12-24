pragma solidity ^0.8.0;
import "interfaces/IPostPaymentAction.sol";
import "contracts/PaymentRequest.sol";
import "contracts/Receipt.sol";

import {Payment} from "contracts/libraries/Payment.sol";

contract MyPostPaymentAction is IPostPaymentAction {
    event DynamicTokenAmountPPAExecuted(address receipt, uint256 receiptId, address receiptToken, uint256 receiptTokenAmount, address payer, address payee, address paymentPrecondition);
    event StaticTokenAmountPPAExecuted(address receipt, uint256 receiptId, address receiptToken, uint256 receiptTokenAmount, address payer, address payee, address paymentPrecondition, address paymentRequestToken, uint256 paymentRequestTokenAmount);


    function onPostPayment(address receipt, uint256 receiptId) override external {
        Receipt receiptContract = Receipt(receipt);
        Payment.ReceiptData memory receiptMetadata  = receiptContract.getReceiptData(receiptId);
        address token = receiptMetadata.token;
        uint256 tokenAmount = receiptMetadata.tokenAmount;
        address payer = receiptMetadata.payer;
        address payee = receiptMetadata.payee;

        address paymentRequestAddr = receiptMetadata.paymentRequest;
        uint256 paymentRequestId = receiptMetadata.paymentRequestId;
        PaymentRequest paymentRequest = PaymentRequest(paymentRequestAddr);
        address paymentPrecondition = paymentRequest.getPaymentPrecondition(paymentRequestId);

        if (paymentRequest.isTokenAmountStatic(paymentRequestId)) {
            Payment.TokenAmountInfo[] memory tokenAmounts = paymentRequest.getStaticTokenAmountInfos(paymentRequestId);
            address firstToken = tokenAmounts[0].token;
            uint256 tokenAmountStatic = paymentRequest.getStaticAmountForToken(paymentRequestId, firstToken);
            emit StaticTokenAmountPPAExecuted(receipt, receiptId, token, tokenAmount, payer, payee, paymentPrecondition, firstToken, tokenAmountStatic);
        } else {
            emit DynamicTokenAmountPPAExecuted(receipt, receiptId, token, tokenAmount, payer, payee, paymentPrecondition);
        }

    }
}