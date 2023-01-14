pragma solidity ^0.8.0;

library Payment {

    /// @notice Amount of token in terms of its amount. Mapping value interface.
    struct TokenAmountMappingValue {
        uint256 tokenAmount;
        bool isSet;
    }

    /// @notice Token amount interface. Contains the address of the token and its amount. Useful abstraction for pulic input paramaters.
    struct TokenAmountInfo {
        address token;
        uint256 tokenAmount;
    }
}