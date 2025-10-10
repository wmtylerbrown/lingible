# TranslationResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**translation_id** | **str** | Unique translation ID |
**original_text** | **str** |  |
**translated_text** | **str** |  |
**direction** | **str** | Translation direction used |
**confidence_score** | **float** |  | [optional]
**created_at** | **datetime** | Translation timestamp |
**processing_time_ms** | **int** | Processing time in milliseconds | [optional]
**model_used** | **str** | AI model used for translation | [optional]
**translation_failed** | **bool** | Whether the translation failed or returned the same text |
**failure_reason** | **str** | Technical reason for translation failure | [optional]
**user_message** | **str** | User-friendly message about the translation result | [optional]
**can_submit_feedback** | **bool** | Whether user can submit slang feedback (premium feature, only true when translation fails) | [optional]
**daily_used** | **int** | Total translations used today (after this translation) |
**daily_limit** | **int** | Daily translation limit |
**tier** | **str** | User tier (free/premium) |

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
