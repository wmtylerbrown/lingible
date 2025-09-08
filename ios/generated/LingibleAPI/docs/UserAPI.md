# UserAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**userAccountDelete**](UserAPI.md#useraccountdelete) | **DELETE** /user/account | Delete user account
[**userProfileGet**](UserAPI.md#userprofileget) | **GET** /user/profile | Get user profile
[**userUpgradePost**](UserAPI.md#userupgradepost) | **POST** /user/upgrade | Upgrade user subscription
[**userUsageGet**](UserAPI.md#userusageget) | **GET** /user/usage | Get usage statistics


# **userAccountDelete**
```swift
    open class func userAccountDelete(accountDeletionRequest: AccountDeletionRequest, completion: @escaping (_ data: AccountDeletionResponse?, _ error: Error?) -> Void)
```

Delete user account

Permanently delete the user's account and all associated data. This action cannot be undone. Requires that the user has no active subscription - cancel subscription first in App Store/Google Play Store.

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let accountDeletionRequest = AccountDeletionRequest(confirmationText: "confirmationText_example", reason: "reason_example") // AccountDeletionRequest |

// Delete user account
UserAPI.userAccountDelete(accountDeletionRequest: accountDeletionRequest) { (response, error) in
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
 **accountDeletionRequest** | [**AccountDeletionRequest**](AccountDeletionRequest.md) |  |

### Return type

[**AccountDeletionResponse**](AccountDeletionResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **userProfileGet**
```swift
    open class func userProfileGet(completion: @escaping (_ data: UserProfileResponse?, _ error: Error?) -> Void)
```

Get user profile

Get the current user's profile information

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI


// Get user profile
UserAPI.userProfileGet() { (response, error) in
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

[**UserProfileResponse**](UserProfileResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **userUpgradePost**
```swift
    open class func userUpgradePost(upgradeRequest: UpgradeRequest, completion: @escaping (_ data: UpgradeResponse?, _ error: Error?) -> Void)
```

Upgrade user subscription

Upgrade user to premium subscription

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let upgradeRequest = UpgradeRequest(platform: "platform_example", receiptData: "receiptData_example", transactionId: "transactionId_example") // UpgradeRequest |

// Upgrade user subscription
UserAPI.userUpgradePost(upgradeRequest: upgradeRequest) { (response, error) in
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
 **upgradeRequest** | [**UpgradeRequest**](UpgradeRequest.md) |  |

### Return type

[**UpgradeResponse**](UpgradeResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **userUsageGet**
```swift
    open class func userUsageGet(completion: @escaping (_ data: UsageResponse?, _ error: Error?) -> Void)
```

Get usage statistics

Get the current user's usage statistics

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI


// Get usage statistics
UserAPI.userUsageGet() { (response, error) in
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

[**UsageResponse**](UsageResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
