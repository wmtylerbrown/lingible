# AccountDeletionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**success** | **bool** | Whether the account deletion was successful | [optional]
**message** | **str** | Confirmation message | [optional]
**deleted_at** | **datetime** | When the account was deleted | [optional]
**cleanup_summary** | [**AccountDeletionResponseCleanupSummary**](AccountDeletionResponseCleanupSummary.md) |  | [optional]

## Example

```python
from lingible_client.models.account_deletion_response import AccountDeletionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AccountDeletionResponse from a JSON string
account_deletion_response_instance = AccountDeletionResponse.from_json(json)
# print the JSON string representation of the object
print(AccountDeletionResponse.to_json())

# convert the object into a dict
account_deletion_response_dict = account_deletion_response_instance.to_dict()
# create an instance of AccountDeletionResponse from a dict
account_deletion_response_from_dict = AccountDeletionResponse.from_dict(account_deletion_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
