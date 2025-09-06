# lingible_client.TrendingApi

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**trending_get**](TrendingApi.md#trending_get) | **GET** /trending | Get trending GenZ slang terms


# **trending_get**
> TrendingListResponse trending_get(limit=limit, category=category, active_only=active_only)

Get trending GenZ slang terms

Get a list of currently trending GenZ slang terms with popularity scores and metadata.

**Free Tier Features:**
- Access to top 10 trending slang terms
- Basic definitions and categories
- Limited to 'slang' category only

**Premium Tier Features:**
- Access to up to 100 trending terms
- All categories (slang, meme, expression, hashtag, phrase)
- Detailed usage examples and origins
- Related terms and synonyms
- Search and translation counts
- Advanced filtering options


### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.trending_list_response import TrendingListResponse
from lingible_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://api.dev.lingible.com
# See configuration.py for a list of all supported configuration parameters.
configuration = lingible_client.Configuration(
    host = "https://api.dev.lingible.com"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): BearerAuth
configuration = lingible_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with lingible_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = lingible_client.TrendingApi(api_client)
    limit = 50 # int | Number of trending terms to return. - Free tier: Maximum 10 terms - Premium tier: Maximum 100 terms  (optional) (default to 50)
    category = 'category_example' # str | Filter by trending category. - Free tier: Only 'slang' category allowed - Premium tier: All categories available  (optional)
    active_only = True # bool | Show only active trending terms (optional) (default to True)

    try:
        # Get trending GenZ slang terms
        api_response = api_instance.trending_get(limit=limit, category=category, active_only=active_only)
        print("The response of TrendingApi->trending_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TrendingApi->trending_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int**| Number of trending terms to return. - Free tier: Maximum 10 terms - Premium tier: Maximum 100 terms  | [optional] [default to 50]
 **category** | **str**| Filter by trending category. - Free tier: Only &#39;slang&#39; category allowed - Premium tier: All categories available  | [optional] 
 **active_only** | **bool**| Show only active trending terms | [optional] [default to True]

### Return type

[**TrendingListResponse**](TrendingListResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Trending terms retrieved successfully |  -  |
**401** | Unauthorized |  -  |
**400** | Invalid request parameters |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

