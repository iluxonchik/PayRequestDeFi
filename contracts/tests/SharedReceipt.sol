pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "contracts/Receipt.sol";

/// @notice SharedReceipt is a type of receipt, where any contract is allowed to create an instance of it. It may be useful in a sceenario
/// where the same Receipt can be emitted for multiple PaymentRequests. This contract is for EXAMPLE purposes only, to showcase how such
/// a receipt system can be implemented.
contract SharedReceipt is Ownable, Receipt {

    mapping(address => uint256[]) internal receiptIdsCreatedByAddr;
    mapping(address => mapping(address => uint256[])) internal receiptIdsCreatedByAddrAndPaidByAddr;

    constructor(string memory name, string memory symbol) Receipt(name, symbol) {}

    function create(uint256 paymentRequestId, address tokenId, uint256 tokenAmount, address payer, address payee) public override returns (uint256) {
        uint256 receiptId = super.create(paymentRequestId, tokenId, tokenAmount, payer, payee);
        
        receiptIdsCreatedByAddr[msg.sender].push(receiptId);
        receiptIdsCreatedByAddrAndPaidByAddr[msg.sender][payer].push(receiptId);
        
        return receiptId;
    }

    function getReceiptIdsCreatedBy(address creator) public view returns (uint256[] memory) {
        return receiptIdsCreatedByAddr[creator];
    }

    function getReceiptIdsCreatedByAndPaidBy(address creator, address payer) public view returns (uint256[] memory) {
        return receiptIdsCreatedByAddrAndPaidByAddr[creator][payer];
    }

    function getNumberOfReceiptIdsCreatedBy(address creator) public view returns (uint256) {
        return receiptIdsCreatedByAddr[creator].length;
    }

    function getNumberReceiptIdsCreatedByAndPaidBy(address creator, address payer) public view returns (uint256) {
        return receiptIdsCreatedByAddrAndPaidByAddr[creator][payer].length;
    }
    
}
