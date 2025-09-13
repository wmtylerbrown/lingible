# TranslationResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**translationId** | **String** | Unique translation ID |
**originalText** | **String** |  |
**translatedText** | **String** |  |
**direction** | **String** | Translation direction used |
**confidenceScore** | **Float** |  | [optional]
**createdAt** | **Date** | Translation timestamp |
**processingTimeMs** | **Int** | Processing time in milliseconds | [optional]
**modelUsed** | **String** | AI model used for translation | [optional]
**dailyUsed** | **Int** | Total translations used today (after this translation) |
**dailyLimit** | **Int** | Daily translation limit |
**tier** | **String** | User tier (free/premium) |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
