# QuizSessionProgress


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**questions_answered** | **int** | Number of questions answered |
**correct_count** | **int** | Number of correct answers |
**total_score** | **float** | Total score accumulated |
**accuracy** | **float** | Current accuracy rate (0.0 to 1.0) |
**time_spent_seconds** | **float** | Total time spent on quiz so far |

## Example

```python
from lingible_client.models.quiz_session_progress import QuizSessionProgress

# TODO update the JSON string below
json = "{}"
# create an instance of QuizSessionProgress from a JSON string
quiz_session_progress_instance = QuizSessionProgress.from_json(json)
# print the JSON string representation of the object
print(QuizSessionProgress.to_json())

# convert the object into a dict
quiz_session_progress_dict = quiz_session_progress_instance.to_dict()
# create an instance of QuizSessionProgress from a dict
quiz_session_progress_from_dict = QuizSessionProgress.from_dict(quiz_session_progress_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
