# SlangSubmissionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**submission_id** | **str** | Unique submission ID |
**status** | **str** | Current submission status |
**message** | **str** | Success message |
**created_at** | **datetime** | Submission timestamp |

## Example

```python
from lingible_client.models.slang_submission_response import SlangSubmissionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SlangSubmissionResponse from a JSON string
slang_submission_response_instance = SlangSubmissionResponse.from_json(json)
# print the JSON string representation of the object
print(SlangSubmissionResponse.to_json())

# convert the object into a dict
slang_submission_response_dict = slang_submission_response_instance.to_dict()
# create an instance of SlangSubmissionResponse from a dict
slang_submission_response_from_dict = SlangSubmissionResponse.from_dict(slang_submission_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
