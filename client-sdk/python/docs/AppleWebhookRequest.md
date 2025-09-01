# AppleWebhookRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**notification_type** | **str** | Type of Apple subscription notification |
**transaction_id** | **str** | Apple transaction ID |
**receipt_data** | **str** | Base64 encoded receipt data from Apple |

## Example

```python
from lingible_client.models.apple_webhook_request import AppleWebhookRequest

# TODO update the JSON string below
json = "{}"
# create an instance of AppleWebhookRequest from a JSON string
apple_webhook_request_instance = AppleWebhookRequest.from_json(json)
# print the JSON string representation of the object
print(AppleWebhookRequest.to_json())

# convert the object into a dict
apple_webhook_request_dict = apple_webhook_request_instance.to_dict()
# create an instance of AppleWebhookRequest from a dict
apple_webhook_request_from_dict = AppleWebhookRequest.from_dict(apple_webhook_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
