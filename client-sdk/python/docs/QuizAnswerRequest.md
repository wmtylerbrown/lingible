# QuizAnswerRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**session_id** | **str** | Quiz session identifier |
**question_id** | **str** | ID of the question being answered |
**selected_option** | **str** | Selected option ID (a, b, c, d) |
**time_taken_seconds** | **float** | Time taken to answer (in seconds) |

## Example

```python
from lingible_client.models.quiz_answer_request import QuizAnswerRequest

# TODO update the JSON string below
json = "{}"
# create an instance of QuizAnswerRequest from a JSON string
quiz_answer_request_instance = QuizAnswerRequest.from_json(json)
# print the JSON string representation of the object
print(QuizAnswerRequest.to_json())

# convert the object into a dict
quiz_answer_request_dict = quiz_answer_request_instance.to_dict()
# create an instance of QuizAnswerRequest from a dict
quiz_answer_request_from_dict = QuizAnswerRequest.from_dict(quiz_answer_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
