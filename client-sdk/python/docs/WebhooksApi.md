# lingible_client.WebhooksApi

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**webhook_apple_post**](WebhooksApi.md#webhook_apple_post) | **POST** /webhook/apple | Apple webhook for subscription notifications


# **webhook_apple_post**
> WebhookResponse webhook_apple_post(apple_webhook_request)

Apple webhook for subscription notifications

Webhook endpoint for Apple App Store subscription notifications

### Example


```python
import lingible_client
from lingible_client.models.apple_webhook_request import AppleWebhookRequest
from lingible_client.models.webhook_response import WebhookResponse
from lingible_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://api.dev.lingible.com
# See configuration.py for a list of all supported configuration parameters.
configuration = lingible_client.Configuration(
    host = "https://api.dev.lingible.com"
)


# Enter a context with an instance of the API client
with lingible_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = lingible_client.WebhooksApi(api_client)
    apple_webhook_request = lingible_client.AppleWebhookRequest() # AppleWebhookRequest |

    try:
        # Apple webhook for subscription notifications
        api_response = api_instance.webhook_apple_post(apple_webhook_request)
        print("The response of WebhooksApi->webhook_apple_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling WebhooksApi->webhook_apple_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **apple_webhook_request** | [**AppleWebhookRequest**](AppleWebhookRequest.md)|  |

### Return type

[**WebhookResponse**](WebhookResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Webhook processed successfully |  -  |
**400** | Invalid webhook payload |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
