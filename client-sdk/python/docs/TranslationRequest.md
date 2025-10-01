# TranslationRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**text** | **str** | Text to translate |
**direction** | **str** | Translation direction |

## Example

```python
from lingible_client.models.translation_request import TranslationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of TranslationRequest from a JSON string
translation_request_instance = TranslationRequest.from_json(json)
# print the JSON string representation of the object
print(TranslationRequest.to_json())

# convert the object into a dict
translation_request_dict = translation_request_instance.to_dict()
# create an instance of TranslationRequest from a dict
translation_request_from_dict = TranslationRequest.from_dict(translation_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
