pragma solidity ^0.8.0;
import "interfaces/IPostPaymentAction.sol";
import "contracts/PaymentRequest.sol";
import "contracts/Receipt.sol";

import {Payment} from "contracts/libraries/Payment.sol";

contract MyPostPaymentAction is IPostPaymentAction {
    event DynamicTokenAmountPPAExecuted(address receiptAddr, uint256 receiptId, address receiptTokenAddr, uint256 receiptTokenAmount, address payer, address payee, address paymentPreconditionAddr);
    event StaticTokenAmountPPAExecuted(address receiptAddr, uint256 receiptId, address receiptTokenAddr, uint256 receiptTokenAmount, address payer, address payee, address paymentPreconditionAddr, address paymentRequestTokenAddr, uint256 paymentRequestTokenAmount);


    function onPostPayment(address receiptAddr, uint256 receiptId) override external {
        Receipt receipt = Receipt(receiptAddr);
        Payment.Receipt memory receiptMetadata  = receipt.getReceipt(receiptId);
        address tokenAddr = receiptMetadata.tokenAddr;
        uint256 tokenAmount = receiptMetadata.tokenAmount;
        address payer = receiptMetadata.payerAddr;
        address payee = receiptMetadata.payeeAddr;

        address paymentRequestAddr = receiptMetadata.paymentRequestAddr;
        uint256 paymentRequestId = receiptMetadata.paymentRequestId;
        PaymentRequest paymentRequest = PaymentRequest(paymentRequestAddr);
        address paymentPreconditionAddr = paymentRequest.getPaymentPreconditionAddr(paymentRequestId);

        if (paymentRequest.isTokenAmountStatic(paymentRequestId)) {
            Payment.TokenAmountInfo[] memory tokenAmounts = paymentRequest.getStaticTokenAmountInfos(paymentRequestId);
            address firstTokenAddr = tokenAmounts[0].tokenAddr;
            uint256 tokenAmountStatic = paymentRequest.getStaticAmountForToken(paymentRequestId, firstTokenAddr);
            emit StaticTokenAmountPPAExecuted(receiptAddr, receiptId, tokenAddr, tokenAmount, payer, payee, paymentPreconditionAddr, firstTokenAddr, tokenAmountStatic);
        } else {
            emit DynamicTokenAmountPPAExecuted(receiptAddr, receiptId, tokenAddr, tokenAmount, payer, payee, paymentPreconditionAddr);
        }

    }
}