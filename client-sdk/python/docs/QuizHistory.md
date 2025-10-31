# QuizHistory


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**user_id** | **str** | User ID |
**total_quizzes** | **int** | Total quizzes taken |
**average_score** | **float** | Average score across all quizzes |
**best_score** | **int** | Best score achieved |
**total_correct** | **int** | Total correct answers |
**total_questions** | **int** | Total questions answered |
**accuracy_rate** | **float** | Overall accuracy percentage |
**quizzes_today** | **int** | Number of quizzes taken today |
**can_take_quiz** | **bool** | Whether user can take another quiz |
**reason** | **str** | Reason if user cannot take quiz (e.g., &#39;Daily limit reached&#39;) | [optional]

## Example

```python
from lingible_client.models.quiz_history import QuizHistory

# TODO update the JSON string below
json = "{}"
# create an instance of QuizHistory from a JSON string
quiz_history_instance = QuizHistory.from_json(json)
# print the JSON string representation of the object
print(QuizHistory.to_json())

# convert the object into a dict
quiz_history_dict = quiz_history_instance.to_dict()
# create an instance of QuizHistory from a dict
quiz_history_from_dict = QuizHistory.from_dict(quiz_history_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
