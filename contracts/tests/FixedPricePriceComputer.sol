pragma solidity ^0.8.0;
import "interfaces/IPriceComputer.sol";

contract FixedPricePriceComputer is IPriceComputer {
    uint256 public price;

    constructor(uint256 _price) {
        price = _price;
    }

    function getPriceForToken(uint256 paymentRequestId, address tokenAddr, address payer) external override returns (uint256) {
        return price;
    }
}