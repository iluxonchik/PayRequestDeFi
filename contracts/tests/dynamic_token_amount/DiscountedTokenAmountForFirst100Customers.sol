pragma solidity ^0.8.0;

import "interfaces/IDynamicTokenAmount.sol";
import "contracts/PaymentRequest.sol";
import "contracts/Receipt.sol";

contract DiscountedTokenAmountForFirst100Customers is IDynamicTokenAmount {
    uint256 constant public PRICE = 100;
    uint256 constant public MAX_UNIQUE_PURCHASESS_FOR_DISCOUNT = 100;
    uint256 constant public DICOUNT_DIVIDER = 2;
    uint256 public numUniquePurchases = 0;
    mapping(address => bool) internal isPurchaseAccountedForAddr;

    function getAmountForToken(uint256 paymentRequestId, address token, address payer) public override returns (uint256) {
        PaymentRequest paymentRequest = PaymentRequest(msg.sender);
        Receipt receipt = Receipt(paymentRequest.receipt());

        if (numUniquePurchases <= MAX_UNIQUE_PURCHASESS_FOR_DISCOUNT) {
            // check if payer has purchased before
            uint256 numPurchasesByPayer = receipt.getNumberOfReceiptsPaidBy(payer);
            if (numPurchasesByPayer == 0) {
                // valid state. for example, the payer may be inquiring for the price that they would have to pay
                return PRICE / DICOUNT_DIVIDER;
            } else if (numPurchasesByPayer == 1) {
                // only incremenet unique purchases if the purchase for address has not been accounted for yet
                if (!isPurchaseAccountedForAddr[payer]) {
                    numUniquePurchases += 1;
                    isPurchaseAccountedForAddr[payer] = true;
                }
                return PRICE / DICOUNT_DIVIDER;
            } else {
                return PRICE;
            }
        }
    }
    function isTokenAccepted(uint256 paymentRequestId, address token, address payer) public override returns (bool) {
        return true;
    }
}