pragma solidity ^0.8.0;


contract Demo1 {
    address public callee;
    uint256 public value;

    function hello() public payable {
        callee = msg.sender;
        value = msg.value;

    }
}
