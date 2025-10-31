# QuizOption


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Option identifier (a, b, c, d) |
**text** | **str** | The answer text |
**is_correct** | **bool** | Whether this option is correct (only included in results, not in challenge) | [optional]

## Example

```python
from lingible_client.models.quiz_option import QuizOption

# TODO update the JSON string below
json = "{}"
# create an instance of QuizOption from a JSON string
quiz_option_instance = QuizOption.from_json(json)
# print the JSON string representation of the object
print(QuizOption.to_json())

# convert the object into a dict
quiz_option_dict = quiz_option_instance.to_dict()
# create an instance of QuizOption from a dict
quiz_option_from_dict = QuizOption.from_dict(quiz_option_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
