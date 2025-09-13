# ReceiptValidationResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**isValid** | **Bool** | Whether receipt is valid | [optional]
**status** | **String** | Validation status | [optional]
**transactionId** | **String** | Transaction ID |
**productId** | **String** | Product ID from receipt |
**purchaseDate** | **Date** | Purchase date |
**expirationDate** | **Date** | Expiration date | [optional]
**environment** | **String** | Environment | [optional]
**errorMessage** | **String** | Error message if validation failed | [optional]
**retryAfter** | **Int** | Seconds to wait before retry | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
