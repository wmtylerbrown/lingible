# WebhooksAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**webhookApplePost**](WebhooksAPI.md#webhookapplepost) | **POST** /webhook/apple | Apple webhook for subscription notifications


# **webhookApplePost**
```swift
    open class func webhookApplePost(appleWebhookRequest: AppleWebhookRequest, completion: @escaping (_ data: WebhookResponse?, _ error: Error?) -> Void)
```

Apple webhook for subscription notifications

Webhook endpoint for Apple App Store subscription notifications

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let appleWebhookRequest = AppleWebhookRequest(notificationType: "notificationType_example", transactionId: "transactionId_example", receiptData: "receiptData_example", environment: "environment_example") // AppleWebhookRequest | 

// Apple webhook for subscription notifications
WebhooksAPI.webhookApplePost(appleWebhookRequest: appleWebhookRequest) { (response, error) in
    guard error == nil else {
        print(error)
        return
    }

    if (response) {
        dump(response)
    }
}
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **appleWebhookRequest** | [**AppleWebhookRequest**](AppleWebhookRequest.md) |  | 

### Return type

[**WebhookResponse**](WebhookResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

