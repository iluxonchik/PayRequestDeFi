pragma solidity ^0.8.0;

library Billing {

    /// @notice Price of token in terms of its amount. Mapping value interface.
    struct TokenPriceMappingValue {
        uint256 tokenAmmount;
        bool isSet;
    }

    /// @notice Token price interface. Contains the address of the token and its amount. Useful abstraction for pulic input paramaters.
    struct TokenPrice {
        address tokenAddr;
        uint256 tokenAmmount;
    }

    /// @notice Maps ERC-721 token ID to the token addrss that maps to the price in terms of the amount of that token.
    struct RequestPrice {
        mapping(uint => mapping(address => TokenPriceMappingValue)) tokenIdToPriceMap;
        mapping(uint => TokenPrice[]) tokenIdToPriceArray;
    }
    
    /// @notice Maps token address to the price in that token, in terms of its amount
    struct PriceByTokenID {
        mapping(address => TokenPriceMappingValue) tokenAddrToTokenAmount;
    }
}