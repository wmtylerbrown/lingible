# ReceiptValidationResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_valid** | **bool** | Whether receipt is valid | [optional] 
**status** | **str** | Validation status | [optional] 
**transaction_id** | **str** | Transaction ID | [optional] 
**product_id** | **str** | Product ID from receipt | [optional] 
**purchase_date** | **datetime** | Purchase date | [optional] 
**expiration_date** | **datetime** | Expiration date | [optional] 
**environment** | **str** | Environment | [optional] 
**error_message** | **str** | Error message if validation failed | [optional] 
**retry_after** | **int** | Seconds to wait before retry | [optional] 

## Example

```python
from lingible_client.models.receipt_validation_response import ReceiptValidationResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ReceiptValidationResponse from a JSON string
receipt_validation_response_instance = ReceiptValidationResponse.from_json(json)
# print the JSON string representation of the object
print(ReceiptValidationResponse.to_json())

# convert the object into a dict
receipt_validation_response_dict = receipt_validation_response_instance.to_dict()
# create an instance of ReceiptValidationResponse from a dict
receipt_validation_response_from_dict = ReceiptValidationResponse.from_dict(receipt_validation_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


