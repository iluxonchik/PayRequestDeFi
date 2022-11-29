pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

import "interfaces/IERC20.sol";



import {Billing} from "./libraries/Billing.sol";

contract Receipt is ERC721, Ownable {

    using Counters for Counters.Counter;
    Counters.Counter private _tokenId;

    mapping(uint256 => Billing.Receipt) public receipt;

    constructor(string memory name, string memory symbol) ERC721(name, symbol) {}

    function create(uint256 billingRequestId, address tokenId, uint256 tokenAmount, address payer, address payee) public onlyOwner returns (uint256) {
        uint256 ercTokenId = _tokenId.current();
        _mint(msg.sender, ercTokenId);
        _tokenId.increment();
        receipt[ercTokenId] = Billing.Receipt(
            {
                billingRequestId: billingRequestId,
                tokenId: tokenId,
                tokenAmount: tokenAmount,
                payer: payer,
                payee: payee
            }
        );
        return ercTokenId;

    }
}