pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "interfaces/IERC20.sol";
import "contracts/Receipt.sol";

import {Payment} from "./libraries/Payment.sol";

/// @notice ExclusiveReceipt is a type of receipt, where only the owner of the contract is allowed to create receipts.
/// This is useful in case you want to have a receipt emission system that can only be used by your PaymentRequest instance.
contract ExclusiveReceipt is Ownable, Receipt {
    constructor(string memory name, string memory symbol) Receipt(name, symbol) {}

    function create(uint256 paymentRequestId, address tokenId, uint256 tokenAmount, address payerAddr, address payeeAddr) public override onlyOwner returns (uint256) {
        super.create(paymentRequestId, tokenId, tokenAmount, payerAddr, payeeAddr);

    }
}