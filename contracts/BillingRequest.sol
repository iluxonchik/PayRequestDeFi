pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "interfaces/IERC20.sol";


import {Billing} from "./libraries/Billing.sol";

// TODO: abstract all of the bill storage into a separate contract

// in the context below, "BillingRequest" can be in place of ERC-721 and vice-versa.
contract BillingRequest is ERC721 {

    event BillPaid(uint256 billId, address buyer, address seller, address token, uint256 amount);

    using Counters for Counters.Counter;
    Counters.Counter private _tokenId;

    mapping(address => uint256[]) public tokenIdsCreatedByAddr;

    // map of Billing Request ERC-721 to its prices
    mapping(uint => mapping(address => Billing.TokenPriceMappingValue)) public tokenIdToPriceMap;
    mapping(uint => Billing.TokenPrice[]) public tokenIdToPriceArray;

    constructor() ERC721("Billing Request", "BRQ") {}

    /// @notice Stores the provided billing request prices in the internal storage of the contract
    /// There is is large risk in storing and enabling calls to unverified token addresses, as you do not know
    /// what the smart contracts at those addresses do. For example, they may be calling approve on a completely
    /// different set of tokens. Thouhg should be put into wether the whitelisting of addresses should be done
    /// by this smart contract or an outside one. One idea is to use the number of interactions with a smart
    /// contract as an initial measure of trust. For example, if the number of interactions with a smart contract
    /// is below 1000, then rquire an additional explicit confirmation. However, such as sytem is outside of the
    /// scope of the initial version of this module.
    function _storePricesInInternalStructures(uint256 tokenId, Billing.TokenPrice[] memory prices) internal {
        for (uint i = 0; i < prices.length; i++) {
            Billing.TokenPrice memory price = prices[i];
            tokenIdToPriceMap[tokenId][price.tokenAddr] = Billing.TokenPriceMappingValue({
                tokenAmount: price.tokenAmount,
                isSet: true
            });
            tokenIdToPriceArray[tokenId].push(price);
        }
    }

    /// @notice Retuns the TokenPriceMappingValue for a given bill and token pair. Practically, this allows
    /// you to obtain price in tokens for a given contract address, or identify that the provided bill ID
    /// does not accept payments in the provided token ID. You should always check the isSet variable of the
    /// reutned struct: if it false, the payments in the provided token are not defined.
    /// Both parts done in a single function to be more gas efficient.
    function getPriceForTokenId(uint256 billId, address tokenAddr) public view returns (Billing.TokenPriceMappingValue memory) {
        return tokenIdToPriceMap[billId][tokenAddr];
    }

    function create(Billing.TokenPrice[] memory prices, address payTo) public returns (uint256) {
        uint256 tokenId = _tokenId.current();
        // the payments will be done to the owner of the ERC720. the "lending" of payTo should be done via another SC
        _mint(payTo, tokenId);

        // map token prices into internal data structure
        _storePricesInInternalStructures(tokenId, prices);
        tokenIdsCreatedByAddr[msg.sender].push(tokenId);
        _tokenId.increment();
        return tokenId;

    }

    function create(Billing.TokenPrice[] memory prices) public returns (uint256) {
        return create(prices, msg.sender);
    }

    function payBill(uint256 billId, address tokenAddr) external returns (bool) {
        // immune to attack described in https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729,
        // since the approval and the transfer are done one after another.

        // verify that token addr is in digital bill
        Billing.TokenPriceMappingValue memory tokenPrice = getPriceForTokenId(billId, tokenAddr);

        if (tokenPrice.isSet) {
            // payments in the provided token are accepted

            /*
                Here is how the payment is performced:
                1. (Externally), the user approves a transfer the amount of tokens for this contract
                2. move tokens from buyer to this contract
                3. move tokens from this contract to seller
            */
            IERC20 erc20Token = IERC20(tokenAddr);
            bool isTransferSuccess = erc20Token.transferFrom(
                msg.sender,
                address(this),
                tokenPrice.tokenAmount
            );

            if (isTransferSuccess) {
                // bill has been succesfully paid!
                emit BillPaid(billId, msg.sender, ownerOf(billId), tokenAddr, tokenPrice.tokenAmount);
                // TODO: run post-event function
                // TODO: emit receipt
                return true;
            } else {
                revert("Could not transfer payment.");
            }
        } else {
            revert("Payments in the provided token are not accepted.");
        }

    }
     

}