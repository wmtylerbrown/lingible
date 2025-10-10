# SlangAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**slangSubmitPost**](SlangAPI.md#slangsubmitpost) | **POST** /slang/submit | Submit new slang term


# **slangSubmitPost**
```swift
    open class func slangSubmitPost(slangSubmissionRequest: SlangSubmissionRequest, completion: @escaping (_ data: SlangSubmissionResponse?, _ error: Error?) -> Void)
```

Submit new slang term

Submit a new slang term for review (premium feature)

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let slangSubmissionRequest = SlangSubmissionRequest(slangTerm: "slangTerm_example", meaning: "meaning_example", exampleUsage: "exampleUsage_example", context: "context_example", translationId: "translationId_example") // SlangSubmissionRequest |

// Submit new slang term
SlangAPI.slangSubmitPost(slangSubmissionRequest: slangSubmissionRequest) { (response, error) in
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
 **slangSubmissionRequest** | [**SlangSubmissionRequest**](SlangSubmissionRequest.md) |  |

### Return type

[**SlangSubmissionResponse**](SlangSubmissionResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
