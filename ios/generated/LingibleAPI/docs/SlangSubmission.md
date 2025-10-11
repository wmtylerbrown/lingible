# SlangSubmission

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**submissionId** | **String** | Unique submission ID |
**userId** | **String** | User who submitted the term |
**slangTerm** | **String** | The slang term |
**meaning** | **String** | What the term means |
**exampleUsage** | **String** | Optional example usage | [optional]
**context** | **String** | How the submission was initiated |
**originalTranslationId** | **String** | Translation ID if from failed translation | [optional]
**status** | **String** | Overall approval status |
**llmValidationStatus** | **String** | LLM validation status |
**llmConfidenceScore** | **Float** | Confidence score from LLM validation | [optional]
**approvalType** | **String** | Type of approval if approved | [optional]
**upvotes** | **Int** | Number of community upvotes |
**createdAt** | **Date** | Submission timestamp |
**reviewedAt** | **Date** | Review timestamp | [optional]
**reviewedBy** | **String** | Reviewer user ID | [optional]
**approvedBy** | **String** | Admin who approved (if manual) | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
