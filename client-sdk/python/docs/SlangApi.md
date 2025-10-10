# lingible_client.SlangApi

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**slang_submit_post**](SlangApi.md#slang_submit_post) | **POST** /slang/submit | Submit new slang term


# **slang_submit_post**
> SlangSubmissionResponse slang_submit_post(slang_submission_request)

Submit new slang term

Submit a new slang term for review (premium feature)

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.slang_submission_request import SlangSubmissionRequest
from lingible_client.models.slang_submission_response import SlangSubmissionResponse
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
    api_instance = lingible_client.SlangApi(api_client)
    slang_submission_request = lingible_client.SlangSubmissionRequest() # SlangSubmissionRequest |

    try:
        # Submit new slang term
        api_response = api_instance.slang_submit_post(slang_submission_request)
        print("The response of SlangApi->slang_submit_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SlangApi->slang_submit_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **slang_submission_request** | [**SlangSubmissionRequest**](SlangSubmissionRequest.md)|  |

### Return type

[**SlangSubmissionResponse**](SlangSubmissionResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Slang submission created |  -  |
**400** | Invalid request |  -  |
**401** | Unauthorized |  -  |
**403** | Premium feature required |  -  |
**429** | Rate limit exceeded |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
