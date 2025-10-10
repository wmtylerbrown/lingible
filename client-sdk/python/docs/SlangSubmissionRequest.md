# SlangSubmissionRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**slang_term** | **str** | The slang term to submit |
**meaning** | **str** | What the slang term means |
**example_usage** | **str** | Optional example of how the term is used | [optional]
**context** | **str** | How the submission was initiated | [optional] [default to 'manual']
**translation_id** | **str** | Original translation ID if submitted from a failed translation | [optional]

## Example

```python
from lingible_client.models.slang_submission_request import SlangSubmissionRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SlangSubmissionRequest from a JSON string
slang_submission_request_instance = SlangSubmissionRequest.from_json(json)
# print the JSON string representation of the object
print(SlangSubmissionRequest.to_json())

# convert the object into a dict
slang_submission_request_dict = slang_submission_request_instance.to_dict()
# create an instance of SlangSubmissionRequest from a dict
slang_submission_request_from_dict = SlangSubmissionRequest.from_dict(slang_submission_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
