# QuizQuestionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**session_id** | **str** | Quiz session identifier |
**question** | [**QuizQuestion**](QuizQuestion.md) |  |

## Example

```python
from lingible_client.models.quiz_question_response import QuizQuestionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of QuizQuestionResponse from a JSON string
quiz_question_response_instance = QuizQuestionResponse.from_json(json)
# print the JSON string representation of the object
print(QuizQuestionResponse.to_json())

# convert the object into a dict
quiz_question_response_dict = quiz_question_response_instance.to_dict()
# create an instance of QuizQuestionResponse from a dict
quiz_question_response_from_dict = QuizQuestionResponse.from_dict(quiz_question_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
