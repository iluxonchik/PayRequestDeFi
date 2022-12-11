pragma solidity ^0.8.0;
import "interfaces/IPostPaymentAction.sol";
import "contracts/PaymentRequest.sol";
import "contracts/Receipt.sol";

import {Payment} from "contracts/libraries/Payment.sol";

contract MyPostPaymentAction is IPostPaymentAction {
    event DynamicPricePPAExecuted(address receiptAddr, uint256 receiptId, address tokenAddr, uint256 tokenAmount, address payer, address payee, address paymentPreconditionAddr);
    event StaticPricePPAExecuted(address receiptAddr, uint256 receiptId, address tokenAddr, uint256 tokenAmount, address payer, address payee, address paymentPreconditionAddr, address tokenAddr, uint256 price);


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
        address paymentPreconditionAddr = paymentRequest.tokenIdToPaymentPrecondition(paymentRequestId);

        if (paymentRequest.isPriceStatic(paymentRequestId)) {
            Payment.TokenPrice[] memory tokenPrices = paymentRequest.getStaticTokenPrices(paymentRequestId);
            address firstTokenAddr = tokenPrices[0].tokenAddr;
            uint256 tokenPrice = paymentRequest.getStaticTokenPrice(paymentRequestId, firstTokenAddr);
            emit StaticPricePPAExecuted(receiptAddr, receiptId, tokenAddr, tokenAmount, payer, payee, paymentPreconditionAddr, firstTokenAddr, tokenPrice);
        }

        emit DynamicPricePPAExecuted(receiptAddr, receiptId, tokenAddr, tokenAmount, payer, payee, paymentPreconditionAddr);
    }
}