pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

import {Billing} from "./libraries/Billing.sol";

// in the context below, "BillingRequest" can be in place of ERC-721 and vice-versa.
contract BillingRequest is ERC721 {

    using Counters for Counters.Counter;
    Counters.Counter private _tokenId;
    // map of Billing Request ERC-721 to its prices
    Billing.RequestPrice internal requestPrice;
    mapping(address => uint256[]) public tokenIdsCreatedByAddr;

    constructor() ERC721("Billing Request", "BRQ") {}

    /// @notice Stores the provided billing request prices in the internal storage of the contract
    function _storePricesInInternalStructures(uint256 tokenId, Billing.TokenPrice[] memory prices) internal {
        requestPrice.tokenIdToPriceArray[tokenId] = prices;
        for (uint i = 0; i < requestPrice.tokenIdToPriceArray[tokenId].length; i++) {
            Billing.TokenPrice storage price = requestPrice.tokenIdToPriceArray[tokenId][i];
            requestPrice.tokenIdToPriceMap[tokenId][price.tokenAddr] = Billing.TokenPriceMappingValue({
                tokenAmmount: price.tokenAmmount,
                isSet: true
            });
        }
    }
    function create(Billing.TokenPrice[] memory prices, address payTo) public returns (uint256) {
        uint256 tokenId = _tokenId.current();
        // the payments will be done to the owner of the ERC720. the "lending" of payTo should be done via another SC
        _mint(payTo, tokenId);
        _tokenId.increment();

        // map token prices into internal data structure
        _storePricesInInternalStructures(_tokenId.current(), prices);
        tokenIdsCreatedByAddr[msg.sender].push(tokenId);

        return tokenId;

    }

    function create(Billing.TokenPrice[] memory prices) public returns (uint256) {
        return create(prices, msg.sender);
    }


     

}