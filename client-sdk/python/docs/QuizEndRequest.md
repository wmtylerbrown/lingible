# QuizEndRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**session_id** | **str** | Quiz session identifier |

## Example

```python
from lingible_client.models.quiz_end_request import QuizEndRequest

# TODO update the JSON string below
json = "{}"
# create an instance of QuizEndRequest from a JSON string
quiz_end_request_instance = QuizEndRequest.from_json(json)
# print the JSON string representation of the object
print(QuizEndRequest.to_json())

# convert the object into a dict
quiz_end_request_dict = quiz_end_request_instance.to_dict()
# create an instance of QuizEndRequest from a dict
quiz_end_request_from_dict = QuizEndRequest.from_dict(quiz_end_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
