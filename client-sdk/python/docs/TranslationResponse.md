# TranslationResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**translation_id** | **str** | Unique translation ID | [optional]
**original_text** | **str** |  | [optional]
**translated_text** | **str** |  | [optional]
**direction** | **str** | Translation direction used | [optional]
**confidence_score** | **float** |  | [optional]
**created_at** | **datetime** |  | [optional]
**processing_time_ms** | **int** | Processing time in milliseconds | [optional]
**model_used** | **str** | AI model used for translation | [optional]

## Example

```python
from lingible_client.models.translation_response import TranslationResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TranslationResponse from a JSON string
translation_response_instance = TranslationResponse.from_json(json)
# print the JSON string representation of the object
print(TranslationResponse.to_json())

# convert the object into a dict
translation_response_dict = translation_response_instance.to_dict()
# create an instance of TranslationResponse from a dict
translation_response_from_dict = TranslationResponse.from_dict(translation_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
