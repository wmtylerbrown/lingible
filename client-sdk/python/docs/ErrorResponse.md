# ErrorResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**success** | **bool** | Always false for error responses |
**message** | **str** | Human-readable error message |
**error_code** | **str** | Application-specific error code |
**status_code** | **int** | HTTP status code |
**details** | **object** | Additional error details | [optional]
**timestamp** | **datetime** | Error timestamp |
**request_id** | **str** | Request ID for tracing | [optional]

## Example

```python
from lingible_client.models.error_response import ErrorResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ErrorResponse from a JSON string
error_response_instance = ErrorResponse.from_json(json)
# print the JSON string representation of the object
print(ErrorResponse.to_json())

# convert the object into a dict
error_response_dict = error_response_instance.to_dict()
# create an instance of ErrorResponse from a dict
error_response_from_dict = ErrorResponse.from_dict(error_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
