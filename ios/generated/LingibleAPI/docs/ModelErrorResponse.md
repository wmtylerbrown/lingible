# ModelErrorResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**success** | **Bool** | Always false for error responses |
**message** | **String** | Human-readable error message |
**errorCode** | **String** | Application-specific error code |
**statusCode** | **Int** | HTTP status code |
**details** | **AnyCodable** | Additional error details | [optional]
**timestamp** | **Date** | Error timestamp |
**requestId** | **String** | Request ID for tracing | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
