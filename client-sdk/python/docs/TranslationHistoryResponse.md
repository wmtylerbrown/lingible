# TranslationHistoryResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**translations** | [**List[TranslationResponse]**](TranslationResponse.md) |  | [optional]
**pagination** | [**PaginationInfo**](PaginationInfo.md) |  | [optional]

## Example

```python
from lingible_client.models.translation_history_response import TranslationHistoryResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TranslationHistoryResponse from a JSON string
translation_history_response_instance = TranslationHistoryResponse.from_json(json)
# print the JSON string representation of the object
print(TranslationHistoryResponse.to_json())

# convert the object into a dict
translation_history_response_dict = translation_history_response_instance.to_dict()
# create an instance of TranslationHistoryResponse from a dict
translation_history_response_from_dict = TranslationHistoryResponse.from_dict(translation_history_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
