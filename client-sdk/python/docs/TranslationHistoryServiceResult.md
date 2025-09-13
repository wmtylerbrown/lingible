# TranslationHistoryServiceResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**translations** | [**List[TranslationHistory]**](TranslationHistory.md) |  |
**total_count** | **int** | Total number of translations |
**has_more** | **bool** | Whether there are more translations to load |
**last_evaluated_key** | **object** | Pagination key for next request | [optional]

## Example

```python
from lingible_client.models.translation_history_service_result import TranslationHistoryServiceResult

# TODO update the JSON string below
json = "{}"
# create an instance of TranslationHistoryServiceResult from a JSON string
translation_history_service_result_instance = TranslationHistoryServiceResult.from_json(json)
# print the JSON string representation of the object
print(TranslationHistoryServiceResult.to_json())

# convert the object into a dict
translation_history_service_result_dict = translation_history_service_result_instance.to_dict()
# create an instance of TranslationHistoryServiceResult from a dict
translation_history_service_result_from_dict = TranslationHistoryServiceResult.from_dict(translation_history_service_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
