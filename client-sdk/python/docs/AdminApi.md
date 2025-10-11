# lingible_client.AdminApi

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**slang_admin_approve_submission_id_post**](AdminApi.md#slang_admin_approve_submission_id_post) | **POST** /slang/admin/approve/{submission_id} | Admin approve slang submission
[**slang_admin_reject_submission_id_post**](AdminApi.md#slang_admin_reject_submission_id_post) | **POST** /slang/admin/reject/{submission_id} | Admin reject slang submission


# **slang_admin_approve_submission_id_post**
> AdminApprovalResponse slang_admin_approve_submission_id_post(submission_id)

Admin approve slang submission

Manually approve a slang submission (admin only)

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.admin_approval_response import AdminApprovalResponse
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
    api_instance = lingible_client.AdminApi(api_client)
    submission_id = 'submission_id_example' # str | The submission ID to approve

    try:
        # Admin approve slang submission
        api_response = api_instance.slang_admin_approve_submission_id_post(submission_id)
        print("The response of AdminApi->slang_admin_approve_submission_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->slang_admin_approve_submission_id_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **submission_id** | **str**| The submission ID to approve |

### Return type

[**AdminApprovalResponse**](AdminApprovalResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Submission approved successfully |  -  |
**401** | Unauthorized |  -  |
**403** | Admin access required |  -  |
**404** | Submission not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **slang_admin_reject_submission_id_post**
> AdminApprovalResponse slang_admin_reject_submission_id_post(submission_id)

Admin reject slang submission

Manually reject a slang submission (admin only)

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.admin_approval_response import AdminApprovalResponse
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
    api_instance = lingible_client.AdminApi(api_client)
    submission_id = 'submission_id_example' # str | The submission ID to reject

    try:
        # Admin reject slang submission
        api_response = api_instance.slang_admin_reject_submission_id_post(submission_id)
        print("The response of AdminApi->slang_admin_reject_submission_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AdminApi->slang_admin_reject_submission_id_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **submission_id** | **str**| The submission ID to reject |

### Return type

[**AdminApprovalResponse**](AdminApprovalResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Submission rejected successfully |  -  |
**401** | Unauthorized |  -  |
**403** | Admin access required |  -  |
**404** | Submission not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
