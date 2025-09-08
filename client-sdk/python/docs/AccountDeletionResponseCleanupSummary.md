# AccountDeletionResponseCleanupSummary


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**translations_deleted** | **int** | Number of translation records deleted | [optional]
**data_retention_period** | **str** | How long some data may be retained for legal/operational purposes | [optional]

## Example

```python
from lingible_client.models.account_deletion_response_cleanup_summary import AccountDeletionResponseCleanupSummary

# TODO update the JSON string below
json = "{}"
# create an instance of AccountDeletionResponseCleanupSummary from a JSON string
account_deletion_response_cleanup_summary_instance = AccountDeletionResponseCleanupSummary.from_json(json)
# print the JSON string representation of the object
print(AccountDeletionResponseCleanupSummary.to_json())

# convert the object into a dict
account_deletion_response_cleanup_summary_dict = account_deletion_response_cleanup_summary_instance.to_dict()
# create an instance of AccountDeletionResponseCleanupSummary from a dict
account_deletion_response_cleanup_summary_from_dict = AccountDeletionResponseCleanupSummary.from_dict(account_deletion_response_cleanup_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
