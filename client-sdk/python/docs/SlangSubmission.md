# SlangSubmission


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**submission_id** | **str** | Unique submission ID |
**user_id** | **str** | User who submitted the term |
**slang_term** | **str** | The slang term |
**meaning** | **str** | What the term means |
**example_usage** | **str** | Optional example usage | [optional]
**context** | **str** | How the submission was initiated |
**original_translation_id** | **str** | Translation ID if from failed translation | [optional]
**status** | **str** | Overall approval status |
**llm_validation_status** | **str** | LLM validation status |
**llm_confidence_score** | **float** | Confidence score from LLM validation | [optional]
**approval_type** | **str** | Type of approval if approved | [optional]
**upvotes** | **int** | Number of community upvotes |
**created_at** | **datetime** | Submission timestamp |
**reviewed_at** | **datetime** | Review timestamp | [optional]
**reviewed_by** | **str** | Reviewer user ID | [optional]
**approved_by** | **str** | Admin who approved (if manual) | [optional]

## Example

```python
from lingible_client.models.slang_submission import SlangSubmission

# TODO update the JSON string below
json = "{}"
# create an instance of SlangSubmission from a JSON string
slang_submission_instance = SlangSubmission.from_json(json)
# print the JSON string representation of the object
print(SlangSubmission.to_json())

# convert the object into a dict
slang_submission_dict = slang_submission_instance.to_dict()
# create an instance of SlangSubmission from a dict
slang_submission_from_dict = SlangSubmission.from_dict(slang_submission_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
