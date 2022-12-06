pragma solidity ^0.8.0;

// contracts/MyNFT.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract MyERC721 is ERC721 {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenId;

    constructor(string memory name, string memory symbol) ERC721(name, symbol) {}

    function create(address owner) public returns (uint256) {
        uint256 tokenId = _tokenId.current();
        _mint(owner, tokenId);
        _tokenId.increment();
        return tokenId;
    }
}