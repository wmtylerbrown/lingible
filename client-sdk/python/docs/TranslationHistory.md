# TranslationHistory


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**translation_id** | **str** | Unique translation ID |
**user_id** | **str** | User ID | [optional]
**original_text** | **str** |  |
**translated_text** | **str** |  |
**direction** | **str** | Translation direction used |
**confidence_score** | **float** |  | [optional]
**created_at** | **datetime** | Translation timestamp |
**model_used** | **str** | AI model used for translation | [optional]

## Example

```python
from lingible_client.models.translation_history import TranslationHistory

# TODO update the JSON string below
json = "{}"
# create an instance of TranslationHistory from a JSON string
translation_history_instance = TranslationHistory.from_json(json)
# print the JSON string representation of the object
print(TranslationHistory.to_json())

# convert the object into a dict
translation_history_dict = translation_history_instance.to_dict()
# create an instance of TranslationHistory from a dict
translation_history_from_dict = TranslationHistory.from_dict(translation_history_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
