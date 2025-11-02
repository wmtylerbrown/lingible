# QuizAnswerResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_correct** | **bool** | Whether the answer was correct |
**points_earned** | **float** | Points earned for this question |
**explanation** | **str** | Explanation of the correct answer |
**running_stats** | [**QuizSessionProgress**](QuizSessionProgress.md) |  |

## Example

```python
from lingible_client.models.quiz_answer_response import QuizAnswerResponse

# TODO update the JSON string below
json = "{}"
# create an instance of QuizAnswerResponse from a JSON string
quiz_answer_response_instance = QuizAnswerResponse.from_json(json)
# print the JSON string representation of the object
print(QuizAnswerResponse.to_json())

# convert the object into a dict
quiz_answer_response_dict = quiz_answer_response_instance.to_dict()
# create an instance of QuizAnswerResponse from a dict
quiz_answer_response_from_dict = QuizAnswerResponse.from_dict(quiz_answer_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
