# TranslationAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**translatePost**](TranslationAPI.md#translatepost) | **POST** /translate | Translate teen slang
[**translationsDeleteAllDelete**](TranslationAPI.md#translationsdeletealldelete) | **DELETE** /translations/delete-all | Clear all slang translations
[**translationsGet**](TranslationAPI.md#translationsget) | **GET** /translations | Get slang translation history
[**translationsTranslationIdDelete**](TranslationAPI.md#translationstranslationiddelete) | **DELETE** /translations/{translationId} | Delete specific slang translation


# **translatePost**
```swift
    open class func translatePost(translationRequest: TranslationRequest, completion: @escaping (_ data: TranslationResponse?, _ error: Error?) -> Void)
```

Translate teen slang

Translate GenZ/teen slang to formal English and vice versa using AWS Bedrock AI

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let translationRequest = TranslationRequest(text: "text_example", direction: "direction_example") // TranslationRequest |

// Translate teen slang
TranslationAPI.translatePost(translationRequest: translationRequest) { (response, error) in
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
 **translationRequest** | [**TranslationRequest**](TranslationRequest.md) |  |

### Return type

[**TranslationResponse**](TranslationResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **translationsDeleteAllDelete**
```swift
    open class func translationsDeleteAllDelete(completion: @escaping (_ data: SuccessResponse?, _ error: Error?) -> Void)
```

Clear all slang translations

Delete all slang translations for the user (premium feature)

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI


// Clear all slang translations
TranslationAPI.translationsDeleteAllDelete() { (response, error) in
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
This endpoint does not need any parameter.

### Return type

[**SuccessResponse**](SuccessResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **translationsGet**
```swift
    open class func translationsGet(limit: Int? = nil, offset: Int? = nil, completion: @escaping (_ data: TranslationHistoryResponse?, _ error: Error?) -> Void)
```

Get slang translation history

Get user's slang translation history (premium feature)

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let limit = 987 // Int | Number of translations to return (optional) (default to 20)
let offset = 987 // Int | Number of translations to skip (optional) (default to 0)

// Get slang translation history
TranslationAPI.translationsGet(limit: limit, offset: offset) { (response, error) in
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
 **limit** | **Int** | Number of translations to return | [optional] [default to 20]
 **offset** | **Int** | Number of translations to skip | [optional] [default to 0]

### Return type

[**TranslationHistoryResponse**](TranslationHistoryResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **translationsTranslationIdDelete**
```swift
    open class func translationsTranslationIdDelete(translationId: String, completion: @escaping (_ data: SuccessResponse?, _ error: Error?) -> Void)
```

Delete specific slang translation

Delete a specific slang translation by ID

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let translationId = "translationId_example" // String | Translation ID

// Delete specific slang translation
TranslationAPI.translationsTranslationIdDelete(translationId: translationId) { (response, error) in
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
 **translationId** | **String** | Translation ID |

### Return type

[**SuccessResponse**](SuccessResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
