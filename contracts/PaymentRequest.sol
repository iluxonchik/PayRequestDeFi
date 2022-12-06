pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "interfaces/IERC20.sol";
import "interfaces/IPostPaymentAction.sol";
import "interfaces/IPaymentPrecondition.sol";
import "interfaces/IPriceComputer.sol";

import {Payment} from "./libraries/Payment.sol";
import "contracts/Receipt.sol";

// in the context below, "PaymentRequest" can be in place of ERC-721 and vice-versa.
/// @notice PaymentRequest represents a request for a bill, to be paid by some party.
contract PaymentRequest is ERC721 {
    event BillPaid(
        uint256 billId,
        address buyer,
        address seller,
        address token,
        uint256 amount
    );
    event PostPaymentActionExecuted(
        uint256 billId,
        address action,
        address receipt,
        uint256 receiptId
    );
    event PaymentPreconditionRejected(
        uint256 billId,
        address payer,
        address token
    );
    event PaymentRequestEnabled(uint256 paymentRequestId, address enabledBy);
    event PaymentRequestDisabled(uint256 paymentRequestId, address disabledBy);

    using Counters for Counters.Counter;
    Counters.Counter private _tokenId;
    Receipt public receipt;

    mapping(address => uint256[]) public tokenIdsCreatedByAddr;

    // map of Payment Request ERC-721 to its prices
    mapping(uint256 => mapping(address => Payment.TokenPriceMappingValue))
        public tokenIdToPriceMap;
    mapping(uint256 => Payment.TokenPrice[]) public tokenIdToPriceArray;
    mapping(uint256 => address) public tokenIdToPostPaymentAction;
    mapping(uint256 => address) public tokenIdToPaymentPrecondition;
    mapping(uint256 => address) public tokenIdToPriceComputer;
    mapping(uint256 => bool) public tokenIdToEnabled;

    constructor(
        string memory name,
        string memory symbol,
        address receiptAddr
    ) ERC721(name, symbol) {
        // you can either utilize an existing Receipt contract or deploy your own one
        receipt = Receipt(receiptAddr);
    }

        /* == BEGIN auxiliary procedures for creating the PaymentReqeust == */

    /// @notice Stores the provided Payment request prices in the internal storage of the contract
    /// There is is large risk in storing and enabling calls to unverified token addresses, as you do not know
    /// what the smart contracts at those addresses do. For example, they may be calling approve on a completely
    /// different set of tokens. Thouhg should be put into wether the whitelisting of addresses should be done
    /// by this smart contract or an outside one. One idea is to use the number of interactions with a smart
    /// contract as an initial measure of trust. For example, if the number of interactions with a smart contract
    /// is below 1000, then rquire an additional explicit confirmation. However, such as sytem is outside of the
    /// scope of the initial version of this module.
    function _storePricesInInternalStructures(
        uint256 tokenId,
        Payment.TokenPrice[] memory prices
    ) internal {
        if (prices.length == 0) {
            revert("Product prices cannot be empty.");
        }

        for (uint256 i = 0; i < prices.length; i++) {
            Payment.TokenPrice memory price = prices[i];
            tokenIdToPriceMap[tokenId][price.tokenAddr] = Payment
                .TokenPriceMappingValue({
                    tokenAmount: price.tokenAmount,
                    isSet: true
                });
            tokenIdToPriceArray[tokenId].push(price);
        }
    }

    function _createCommonBase(address payTo, address paymentPrecondition, address postPaymentAction)
        internal
        returns (uint256)
    {
        uint256 tokenId = _tokenId.current();
        // the payments will be done to the owner of the ERC720. the "lending" of payTo should be done via another SC
        _mint(payTo, tokenId);

        tokenIdsCreatedByAddr[msg.sender].push(tokenId);
        tokenIdToPostPaymentAction[tokenId] = postPaymentAction;
        tokenIdToEnabled[tokenId] = true;
        tokenIdToPaymentPrecondition[tokenId] = paymentPrecondition;

        _tokenId.increment();
        return tokenId;
    }

    /* == END auxiliary procedures for creating the PaymentReqeust == */


    /* == BEGIN auxiliary functions for performing a payment == */

    /// @notice Retuns the TokenPriceMappingValue for a given bill and token pair. Practically, this allows
    /// you to obtain price in tokens for a given contract address, or identify that the provided bill ID
    /// does not accept payments in the provided token ID. You should always check the isSet variable of the
    /// reutned struct: if it false, the payments in the provided token are not defined.
    /// Both parts done in a single function to be more gas efficient.
    function getPriceForTokenId(
        uint256 paymentRequestId,
        address tokenAddr,
        address payer
    ) public returns (uint256) {
        address priceComputerAddr = tokenIdToPriceComputer[paymentRequestId];
        if (priceComputerAddr == address(0)) {
            Payment.TokenPriceMappingValue
                memory tokenPriceMapping = tokenIdToPriceMap[paymentRequestId][
                    tokenAddr
                ];
            if (tokenPriceMapping.isSet) {
                return tokenPriceMapping.tokenAmount;
            } else {
                revert("Payments in the provided token are not accepted.");
            }
        } else {
            IPriceComputer priceComputer = IPriceComputer(priceComputerAddr);
            return
                priceComputer.getPriceForToken(
                    paymentRequestId,
                    tokenAddr,
                    payer
                );
        }
    }

    function _checkPaymentPrecondition(
        uint256 paymentRequestId,
        address tokenAddr
    ) internal {
        // Check if pre-conditions for payment are met. For example, perhaps you only want to allow this product
        // to be purchaseable by addresses who own a particular NFT, or perhaps owners of a particular NFT are allowed
        // to pay in a particular token.
        address paymentPreconditionAddr = tokenIdToPaymentPrecondition[
            paymentRequestId
        ];
        if (paymentPreconditionAddr != address(0)) {
            IPaymentPrecondition paymentPrecondition = IPaymentPrecondition(
                paymentPreconditionAddr
            );
            bool isPaymentPreconditionMet = paymentPrecondition
                .isPaymentPreconditionMet(
                    paymentRequestId,
                    msg.sender,
                    tokenAddr
                );
            if (!isPaymentPreconditionMet) {
                // rejections may be interesting to track per paymentRequestId. badly formed or documented bills are more likely
                // to have a high number of rejections.
                emit PaymentPreconditionRejected(
                    paymentRequestId,
                    msg.sender,
                    tokenAddr
                );
                revert("Payment precondition not met");
            }
        }
    }

    function _performTokenTransfer(
        uint256 paymentRequestId,
        address tokenAddr,
        uint256 tokenAmount
    ) internal returns (bool) {
        // immune to attack described in https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729,
        // since the approval and the transfer are done one after another.

        /*
            Here is how the payment is performced:
            1. (Externally), the user approves a transfer the amount of tokens for this contract
            2. move tokens from buyer to this contract
            3. move tokens from this contract to seller
        */

        IERC20 erc20Token = IERC20(tokenAddr);

        bool isIntermediaryTransferSuccess = erc20Token.transferFrom(
            msg.sender,
            address(this),
            tokenAmount
        );

        require(
            isIntermediaryTransferSuccess,
            "Could not transfer payment. Was it approved?"
        );

        return
            erc20Token.transferFrom(
                address(this),
                ownerOf(paymentRequestId),
                tokenAmount
            );
    }

    function _emitReceipt(
        uint256 paymentRequestId,
        address tokenAddr,
        uint256 tokenAmount
    ) internal returns (uint256) {
        emit BillPaid(
            paymentRequestId,
            msg.sender,
            ownerOf(paymentRequestId),
            tokenAddr,
            tokenAmount
        );
        return
            receipt.create(
                paymentRequestId,
                tokenAddr,
                tokenAmount,
                msg.sender,
                ownerOf(paymentRequestId)
            );
    }

    function _executePostPaymentAction(
        uint256 paymentRequestId,
        uint256 receiptId
    ) internal {
        // run post-payment function, if set
        address postPaymentActionAddr = tokenIdToPostPaymentAction[
            paymentRequestId
        ];
        if (postPaymentActionAddr != address(0)) {
            IPostPaymentAction postPaymentAction = IPostPaymentAction(
                postPaymentActionAddr
            );
            postPaymentAction.onPostPayment(address(receipt), receiptId);
            emit PostPaymentActionExecuted(
                paymentRequestId,
                postPaymentActionAddr,
                address(receipt),
                receiptId
            );
        }
    }

    modifier paymentRequestIsEnabled(uint256 paymentRequestId) {
        require(
            isEnabled(paymentRequestId),
            "PaymentRequest is disabled"
        );
        _;
    }

    /* == END auxiliary functions for performing a payment == */


    /* == BEGIN PaymentRequest creation procedures == */

    // Limiting to only the strictly necessary creators semantically is an intentional decision. Any constructing
    // utilities, such as the numerous create overload possibilities should be deployed as a part of a separate contract.
    // The payTo option allows for a proxied creation of PaymentRequests. In such an approach, this payment system this
    // an L1 and its goal is to offer core functionality. Any additional one should be developed as a part of
    // distinct contracts, which would be acting akin to an L2 for this L1.

    // In my vision, there are two variables in the semantics:
    // * static or dynamic price definition - results in the prices and priceComputer parameters
    // * proxied or non-proxied creation - results in the presence or absence of the payTo parameter

    // Initially I started with overloading, but practical deliberation revealed that more explicit constructors
    // are better, as they are also self-documenting.

    function createWithStaticPriceFor(
        Payment.TokenPrice[] memory prices,
        address payTo,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        uint256 tokenId = _createCommonBase(payTo, paymentPrecondition, postPaymentAction);

        // map token prices into internal data structure
        _storePricesInInternalStructures(tokenId, prices);

        return tokenId;
    }

    function createWithDynamicPriceFor(
        address priceComputer,
        address payTo,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        uint256 tokenId = _createCommonBase(payTo, paymentPrecondition, postPaymentAction);

        // map token prices into internal data structure
        tokenIdToPriceComputer[tokenId] = priceComputer;

        return tokenId;
    }

    function createWithStaticPrice(
        Payment.TokenPrice[] memory prices,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        return createWithStaticPriceFor(prices, msg.sender, paymentPrecondition, postPaymentAction);
    }

    function createWithDynamicPrice(
        address priceComputer,
        address payTo,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        return createWithDynamicPriceFor(priceComputer, msg.sender, paymentPrecondition, postPaymentAction);
    }

    /* == END PaymentRequest creation procedures == */

    /* == BEGIN PaymentRequest mutators == */
    function enable(uint256 paymentRequestId) public {
        require(
            msg.sender == ownerOf(paymentRequestId),
            "Only owner can enable a PaymentRequest"
        );
        if (isEnabled(paymentRequestId)) {
            return;
        }
        tokenIdToEnabled[paymentRequestId] = true;
        emit PaymentRequestEnabled(paymentRequestId, msg.sender);
    }

    function disable(uint256 paymentRequestId) public {
        require(
            msg.sender == ownerOf(paymentRequestId),
            "Only owner can disable a PaymentRequest"
        );
        if (isEnabled(paymentRequestId)) {
            tokenIdToEnabled[paymentRequestId] = false;
            emit PaymentRequestDisabled(paymentRequestId, msg.sender);
        }

    }

    /* == END PaymentRequest mutators == */

    /* == BEGIN PaymentRequest state readers == */

    function isEnabled(uint256 paymentRequestId)
        public
        view
        returns (bool)
    {
        return tokenIdToEnabled[paymentRequestId];
    }

    /* == END PaymentRequest state readers == */

    function pay(uint256 paymentRequestId, address tokenAddr)
        external
        paymentRequestIsEnabled(paymentRequestId)
        returns (bool)
    {
        _checkPaymentPrecondition(paymentRequestId, tokenAddr);

        uint256 tokenAmount = getPriceForTokenId(
            paymentRequestId,
            tokenAddr,
            msg.sender
        );

        bool isTransferSuccess = _performTokenTransfer(
            paymentRequestId,
            tokenAddr,
            tokenAmount
        );

        require(isTransferSuccess, "Could not transfer payment.");

        // PaymentReqeust has been succesfully paid, emit receipt
        uint256 receiptId = _emitReceipt(
            paymentRequestId,
            tokenAddr,
            tokenAmount
        );
        _executePostPaymentAction(paymentRequestId, receiptId);

        return true;
    }
}
