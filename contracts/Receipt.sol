pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

struct ReceiptData {
        address paymentRequest;
        uint256 paymentRequestId;
        address token;
        uint256 tokenAmount;
        address payer;
        address payee;
}

struct OptionalReceiptDataLocation {
    address data;
    uint256 dataId;
    bool isSet;
}

/// @notice Receipt that is emitted upon successful payment. A Receipt's ownership is assigned to the payerAddres and it can be
/// transferred to another address. A record of both, the address that emitted the receipt (a PaymentRequest under regular use-case)
/// and the original payer. Getter functions to obtain the list of Receipt IDs origninally issued to a particular address are available.
contract Receipt is ERC721Enumerable, Ownable {
    using Counters for Counters.Counter;
    Counters.Counter internal _tokenId;

    mapping(uint256 => ReceiptData) internal receiptData;
    mapping(uint256 => OptionalReceiptDataLocation) internal optionalReceiptDataLocation;
    // paymentRequestId --> address (Payer) --> receiptIds paid by Payer
    mapping(address => uint256[]) internal receiptIdsPaidByAddr;
    mapping(uint256 => mapping(address => uint256[])) internal receiptIdsPaidByAddrForPaymentRequestId;
    
    // Strucutres to store and access access ReceiptIDs and their owners for a particular PaymentRequestID
    mapping(uint256 => mapping(address => uint256)) internal _balancesForPaymentRequestId;
    mapping(uint256 => mapping(address => mapping(uint256 => uint256))) internal _ownedTokensForPaymentRequestId;
    mapping(uint256 => mapping(uint256 => uint256)) internal _ownedTokensIndexForPaymentRequestId;
    mapping(uint256 => uint256[]) internal _allTokensForPaymentRequestId;
    mapping(uint256 => mapping(uint256 => uint256)) internal _allTokensIndexForPaymentRequestId;

    constructor(string memory name, string memory symbol) ERC721(name, symbol) {}

    // Receipt creators without data
    function create(uint256 paymentRequestId, address token, uint256 tokenAmount, address payer, address payee) public virtual onlyOwner returns (uint256) {
        uint256 receiptId = _tokenId.current();
        _mint(payer, receiptId);
        _tokenId.increment();

        receiptData[receiptId] = ReceiptData(
            {
                paymentRequest: msg.sender, // PaymentRequest that emitted the receipt
                paymentRequestId: paymentRequestId,
                token: token,
                tokenAmount: tokenAmount,
                payer: payer, // Address that performed the payment, i.e. called pay() on the PaymentRequest instance
                payee: payee
            }
        );
        receiptIdsPaidByAddr[payer].push(receiptId);
        receiptIdsPaidByAddrForPaymentRequestId[paymentRequestId][payer].push(receiptId);
        
        return receiptId;
    }

    // Receipt creators with Data
    function create(uint256 paymentRequestId, address token, uint256 tokenAmount, address payer, address payee, address data, uint256 dataId) public virtual onlyOwner returns (uint256) {
       uint256 receiptId = create(
        {
            paymentRequestId: paymentRequestId,
            token: token,
            tokenAmount: tokenAmount,
            payer: payer,
            payee: payee
        }
        );
        
        optionalReceiptDataLocation[receiptId] = OptionalReceiptDataLocation(
            {
                data: data, // address of the contract containing extra data
                dataId: dataId, // ID of the extra data in the "data" smart contract
                isSet: true
                
            }
        );

        return receiptId;
    }

    function balanceOfForPaymentRequestId(uint256 paymentRequestId, address owner) public view virtual returns (uint256) {
        return _balancesForPaymentRequestId[paymentRequestId][owner];
    }

    /*
        // https://docs.openzeppelin.com/contracts/4.x/api/token/erc721#ERC721-_beforeTokenTransfer-address-address-uint256-uint256-
        // "from" and "to" non-zero: "from"'s token is transferred to "to".
        // "from" is zero: token minted to "to".
        // "to" is zero: "from"'s token will be burned. Since ERC721Burnable is not implemented, and _burn() is not called within this
        //     smart contract's code, it will never be 0
        // since ERC721Consecutive is not implemented, batchSize will always be 1
    */
    function _beforeTokenTransfer(address from, address to, uint256 receiptId, uint256 batchSize) internal virtual override {
        super._beforeTokenTransfer(from, to, receiptId, batchSize);
        
        if (batchSize > 1) {
            // Batching only possible during the construction phase, not after it.
            revert("Receipt: consecutive transfers not supported");
        }

        ReceiptData memory receiptDataStruct = receiptData[receiptId];
        uint256 paymentRequestId = receiptDataStruct.paymentRequestId;

        // First, deal with balances changes
        if (from != address(0)) {
            // receipt is being transferred from "from" to "to" (i.e. non-mint operation)
            _balancesForPaymentRequestId[paymentRequestId][from] -= 1;
        }
        if (to != address(0)) {
            _balancesForPaymentRequestId[paymentRequestId][to] += 1;
        }
        
        // Now, take care of altering collections as needed
        // First, do all of the necessary changes for the "from" address
        if (from == address(0)) {
            // mint operation
            _addTokenToAllTokensEnumerationForPaymentRequestId(paymentRequestId, receiptId);
        } else if (from != to) {
            // token transferred to an address distinct from current owner. remove ownership from "from"
            _removeTokenFromOwnerEnumerationForPaymentRequestId(paymentRequestId, from, receiptId);
        }

        // Second, do all of the necessary changes for the "to" address
        if (to == address(0)) {
            // burn operation
            _removeTokenFromAllTokensEnumerationForPaymentRequestId(paymentRequestId, receiptId);
        } else if(to != from) {
            // token transferred to an address distinct from the current owner. add ownershipt to "to"
            _addTokenToOwnerEnumerationForPaymentRequestId(paymentRequestId, to, receiptId);
        }
        
    }

    function _addTokenToAllTokensEnumerationForPaymentRequestId(uint256 paymentRequestId, uint256 tokenId) private {
        _allTokensIndexForPaymentRequestId[paymentRequestId][tokenId] = _allTokensForPaymentRequestId[paymentRequestId].length;
        _allTokensForPaymentRequestId[paymentRequestId].push(tokenId);
    }

    function _addTokenToOwnerEnumerationForPaymentRequestId(uint256 paymentRequestId, address to, uint256 receiptId) private {
        uint256 length = balanceOfForPaymentRequestId(paymentRequestId, to);
        _ownedTokensForPaymentRequestId[paymentRequestId][to][length] = receiptId;
        _ownedTokensIndexForPaymentRequestId[paymentRequestId][receiptId] = length;
    }

    function _removeTokenFromAllTokensEnumerationForPaymentRequestId(uint256 paymentRequestId, uint256 receiptId) private {
        // Move last receipt into the place of the token to remove, and delete the last index
        uint256 lastReceiptIndex = _allTokensForPaymentRequestId[paymentRequestId].length;
        uint256 lastReceiptId = _allTokensForPaymentRequestId[paymentRequestId][lastReceiptIndex];
        uint256 indexOfReceiptToRemove = _allTokensIndexForPaymentRequestId[paymentRequestId][receiptId];

        _allTokensForPaymentRequestId[paymentRequestId][indexOfReceiptToRemove] = lastReceiptId;
        _allTokensIndexForPaymentRequestId[paymentRequestId][lastReceiptId] = indexOfReceiptToRemove;

        delete _allTokensIndexForPaymentRequestId[paymentRequestId][receiptId];
        _allTokensForPaymentRequestId[paymentRequestId].pop();
    }

    function _removeTokenFromOwnerEnumerationForPaymentRequestId(uint256 paymentRequestId, address from, uint256 receiptId) private {
        uint256 lastReceiptIndex = balanceOfForPaymentRequestId(paymentRequestId, from) - 1;
        uint256 receiptToRemoveIndex = _ownedTokensIndexForPaymentRequestId[paymentRequestId][receiptId];

        if (lastReceiptIndex != receiptToRemoveIndex) {
            // move the last receipt into the position of the receipt to remove 
            uint256 lastReceipt = _ownedTokensForPaymentRequestId[paymentRequestId][from][lastReceiptIndex];
            _ownedTokensForPaymentRequestId[paymentRequestId][from][receiptToRemoveIndex] = lastReceipt;
            _ownedTokensIndexForPaymentRequestId[paymentRequestId][lastReceipt] = receiptToRemoveIndex;
        }

        delete _ownedTokensForPaymentRequestId[paymentRequestId][from][lastReceiptIndex];
        delete _ownedTokensIndexForPaymentRequestId[paymentRequestId][receiptId];
    }

    function getReceiptData(uint256 receiptId) public view returns (ReceiptData memory) {
        return receiptData[receiptId];
    }

    function isOptionalReceiptDataLocationSet(uint256 receiptId) public view returns (bool) {
        return optionalReceiptDataLocation[receiptId].isSet;
    }

    function getReceiptDataLocation(uint256 receiptId) external view returns (OptionalReceiptDataLocation memory) {
        return optionalReceiptDataLocation[receiptId];
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
    
    function getNumberOfReceiptsForPaymentRequestPaidBy(uint256 paymentRequestId, address payer) public view returns (uint256) {
        return receiptIdsPaidByAddrForPaymentRequestId[paymentRequestId][payer].length;
    }

    function getReceiptIdsForPaymentRequestPaidBy(uint256 paymentRequestId, address payer) public view returns (uint256[] memory) {
        return receiptIdsPaidByAddrForPaymentRequestId[paymentRequestId][payer];
    }

    function getReceiptIdForPaymentRequestPaidByAtIndex(uint256 paymentRequestId, address payer, uint256 index) public view returns (uint256) {
        return receiptIdsPaidByAddrForPaymentRequestId[paymentRequestId][payer][index];
    }

    function receiptIdOfOwnerForPaymentRequestIdByIndex(uint256 paymentRequestId, address owner, uint256 index) public view virtual returns (uint256) {
        require(index < ERC721.balanceOf(owner), "Receipt: owner index out of bounds");
        return _ownedTokensForPaymentRequestId[paymentRequestId][owner][index];
    }

    function totalSupplyForPaymentRequestId(uint256 paymentRequestId) public view virtual returns (uint256) {
        return _allTokensForPaymentRequestId[paymentRequestId].length;
    }

    function receiptIdPaymentRequestIdByIndex(uint256 paymentRequestId, uint256 index) public view virtual returns (uint256) {
        require(index < totalSupplyForPaymentRequestId(paymentRequestId), "Receipt: global index out of bounds");
        return _allTokensForPaymentRequestId[paymentRequestId][index];
    }
}