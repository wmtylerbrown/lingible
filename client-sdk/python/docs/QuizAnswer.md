# QuizAnswer


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**question_id** | **str** | ID of the question being answered |
**selected** | **str** | Selected option ID (a, b, c, d) |

## Example

```python
from lingible_client.models.quiz_answer import QuizAnswer

# TODO update the JSON string below
json = "{}"
# create an instance of QuizAnswer from a JSON string
quiz_answer_instance = QuizAnswer.from_json(json)
# print the JSON string representation of the object
print(QuizAnswer.to_json())

# convert the object into a dict
quiz_answer_dict = quiz_answer_instance.to_dict()
# create an instance of QuizAnswer from a dict
quiz_answer_from_dict = QuizAnswer.from_dict(quiz_answer_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
