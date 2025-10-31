# QuizSubmissionRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**challenge_id** | **str** | ID of the challenge being submitted |
**answers** | [**List[QuizAnswer]**](QuizAnswer.md) | User&#39;s answers |
**time_taken_seconds** | **int** | Time taken to complete the quiz |

## Example

```python
from lingible_client.models.quiz_submission_request import QuizSubmissionRequest

# TODO update the JSON string below
json = "{}"
# create an instance of QuizSubmissionRequest from a JSON string
quiz_submission_request_instance = QuizSubmissionRequest.from_json(json)
# print the JSON string representation of the object
print(QuizSubmissionRequest.to_json())

# convert the object into a dict
quiz_submission_request_dict = quiz_submission_request_instance.to_dict()
# create an instance of QuizSubmissionRequest from a dict
quiz_submission_request_from_dict = QuizSubmissionRequest.from_dict(quiz_submission_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
