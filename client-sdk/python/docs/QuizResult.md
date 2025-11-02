# QuizResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**session_id** | **str** | Session ID |
**score** | **float** | Total score achieved |
**total_possible** | **float** | Maximum possible score |
**correct_count** | **int** | Number of correct answers |
**total_questions** | **int** | Total number of questions |
**time_taken_seconds** | **float** | Time taken to complete |
**share_text** | **str** | Text for sharing results |
**share_url** | **str** | URL for sharing results (future feature) | [optional]

## Example

```python
from lingible_client.models.quiz_result import QuizResult

# TODO update the JSON string below
json = "{}"
# create an instance of QuizResult from a JSON string
quiz_result_instance = QuizResult.from_json(json)
# print the JSON string representation of the object
print(QuizResult.to_json())

# convert the object into a dict
quiz_result_dict = quiz_result_instance.to_dict()
# create an instance of QuizResult from a dict
quiz_result_from_dict = QuizResult.from_dict(quiz_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
