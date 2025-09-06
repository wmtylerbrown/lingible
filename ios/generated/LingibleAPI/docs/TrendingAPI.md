# TrendingAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**trendingGet**](TrendingAPI.md#trendingget) | **GET** /trending | Get trending GenZ slang terms


# **trendingGet**
```swift
    open class func trendingGet(limit: Int? = nil, category: Category_trendingGet? = nil, activeOnly: Bool? = nil, completion: @escaping (_ data: TrendingListResponse?, _ error: Error?) -> Void)
```

Get trending GenZ slang terms

Get a list of currently trending GenZ slang terms with popularity scores and metadata.  **Free Tier Features:** - Access to top 10 trending slang terms - Basic definitions and categories - Limited to 'slang' category only  **Premium Tier Features:** - Access to up to 100 trending terms - All categories (slang, meme, expression, hashtag, phrase) - Detailed usage examples and origins - Related terms and synonyms - Search and translation counts - Advanced filtering options 

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let limit = 987 // Int | Number of trending terms to return. - Free tier: Maximum 10 terms - Premium tier: Maximum 100 terms  (optional) (default to 50)
let category = "category_example" // String | Filter by trending category. - Free tier: Only 'slang' category allowed - Premium tier: All categories available  (optional)
let activeOnly = true // Bool | Show only active trending terms (optional) (default to true)

// Get trending GenZ slang terms
TrendingAPI.trendingGet(limit: limit, category: category, activeOnly: activeOnly) { (response, error) in
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
 **limit** | **Int** | Number of trending terms to return. - Free tier: Maximum 10 terms - Premium tier: Maximum 100 terms  | [optional] [default to 50]
 **category** | **String** | Filter by trending category. - Free tier: Only &#39;slang&#39; category allowed - Premium tier: All categories available  | [optional] 
 **activeOnly** | **Bool** | Show only active trending terms | [optional] [default to true]

### Return type

[**TrendingListResponse**](TrendingListResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

