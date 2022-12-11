pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

import "interfaces/IERC20.sol";

import {Payment} from "./libraries/Payment.sol";

contract Receipt is ERC721, Ownable {

    using Counters for Counters.Counter;
    Counters.Counter internal _tokenId;

    mapping(uint256 => Payment.Receipt) public receipt;

    constructor(string memory name, string memory symbol) ERC721(name, symbol) {}

    function create(uint256 paymentRequestId, address tokenAddr, uint256 tokenAmount, address payerAddr, address payeeAddr) public virtual returns (uint256) {
        uint256 ercTokenId = _tokenId.current();
        _mint(payerAddr, ercTokenId);
        _tokenId.increment();
        // PaymentRequest contract address can be obtained by ownerOf(<receiptId>)
        receipt[ercTokenId] = Payment.Receipt(
            {
                paymentRequestAddr: msg.sender,
                paymentRequestId: paymentRequestId,
                tokenAddr: tokenAddr,
                tokenAmount: tokenAmount,
                payerAddr: payerAddr,
                payeeAddr: payeeAddr
            }
        );
        return ercTokenId;

    }

    function getReceipt(uint256 receiptId) public view returns (Payment.Receipt memory) {
        return receipt[receiptId];
    }
}