# SlangAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**slangAdminApproveSubmissionIdPost**](SlangAPI.md#slangadminapprovesubmissionidpost) | **POST** /slang/admin/approve/{submission_id} | Admin approve slang submission
[**slangAdminRejectSubmissionIdPost**](SlangAPI.md#slangadminrejectsubmissionidpost) | **POST** /slang/admin/reject/{submission_id} | Admin reject slang submission
[**slangPendingGet**](SlangAPI.md#slangpendingget) | **GET** /slang/pending | Get pending slang submissions
[**slangSubmitPost**](SlangAPI.md#slangsubmitpost) | **POST** /slang/submit | Submit new slang term
[**slangUpvoteSubmissionIdPost**](SlangAPI.md#slangupvotesubmissionidpost) | **POST** /slang/upvote/{submission_id} | Upvote a slang submission


# **slangAdminApproveSubmissionIdPost**
```swift
    open class func slangAdminApproveSubmissionIdPost(submissionId: String, completion: @escaping (_ data: AdminApprovalResponse?, _ error: Error?) -> Void)
```

Admin approve slang submission

Manually approve a slang submission (admin only)

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let submissionId = "submissionId_example" // String | The submission ID to approve

// Admin approve slang submission
SlangAPI.slangAdminApproveSubmissionIdPost(submissionId: submissionId) { (response, error) in
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
 **submissionId** | **String** | The submission ID to approve |

### Return type

[**AdminApprovalResponse**](AdminApprovalResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **slangAdminRejectSubmissionIdPost**
```swift
    open class func slangAdminRejectSubmissionIdPost(submissionId: String, completion: @escaping (_ data: AdminApprovalResponse?, _ error: Error?) -> Void)
```

Admin reject slang submission

Manually reject a slang submission (admin only)

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let submissionId = "submissionId_example" // String | The submission ID to reject

// Admin reject slang submission
SlangAPI.slangAdminRejectSubmissionIdPost(submissionId: submissionId) { (response, error) in
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
 **submissionId** | **String** | The submission ID to reject |

### Return type

[**AdminApprovalResponse**](AdminApprovalResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **slangPendingGet**
```swift
    open class func slangPendingGet(limit: Int? = nil, completion: @escaping (_ data: PendingSubmissionsResponse?, _ error: Error?) -> Void)
```

Get pending slang submissions

Get slang submissions available for community voting (VALIDATED status)

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let limit = 987 // Int | Maximum number of submissions to return (optional) (default to 50)

// Get pending slang submissions
SlangAPI.slangPendingGet(limit: limit) { (response, error) in
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
 **limit** | **Int** | Maximum number of submissions to return | [optional] [default to 50]

### Return type

[**PendingSubmissionsResponse**](PendingSubmissionsResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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

# **slangUpvoteSubmissionIdPost**
```swift
    open class func slangUpvoteSubmissionIdPost(submissionId: String, completion: @escaping (_ data: UpvoteResponse?, _ error: Error?) -> Void)
```

Upvote a slang submission

Add an upvote to a pending slang submission (cannot upvote own submissions)

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let submissionId = "submissionId_example" // String | The submission ID to upvote

// Upvote a slang submission
SlangAPI.slangUpvoteSubmissionIdPost(submissionId: submissionId) { (response, error) in
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
 **submissionId** | **String** | The submission ID to upvote |

### Return type

[**UpvoteResponse**](UpvoteResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
