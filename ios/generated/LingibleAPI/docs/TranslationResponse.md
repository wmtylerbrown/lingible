# TranslationResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**translationId** | **String** | Unique translation ID |
**originalText** | **String** |  |
**translatedText** | **String** |  |
**direction** | **String** | Translation direction used |
**confidenceScore** | **Double** |  | [optional]
**createdAt** | **Date** | Translation timestamp |
**processingTimeMs** | **Int** | Processing time in milliseconds | [optional]
**modelUsed** | **String** | AI model used for translation | [optional]
**translationFailed** | **Bool** | Whether the translation failed or returned the same text |
**failureReason** | **String** | Technical reason for translation failure | [optional]
**userMessage** | **String** | User-friendly message about the translation result | [optional]
**canSubmitFeedback** | **Bool** | Whether user can submit slang feedback (premium feature, only true when translation fails) | [optional]
**dailyUsed** | **Int** | Total translations used today (after this translation) |
**dailyLimit** | **Int** | Daily translation limit |
**tier** | **String** | User tier (free/premium) |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
