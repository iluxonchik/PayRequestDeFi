pragma solidity ^0.8.0;
import "interfaces/ITokenAmountComputer.sol";

contract FixedTokenAmountComputer is ITokenAmountComputer {
    uint256 public price;

    constructor(uint256 _price) {
        price = _price;
    }

    function getAmountForToken(uint256 paymentRequestId, address tokenAddr, address payer) external override returns (uint256) {
        return price;
    }
}