# QuizChallenge


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**challenge_id** | **str** | Unique challenge identifier |
**challenge_type** | [**ChallengeType**](ChallengeType.md) |  |
**difficulty** | [**QuizDifficulty**](QuizDifficulty.md) |  |
**time_limit_seconds** | **int** | Time limit for completing the quiz |
**questions** | [**List[QuizQuestion]**](QuizQuestion.md) | List of quiz questions |
**scoring** | [**QuizChallengeScoring**](QuizChallengeScoring.md) |  |
**expires_at** | **datetime** | When the challenge expires |

## Example

```python
from lingible_client.models.quiz_challenge import QuizChallenge

# TODO update the JSON string below
json = "{}"
# create an instance of QuizChallenge from a JSON string
quiz_challenge_instance = QuizChallenge.from_json(json)
# print the JSON string representation of the object
print(QuizChallenge.to_json())

# convert the object into a dict
quiz_challenge_dict = quiz_challenge_instance.to_dict()
# create an instance of QuizChallenge from a dict
quiz_challenge_from_dict = QuizChallenge.from_dict(quiz_challenge_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
