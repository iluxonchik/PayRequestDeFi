pragma solidity ^0.8.0;

library Billing {

    /// @notice Price of token in terms of its amount. Mapping value interface.
    struct TokenPriceMappingValue {
        uint256 tokenAmount;
        bool isSet;
    }

    /// @notice Token price interface. Contains the address of the token and its amount. Useful abstraction for pulic input paramaters.
    struct TokenPrice {
        address tokenAddr;
        uint256 tokenAmount;
    }

    struct Receipt {
        uint256 billingRequestId;
        address tokenId;
        uint256 tokenAmount;
        address payer;
        address payee;
    }
}