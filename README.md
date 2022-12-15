# PayRequestDeFi: Multi-Token Payments With Post-Payment Actions On The Blockchain

A smart-contract payment system which allows for payments in an arbitrary set of tokens, with a
support for fully customizable post-payment actions, statis or dynamic prices, and payment eligibility conditions.

## NOTE

This document and project is a work-in-progress.

## Concepts

* PaymentRequest - represents a request for payment.

## How It Works

A PymentRequest, is an ERC-721 token and, as the name suggests, it represents a request for a payment in exchange for
something. It may be necessary to meet a set of preconditions in order to be able to perform the payment. It is possible
to specify an arbitrary, customizable action to be performed after a successful payment. It is possible to accept a
payment in multiple ERC-20 tokens, and require a different amount for each token. The token prices can either be set in
a static or a dynamic manner. If the static manner is chosen, the token prices are stored in the PaymentRequest itself.
A dynamic price, means the price for a particular token is computed by an arbitrary, customizable smart contract call.


A PaymentRequest can be created with a specification of the following set of parameters:

* ERC-20 Token and Price Pairs \[Required*\] - each PaymentRequest can be paid in several tokens. The price in each one of the tokens
can be distinct. Upon the creation of the PaymentRequest those pairs can be specified. This price association is static
and cannot be changed. It is possible to set dynamic prices with the ERC-20 token Price Computer below.
Either this argument or *ERC-20 Token Price Computer* must be passed.
* ERC-20 Token Price Computer \[Required*\] - address of a smart contract that conforms to the *IPriceComputer* interface.
This allows custom code to compute the price for a particular bill, token and purchaser address. In practice, this
allows for dynamic price specification for PaymentRequest. This price decision can be taken on the basis of the
Payment Request ID, the token, and the purchaser's address. Either this argument or *ERC-20 Token and Price Pairs* is
must be passed.
* Payment Precondition \[Optional\] - address of a smart contract that conforms to the *IPaymentPrecondition* interface. It allows to
specify the condition which must be met for a payment to be processed. This condition can be based upon the 
PaymentRequest address (obtained from the contract caller), PaymentRequest ID, the purchaser's address and the token address.
* Post-Payment Action \[Optional\] - arbitrary action to be performed after a successful payment. The action can be
executed based on the *Receipt* address and ID. From the receipt, the *PaymentRequest* address, *PaymentRequest* ID,
token address, token amount, payer address and payee address can be obtained.

## Design Philosophy and Considerations

This Multi-Token Payment System is designed with Open DeFi in mind. There are no fees associated with its usage, and
forks of it are encouraged. All the dynamic parts are designed to allow for multiple versions of this payment system
to interact with them.


## Pitfalls and Practical Advices

### Ensure That The Callee Address Is This Smart Contract 

When specifying dynamic functions which are preformed though user-specified smart contract callbacks, a check for on
the caller contract will very likely be necessary, ensuring that the callee address is the PymentRequest. This is 
specially important for the Post-Payment Action, otherwise anyone will be able to execute the Post-Payment Action 
without having to perform the payment.

### Checking Which Payment Requests Fail At Which Part

Detailed on-chain information about the progress of a payment can present itself very useful in judging the quality and 
credibility of a `PaymentRequest`. For example, if a particular `PaymentRequest` contains a lot of failures on the
`precondition` step, it is reasonable to assume that either that part is poorly documented by the owner of the
`PaymentRequest`, or it contains faulty code. As such, a `payee` may reconsider their payment.

Events present themselves as good way to offer this feature. There are two ways in which this can be achieved:

1. Emit events on success. By emitting events on success of each step, it is possible to identify at which part the execution failed, by observing a lack of that event.
2. Emit events on failures. This makes it possible to identify exactly at which step the execution of the `pay()` function failed.

A typical way in which option `2` could be achieved is wrapping blocks of code in a `try/catch` statement, and emitting the events inside the `catch`.
However, at the time of the writing, Solidity does not offer a way to re-raise an exception in the `catch` block. Since detailed failure
information of a contract call is of great value, it is desired to preserve it.

As such, `PaymentRequests` adopts option `1`. The following pseudocode can be used to identify the point where the
failure has occurred:

```
Given a failed pay() transaction for a given paymentRequestID:
    
```

## Use Cases

The purpose of this section is to provide a description of how certain features of the payment system can be achieved
with the smart contracts present here.

### Discounted Price For First 100 Customers

Outside of the blockchain, you don't know if retailers are telling the truth: they may lure you to purchase a product
with the pretense of a special price for the first *N* customers, but in reality offer it to *N+M* customers, with
*M>0*.

### NFT Owners Get A Discounted Price


### Regular Customers Get A Discounted Price