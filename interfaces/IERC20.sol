pragma solidity ^0.8.0;

/// @notice ERC20 interface with strictly limited functions required.
interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    
    function transferFrom(
        address from,
        address to,
        uint256 amount
    ) external returns (bool);

    function transfer(address to, uint256 amount) external returns (bool);
}