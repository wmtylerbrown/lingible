# ModelErrorResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**success** | **Bool** | Always false for error responses | [optional]
**message** | **String** | Human-readable error message | [optional]
**errorCode** | **String** | Application-specific error code | [optional]
**statusCode** | **Int** | HTTP status code | [optional]
**details** | **AnyCodable** | Additional error details | [optional]
**timestamp** | **Date** | Error timestamp | [optional]
**requestId** | **String** | Request ID for tracing | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
