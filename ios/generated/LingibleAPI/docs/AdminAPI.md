# AdminAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**slangAdminApproveSubmissionIdPost**](AdminAPI.md#slangadminapprovesubmissionidpost) | **POST** /slang/admin/approve/{submission_id} | Admin approve slang submission
[**slangAdminRejectSubmissionIdPost**](AdminAPI.md#slangadminrejectsubmissionidpost) | **POST** /slang/admin/reject/{submission_id} | Admin reject slang submission


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
AdminAPI.slangAdminApproveSubmissionIdPost(submissionId: submissionId) { (response, error) in
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
AdminAPI.slangAdminRejectSubmissionIdPost(submissionId: submissionId) { (response, error) in
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
