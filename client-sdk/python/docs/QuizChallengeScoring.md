# QuizChallengeScoring

Scoring configuration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**points_per_correct** | **int** |  | [optional]
**time_bonus** | **bool** | Enable time bonus points | [optional]

## Example

```python
from lingible_client.models.quiz_challenge_scoring import QuizChallengeScoring

# TODO update the JSON string below
json = "{}"
# create an instance of QuizChallengeScoring from a JSON string
quiz_challenge_scoring_instance = QuizChallengeScoring.from_json(json)
# print the JSON string representation of the object
print(QuizChallengeScoring.to_json())

# convert the object into a dict
quiz_challenge_scoring_dict = quiz_challenge_scoring_instance.to_dict()
# create an instance of QuizChallengeScoring from a dict
quiz_challenge_scoring_from_dict = QuizChallengeScoring.from_dict(quiz_challenge_scoring_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
