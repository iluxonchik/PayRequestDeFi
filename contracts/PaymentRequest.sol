pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "interfaces/IPostPaymentAction.sol";
import "interfaces/IPaymentPrecondition.sol";
import "interfaces/IDynamicTokenAmount.sol";
import "interfaces/IPostPaymentActionWithData.sol";
import "interfaces/IPaymentPreconditionWithData.sol";
import "interfaces/IDynamicTokenAmountWithData.sol";

import "contracts/Receipt.sol";
import "./Receipt.sol";

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

// in the context below, "PaymentRequest" can be in place of ERC-721 and vice-versa.
/// @notice PaymentRequest represents a request for a payment, to be paid by some party.
contract PaymentRequest is ERC721Enumerable {
    // This feature will potentially make its way into Version 2:
    // As a note, an alternative approach where the base contract does not emit any events should be considered. As an alternative, configurable
    // arbitrary code steps could be provided, where the application would control which events it wants to emit. For example, this could include:
    // - onBeforePaymenetRequestCreated()
    // - onAfterPaymentRequestCreated()
    // - onBeforePaymentPreconditionCheck()
    // - onAfterPaymentPreconditionCheck()
    // - onBeforePaymentPostActionCheck()
    // - onAfterPaymentPostActionCheck()
    // In this scenario, each application would only listen to its specific events.
    // All of these functions would be provided as a pointer to an address of a contract that implements the interface that contains all of those methods.
    // This way, a particular coffee shop on top of a PaymentRequest could define its own rules, which are very business specific to it.

    event PaymentRequestCreated(
        uint256 indexed paymentRequestId,
        address creator,
        address from,
        bool isStatic
    );

    event PaymentPreconditionPassed(
        uint256 indexed paymentRequestId,
        address token,
        address payer
    );

    event TokenAmountObtained(
        uint256 indexed PaymentRequestId,
        address token,
        uint256 amount,
        address payer,
        bool isStatic
    );

    event PostPaymentActionExecuted(
        uint256 indexed paymentRequestId,
        address action,
        uint256 receiptId
    );

    event PaymentRequestPaid(
        uint256 indexed paymentRequestId,
        uint256 receiptId,
        address token,
        uint256 amuont,
        address payer,
        address payee
    );

    
    event PaymentRequestEnabled(uint256 indexed paymentRequestId);
    event PaymentRequestDisabled(uint256 indexed paymentRequestId);

    using Counters for Counters.Counter;
    Counters.Counter private _tokenId;
    Receipt public receipt;

    // map of Payment Request ERC-721 to its amounts
    mapping(uint256 => mapping(address => TokenAmountMappingValue)) internal tokenIdToAmountMap;
    mapping(uint256 => TokenAmountInfo[]) internal tokenIdToAmountArray;
    mapping(uint256 => address[]) internal tokenIdToAcceptedStaticTokens;
    mapping(uint256 => address) internal tokenIdToPostPaymentAction;
    mapping(uint256 => address) internal tokenIdToPaymentPrecondition;
    mapping(uint256 => address) internal tokenIdToDynamicTokenAmount;
    mapping(uint256 => bool) internal tokenIdToEnabled;
    // If set, the Payment Request is a request for payment for a specific address, i.e. the payment is requested
    // from a specific address.
    mapping(uint256 => address) internal tokenIdToFrom;

    constructor(
        string memory name,
        string memory symbol,
        address customReceipt
    ) ERC721(name, symbol) {
        // you can either utilize an existing Receipt contract or deploy your own
        if (customReceipt == address(0)) {
            // no custom receipt address provided, deploy one
            string memory receiptName = string.concat(name, " Receipt");
            string memory receiptSymbol = string.concat(symbol, "RCT");
            receipt = new Receipt(receiptName, receiptSymbol);
        } else {
            // custom receipt address provided
            receipt = Receipt(customReceipt);
        }
    }

    // Static/Dynamic Token Amount Distinction
    function isTokenAmountStatic(uint256 paymentRequestId) public view returns(bool) {
        return tokenIdToDynamicTokenAmount[paymentRequestId] == address(0);
    }

    function isTokenAmountDynamic(uint256 paymentRequestId) public view returns(bool) {
        return tokenIdToDynamicTokenAmount[paymentRequestId] != address(0);
    }

    function isPaymentPreconditionSet(uint256 paymentRequestId) public view returns(bool) {
        return tokenIdToPaymentPrecondition[paymentRequestId] != address(0);
    }

    function isPaymentPostActionSet(uint256 paymentRequestId) public view returns(bool) {
        return tokenIdToPostPaymentAction[paymentRequestId]  != address(0);
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

    // Static TokenAmountInfo Getetrs
    function getStaticTokenAmountInfos(uint256 paymentRequestId) public view returns (TokenAmountInfo[] memory) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAmountArray[paymentRequestId];
    }

    function getStaticTokenAmountInfoByIndex(uint256 paymentRequestId, uint256 index) public view returns (TokenAmountInfo memory) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAmountArray[paymentRequestId][index];
    }

    // Static uint256 Amount Getters
    function getStaticTokenAmountByIndex(uint256 paymentRequestId, uint256 index) public view returns (uint256) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        return tokenIdToAmountArray[paymentRequestId][index].tokenAmount;
    }

    function getStaticAmountForToken(uint256 paymentRequestId, address token) public view returns (uint256) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");

        TokenAmountMappingValue memory tokenAmount = tokenIdToAmountMap[paymentRequestId][token];
        
        require(tokenAmount.isSet, "Payments in the provided token are not accepted.");
        
        return tokenAmount.tokenAmount;
    }

    function isDynamicTokenAccepted(uint256 paymentRequestId, address token) public returns (bool) {
        require(isTokenAmountDynamic(paymentRequestId), "Amount of the provided PaymentRequest ID is not dynamic.");
        address dynamicTokenAmountAddr = tokenIdToDynamicTokenAmount[paymentRequestId];
        IDynamicTokenAmount dynamicTokenAmount = IDynamicTokenAmount(dynamicTokenAmountAddr);
        return dynamicTokenAmount.isTokenAccepted(
            {
                paymentRequestId: paymentRequestId,
                token: token,
                payer: msg.sender
            });
    }

    function isStaticTokenAccepted(uint256 paymentRequestId, address token) public view returns (bool) {
        require(isTokenAmountStatic(paymentRequestId), "Amount of the provided PaymentRequest ID is not static.");
        TokenAmountMappingValue memory tokenAmount = tokenIdToAmountMap[paymentRequestId][token];
        return tokenAmount.isSet;
    }

    // Address Of Custom Action Getters
    function getPostPaymentAction(uint256 paymentRequestId) public view returns (address) {
        return tokenIdToPostPaymentAction[paymentRequestId];
    }

    function getPaymentPrecondition(uint256 paymentRequestId) public view returns (address) {
        return tokenIdToPaymentPrecondition[paymentRequestId];
    }

    function getDynamicTokenAmount(uint256 paymentRequestId) public view returns (address) {
        return tokenIdToDynamicTokenAmount[paymentRequestId];
    }

    // PaymentRequest From Getters

    /// @notice Get the price when a dynamic pricing scheme is in use. This is the only method available in this
    /// contract to query for the dynamic price of a token. Since its logic is arbitrary, other methods may be
    /// infeasible to implement. An example of that would be an IDynamicTokenAmountInfo that accepts any token converted
    /// to a stablecoin such as USDT. Operations like listing all of the accepted token IDs becomes impractical
    function getDynamicAmountForToken(uint256 paymentRequestId, address token) public returns (uint256) {
        require(isTokenAmountDynamic(paymentRequestId), "Amount of the provided PaymentRequest ID is not dynamic.");
        address dynamicTokenAmountAddr = tokenIdToDynamicTokenAmount[paymentRequestId];
        IDynamicTokenAmount dynamicTokenAmount = IDynamicTokenAmount(dynamicTokenAmountAddr);
        return dynamicTokenAmount.getAmountForToken(
                paymentRequestId,
                token,
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
        TokenAmountInfo[] memory prices
    ) internal {
        require(prices.length > 0, "Product prices cannot be empty.");

        for (uint256 i = 0; i < prices.length; i++) {
            TokenAmountInfo memory price = prices[i];
            require(!tokenIdToAmountMap[tokenId][price.token].isSet, "Multiple token amounts for the same token provided.");
            tokenIdToAmountMap[tokenId][price.token] = TokenAmountMappingValue({
                    tokenAmount: price.tokenAmount,
                    isSet: true
                });
            tokenIdToAmountArray[tokenId].push(price);
            tokenIdToAcceptedStaticTokens[tokenId].push(price.token);
        }
    }

    function _createCommonBase(address owner, address paymentPrecondition, address postPaymentAction)
        internal
        returns (uint256)
    {
        uint256 tokenId = _tokenId.current();
        // the payments will be done to the owner of the ERC720
        _mint(owner, tokenId);

        tokenIdToPostPaymentAction[tokenId] = postPaymentAction;
        tokenIdToEnabled[tokenId] = true;
        tokenIdToPaymentPrecondition[tokenId] = paymentPrecondition;

        _tokenId.increment();
        return tokenId;
    }

    /* == END auxiliary procedures for creating the PaymentReqeust == */


    /* == BEGIN auxiliary functions for performing a payment == */

    /// @notice Returns the TokenAmountMappingValue for a given bill and token pair. Practically, this allows
    /// you to obtain price in tokens for a given contract address, or identify that the provided bill ID
    /// does not accept payments in the provided token ID. You should always check the isSet variable of the
    /// returned struct: if it false, the payments in the provided token are not defined.
    /// Both parts done in a single function to be more gas efficient.
    function getAmountForToken(
        uint256 paymentRequestId,
        address token
    ) public returns (uint256) {
        bool isStatic = isTokenAmountStatic(paymentRequestId);
        uint256 amount = isStatic ? getStaticAmountForToken(paymentRequestId, token) : getDynamicAmountForToken(paymentRequestId, token);
        emit TokenAmountObtained(paymentRequestId, token, amount, msg.sender, isStatic);
        return amount;
    }

    function isTokenAccepted(uint256 paymentRequestId, address token) public returns (bool) {
        return isTokenAmountStatic(paymentRequestId) ? isStaticTokenAccepted(paymentRequestId, token) : isDynamicTokenAccepted(paymentRequestId, token);
    }

    function _checkPaymentPrecondition(
        uint256 paymentRequestId,
        address token
    ) internal {
        // Check if pre-conditions for payment are met. For example, perhaps you only want to allow this product
        // to be purchasable by addresses who own a particular NFT, or perhaps owners of a particular NFT are allowed
        // to pay in a particular token.
        address paymentPreconditionAddr = tokenIdToPaymentPrecondition[
            paymentRequestId
        ];
        if (paymentPreconditionAddr != address(0)) {
            IPaymentPrecondition paymentPrecondition = IPaymentPrecondition(
                paymentPreconditionAddr
            );
            bool isPaymentAllowed = paymentPrecondition
                .isPaymentAllowed(
                    paymentRequestId,
                    token,
                    msg.sender
                );
            
            require(isPaymentAllowed, "Payment precondition not met");
                
            emit PaymentPreconditionPassed(
                paymentRequestId,
                token,
                msg.sender            );
            
        }
    }

    function _performTokenTransfer(
        uint256 paymentRequestId,
        address token,
        uint256 tokenAmount
    ) internal {
        // immune to attack described in https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729,
        // since the approval and the transfer are done one after another.

        /*
            Here is how the payment is performced:
            1. (Externally), the user approves a transfer the amount of tokens for this contract-
                Note: recommended to use increaseAllowance()
            2. move tokens from buyer to this contract
            3. move tokens from this contract to seller
        */

        IERC20 erc20Token = IERC20(token);

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
        address token,
        uint256 tokenAmount
    ) internal returns (uint256) {
        return receipt.create(
            {
                paymentRequestId: paymentRequestId,
                token: token,
                tokenAmount: tokenAmount,
                payer: msg.sender,
                payee: ownerOf(paymentRequestId)
            });
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

    function createWithStaticTokenAmount(
        TokenAmountInfo[] memory prices,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        uint256 tokenId = _createCommonBase(msg.sender, paymentPrecondition, postPaymentAction);

        // map token prices into internal data structure
        _storeTokenAmountsInInternalStructures(tokenId, prices);

        return tokenId;
    }

    function createWithDynamicTokenAmount(
        address dynamicTokenAmount,
        address paymentPrecondition,
        address postPaymentAction
    ) public returns (uint256) {
        uint256 tokenId = _createCommonBase(msg.sender, paymentPrecondition, postPaymentAction);

        // map token prices into internal data structure
        tokenIdToDynamicTokenAmount[tokenId] = dynamicTokenAmount;

        return tokenId;
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
        emit PaymentRequestEnabled(paymentRequestId);
    }

    function disable(uint256 paymentRequestId) public {
        require(
            msg.sender == ownerOf(paymentRequestId),
            "Only owner can disable a PaymentRequest"
        );
        if (isEnabled(paymentRequestId)) {
            tokenIdToEnabled[paymentRequestId] = false;
            emit PaymentRequestDisabled(paymentRequestId);
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
    
    function payA(uint256 paymentRequestId, address token, address data, uint256 dataId) external paymentRequestIsEnabled(paymentRequestId) returns (uint256) {
        // TODO: include arbitrary data with payment Request.
        return 0;
    }

    function pay(uint256 paymentRequestId, address token)
        external
        paymentRequestIsEnabled(paymentRequestId)
        returns (uint256)
    {

        _checkPaymentPrecondition(paymentRequestId, token);

        uint256 tokenAmount = getAmountForToken(
            paymentRequestId,
            token
        );

        _performTokenTransfer(
            paymentRequestId,
            token,
            tokenAmount
        );


        // PaymentReqeust has been successfully paid, emit receipt
        uint256 receiptId = _emitReceipt(
            {
                paymentRequestId: paymentRequestId,
                token: token,
                tokenAmount: tokenAmount
            }
        );
        _executePostPaymentAction(paymentRequestId, receiptId);

        emit PaymentRequestPaid(paymentRequestId, receiptId, token, tokenAmount, msg.sender, ownerOf(paymentRequestId));

        return receiptId;
    }
}
