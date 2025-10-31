# QuizQuestionResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**question_id** | **str** | Question ID |
**slang_term** | **str** | The slang term |
**your_answer** | **str** | User&#39;s selected answer |
**correct_answer** | **str** | Correct answer option ID |
**is_correct** | **bool** | Whether the user got it right |
**explanation** | **str** | Full explanation of the term |

## Example

```python
from lingible_client.models.quiz_question_result import QuizQuestionResult

# TODO update the JSON string below
json = "{}"
# create an instance of QuizQuestionResult from a JSON string
quiz_question_result_instance = QuizQuestionResult.from_json(json)
# print the JSON string representation of the object
print(QuizQuestionResult.to_json())

# convert the object into a dict
quiz_question_result_dict = quiz_question_result_instance.to_dict()
# create an instance of QuizQuestionResult from a dict
quiz_question_result_from_dict = QuizQuestionResult.from_dict(quiz_question_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
