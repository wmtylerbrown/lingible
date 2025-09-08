# AccountDeletionRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**confirmation_text** | **str** | User must type \&quot;DELETE\&quot; to confirm account deletion |
**reason** | **str** | Optional reason for account deletion | [optional]

## Example

```python
from lingible_client.models.account_deletion_request import AccountDeletionRequest

# TODO update the JSON string below
json = "{}"
# create an instance of AccountDeletionRequest from a JSON string
account_deletion_request_instance = AccountDeletionRequest.from_json(json)
# print the JSON string representation of the object
print(AccountDeletionRequest.to_json())

# convert the object into a dict
account_deletion_request_dict = account_deletion_request_instance.to_dict()
# create an instance of AccountDeletionRequest from a dict
account_deletion_request_from_dict = AccountDeletionRequest.from_dict(account_deletion_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
