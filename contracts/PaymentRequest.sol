pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "interfaces/IERC20.sol";
import "interfaces/IPostPaymentAction.sol";
import "interfaces/IPaymentPrecondition.sol";
import "interfaces/ITokenAmountComputer.sol";

import {Payment} from "./libraries/Payment.sol";
import "contracts/Receipt.sol";

// in the context below, "PaymentRequest" can be in place of ERC-721 and vice-versa.
/// @notice PaymentRequest represents a request for a payment, to be paid by some party.
contract PaymentRequest is ERC721Enumerable {

    event PaymentPreconditionPassed(
        uint256 paymentRequestId,
        address payer,
        address token
    );

    event TokenAmountObtained(
        uint256 PaymentRequestId,
        address payer,
        address token,
        uint256 amount,
        bool isStatic
    );

    event PostPaymentActionExecuted(
        uint256 paymentRequestId,
        address action,
        uint256 receiptId
    );

    event PaymentRequestPaid(
        uint256 paymentRequestId,
        uint256 receiptId,
        address payer,
        address payee,
        address token,
        uint256 amuont
    );

    
    
    
    event PaymentRequestEnabled(uint256 paymentRequestId, address enabledBy);
    event PaymentRequestDisabled(uint256 paymentRequestId, address disabledBy);

    using Counters for Counters.Counter;
    Counters.Counter private _tokenId;
    Receipt public receipt;

    // map of Payment Request ERC-721 to its amounts
    mapping(uint256 => mapping(address => Payment.TokenAmountMappingValue)) internal tokenIdToAmountMap;
    mapping(uint256 => Payment.TokenAmountInfo[]) internal tokenIdToAmountArray;
    mapping(uint256 => address[]) internal tokenIdToAcceptedStaticTokens;
    // TODO: make below internal and offer getters
    mapping(uint256 => address) public tokenIdToPostPaymentAction;
    mapping(uint256 => address) public tokenIdToPaymentPrecondition;
    mapping(uint256 => address) public tokenIdToAmountComputer;
    mapping(uint256 => bool) internal tokenIdToEnabled;

    constructor(
        string memory name,
        string memory symbol,
        address receiptAddr
    ) ERC721(name, symbol) {
        // you can either utilize an existing Receipt contract or deploy your own one
        receipt = Receipt(receiptAddr);
    }

    // Static/Dynamic Token Amount Distinction
    function isTokenAmountStatic(uint256 paymentRequestId) public view returns(bool) {
        return tokenIdToAmountComputer[paymentRequestId] == address(0);
    }

    function isTokenAmountDynamic(uint256 paymentRequestId) public view returns(bool) {
        return tokenIdToAmountComputer[paymentRequestId] != address(0);
    }

    // Static Token Count
    function getNumberOfStaticTokens(uint256 paymentRequestId) public view returns (uint256) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAcceptedStaticTokens[paymentRequestId].length;
    }

    // Static Token Address Getters
    function getStaticTokens(uint256 paymentRequestId) public view returns (address[] memory) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAcceptedStaticTokens[paymentRequestId];
    }

    function getStaticTokenByIndex(uint256 paymentRequestId, uint256 index) public view returns (address) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAcceptedStaticTokens[paymentRequestId][index];
    }

    // Static Payment.TokenAmountInfo Gettrs
    function getStaticTokenAmountInfos(uint256 paymentRequestId) public view returns (Payment.TokenAmountInfo[] memory) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAmountArray[paymentRequestId];
    }

    function getStaticTokenAmountInfoByIndex(uint256 paymentRequestId, uint256 index) public view returns (Payment.TokenAmountInfo memory) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAmountArray[paymentRequestId][index];
    }

    // Static uint256 Amount Getters
    function getStaticTokenAmountByIndex(uint256 paymentRequestId, uint256 index) public view returns (uint256) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAmountArray[paymentRequestId][index].tokenAmount;
    }

    function getStaticTokenAmount(uint256 paymentRequestId, address tokenAddr) public view returns (uint256) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");

        Payment.TokenAmountMappingValue memory tokenAmount = tokenIdToAmountMap[paymentRequestId][tokenAddr];
        
        require(tokenAmount.isSet, "Payments in the provided token are not accepted.");
        
        return tokenAmount.tokenAmount;
    }

    /// @notice Get the price when a dynamic pricing scheme is in use. This is the only method available in this
    /// contract to query for the dynamic price of a token. Since its logic is arbitrary, other methods may be
    /// infeasible to implement. An example of that would be an IAmountComputer that accepts any token converted
    /// to a stablecoin such as USDT. Operations like listing all of the accepted token IDs becomes impractical
    function getDynamicTokenAmount(uint256 paymentRequestId, address tokenAddr) public returns (uint256) {
        require(isTokenAmountDynamic(paymentRequestId), "Amount of the provided PaymentRequest ID is not dynamic.");
        address priceComputerAddr = tokenIdToAmountComputer[paymentRequestId];
        ITokenAmountComputer priceComputer = ITokenAmountComputer(priceComputerAddr);
        return priceComputer.getAmountForToken(
                paymentRequestId,
                tokenAddr,
                msg.sender
            );
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
    function _storeTokenAmountsInInternalStructures(
        uint256 tokenId,
        Payment.TokenAmountInfo[] memory prices
    ) internal {
        require(prices.length > 0, "Product prices cannot be empty.");

        for (uint256 i = 0; i < prices.length; i++) {
            Payment.TokenAmountInfo memory price = prices[i];
            tokenIdToAmountMap[tokenId][price.tokenAddr] = Payment
                .TokenAmountMappingValue({
                    tokenAmount: price.tokenAmount,
                    isSet: true
                });
            tokenIdToAmountArray[tokenId].push(price);
            tokenIdToAcceptedStaticTokens[tokenId].push(price.tokenAddr);
        }
    }

    function _createCommonBase(address payTo, address paymentPrecondition, address postPaymentAction)
        internal
        returns (uint256)
    {
        uint256 tokenId = _tokenId.current();
        // the payments will be done to the owner of the ERC720. the "lending" of payTo should be done via another SC
        _mint(payTo, tokenId);

        tokenIdToPostPaymentAction[tokenId] = postPaymentAction;
        tokenIdToEnabled[tokenId] = true;
        tokenIdToPaymentPrecondition[tokenId] = paymentPrecondition;

        _tokenId.increment();
        return tokenId;
    }

    /* == END auxiliary procedures for creating the PaymentReqeust == */


    /* == BEGIN auxiliary functions for performing a payment == */

    /// @notice Retuns the TokenAmountMappingValue for a given bill and token pair. Practically, this allows
    /// you to obtain price in tokens for a given contract address, or identify that the provided bill ID
    /// does not accept payments in the provided token ID. You should always check the isSet variable of the
    /// reutned struct: if it false, the payments in the provided token are not defined.
    /// Both parts done in a single function to be more gas efficient.
    function getTokenAmount(
        uint256 paymentRequestId,
        address tokenAddr
    ) public returns (uint256) {
        bool isPaymentStatic = true;
        uint256 price = isTokenAmountStatic(paymentRequestId) ? getStaticTokenAmount(paymentRequestId, tokenAddr) : getDynamicTokenAmount(paymentRequestId, tokenAddr);
        emit TokenAmountObtained(paymentRequestId, tokenAddr, msg.sender, price, isPaymentStatic);
        return price;
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
            
            require(isPaymentPreconditionMet, "Payment precondition not met");
                
            emit PaymentPreconditionPassed(
                paymentRequestId,
                msg.sender,
                tokenAddr);
            
        }
    }

    function _performTokenTransfer(
        uint256 paymentRequestId,
        address tokenAddr,
        uint256 tokenAmount
    ) internal {
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

        bool isTransferSuccess = erc20Token.transfer(
                ownerOf(paymentRequestId),
                tokenAmount
            );
        // No events emitted by this contract. Observe the Transfer event of ERC-20

        require(isTransferSuccess, "Could not transfer tokens.");
    }

    function _emitReceipt(
        uint256 paymentRequestId,
        address tokenAddr,
        uint256 tokenAmount
    ) internal returns (uint256) {
        return receipt.create(
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
        // run post-payment action, if set
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

    function createWithStaticTokenAmountFor(
        Payment.TokenAmountInfo[] memory prices,
        address payTo,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        uint256 tokenId = _createCommonBase(payTo, paymentPrecondition, postPaymentAction);

        // map token prices into internal data structure
        _storeTokenAmountsInInternalStructures(tokenId, prices);

        return tokenId;
    }

    function createWithDynamicTokenAmountFor(
        address priceComputer,
        address payTo,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        uint256 tokenId = _createCommonBase(payTo, paymentPrecondition, postPaymentAction);

        // map token prices into internal data structure
        tokenIdToAmountComputer[tokenId] = priceComputer;

        return tokenId;
    }

    function createWithStaticTokenAmount(
        Payment.TokenAmountInfo[] memory prices,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        return createWithStaticTokenAmountFor(prices, msg.sender, paymentPrecondition, postPaymentAction);
    }

    function createWithDynamicTokenAmount(
        address priceComputer,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        return createWithDynamicTokenAmountFor(priceComputer, msg.sender, paymentPrecondition, postPaymentAction);
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
        returns (uint256)
    {
        _checkPaymentPrecondition(paymentRequestId, tokenAddr);

        uint256 tokenAmount = getTokenAmount(
            paymentRequestId,
            tokenAddr
        );

        _performTokenTransfer(
            paymentRequestId,
            tokenAddr,
            tokenAmount
        );


        // PaymentReqeust has been successfully paid, emit receipt
        uint256 receiptId = _emitReceipt(
            paymentRequestId,
            tokenAddr,
            tokenAmount
        );
        _executePostPaymentAction(paymentRequestId, receiptId);

        emit PaymentRequestPaid(paymentRequestId, receiptId, msg.sender, ownerOf(paymentRequestId), tokenAddr, tokenAmount);
        return receiptId;
    }
}
