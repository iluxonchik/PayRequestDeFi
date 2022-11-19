pragma solidity ^0.8.0;

import "./Demo1.sol";

contract Demo2 {
    Demo1 public demo;

    constructor(address cntAddr) {
        demo = Demo1(cntAddr);
    }

    function call() payable public {
        demo.hello{value: msg.value}();
    }
}