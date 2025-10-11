# PendingSubmissionsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**submissions** | [**List[SlangSubmission]**](SlangSubmission.md) | List of pending slang submissions |
**total_count** | **int** | Number of submissions returned |
**has_more** | **bool** | Whether more submissions exist |

## Example

```python
from lingible_client.models.pending_submissions_response import PendingSubmissionsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of PendingSubmissionsResponse from a JSON string
pending_submissions_response_instance = PendingSubmissionsResponse.from_json(json)
# print the JSON string representation of the object
print(PendingSubmissionsResponse.to_json())

# convert the object into a dict
pending_submissions_response_dict = pending_submissions_response_instance.to_dict()
# create an instance of PendingSubmissionsResponse from a dict
pending_submissions_response_from_dict = PendingSubmissionsResponse.from_dict(pending_submissions_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
