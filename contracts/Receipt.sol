pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

import {Payment} from "./libraries/Payment.sol";

/// @notice Receipt that is emitted upon successful payment. A Receipt's ownership is assigned to the payerAddres and it can be
/// transferred to another address. A record of both, the address that emitted the receipt (a PaymentRequest under regular use-case)
/// and the original payer. Getter functions to obtain the list of Receipt IDs origninally issued to a particular address are available.
contract Receipt is ERC721Enumerable, Ownable {

    using Counters for Counters.Counter;
    Counters.Counter internal _tokenId;

    mapping(uint256 => Payment.ReceiptData) internal receipt;
    mapping(address => uint256[]) internal receiptIdsPaidByAddr;

    constructor(string memory name, string memory symbol) ERC721(name, symbol) {}

    function create(uint256 paymentRequestId, address tokenAddr, uint256 tokenAmount, address payerAddr, address payeeAddr) public virtual onlyOwner returns (uint256) {
        uint256 receiptId = _tokenId.current();
        _mint(payerAddr, receiptId);
        _tokenId.increment();

        // technically, this receipt can be emitted by anyone, so msg.sender can be arbitrary. as such, you need to verify
        // what paymentRequestAddr points to. for a Receipt that is only emittable by a particular PaymentRequest contract
        // see ExclusiveReceipt.sol
        receipt[receiptId] = Payment.ReceiptData(
            {
                paymentRequestAddr: msg.sender, // PaymentRequest that emitted the receipt
                paymentRequestId: paymentRequestId,
                tokenAddr: tokenAddr,
                tokenAmount: tokenAmount,
                payerAddr: payerAddr, // Address that performed the payment, i.e. called pay() on the PaymentRequest instance
                payeeAddr: payeeAddr
            }
        );
        receiptIdsPaidByAddr[payerAddr].push(receiptId);
        
        return receiptId;

    }

    function getReceiptData(uint256 receiptId) public view returns (Payment.ReceiptData memory) {
        return receipt[receiptId];
    }

    function getNumberOfReceiptsPaidBy(address payer) public view returns (uint256) {
        return receiptIdsPaidByAddr[payer].length;
    }

    function getReceiptIdsPaidBy(address payer) public view returns (uint256[] memory) {
        return receiptIdsPaidByAddr[payer];
    }

    function getReceiptIdPaidByAtIndex(address payer, uint256 index) public view returns (uint256) {
        return receiptIdsPaidByAddr[payer][index];
    }
}