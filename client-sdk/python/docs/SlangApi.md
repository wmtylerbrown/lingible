# lingible_client.SlangApi

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**slang_admin_approve_submission_id_post**](SlangApi.md#slang_admin_approve_submission_id_post) | **POST** /slang/admin/approve/{submission_id} | Admin approve slang submission
[**slang_admin_reject_submission_id_post**](SlangApi.md#slang_admin_reject_submission_id_post) | **POST** /slang/admin/reject/{submission_id} | Admin reject slang submission
[**slang_pending_get**](SlangApi.md#slang_pending_get) | **GET** /slang/pending | Get pending slang submissions
[**slang_submit_post**](SlangApi.md#slang_submit_post) | **POST** /slang/submit | Submit new slang term
[**slang_upvote_submission_id_post**](SlangApi.md#slang_upvote_submission_id_post) | **POST** /slang/upvote/{submission_id} | Upvote a slang submission


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
    api_instance = lingible_client.SlangApi(api_client)
    submission_id = 'submission_id_example' # str | The submission ID to approve

    try:
        # Admin approve slang submission
        api_response = api_instance.slang_admin_approve_submission_id_post(submission_id)
        print("The response of SlangApi->slang_admin_approve_submission_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SlangApi->slang_admin_approve_submission_id_post: %s\n" % e)
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
    api_instance = lingible_client.SlangApi(api_client)
    submission_id = 'submission_id_example' # str | The submission ID to reject

    try:
        # Admin reject slang submission
        api_response = api_instance.slang_admin_reject_submission_id_post(submission_id)
        print("The response of SlangApi->slang_admin_reject_submission_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SlangApi->slang_admin_reject_submission_id_post: %s\n" % e)
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

# **slang_pending_get**
> PendingSubmissionsResponse slang_pending_get(limit=limit)

Get pending slang submissions

Get slang submissions available for community voting (VALIDATED status)

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.pending_submissions_response import PendingSubmissionsResponse
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
    limit = 50 # int | Maximum number of submissions to return (optional) (default to 50)

    try:
        # Get pending slang submissions
        api_response = api_instance.slang_pending_get(limit=limit)
        print("The response of SlangApi->slang_pending_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SlangApi->slang_pending_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int**| Maximum number of submissions to return | [optional] [default to 50]

### Return type

[**PendingSubmissionsResponse**](PendingSubmissionsResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | List of pending submissions |  -  |
**401** | Unauthorized |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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

# **slang_upvote_submission_id_post**
> UpvoteResponse slang_upvote_submission_id_post(submission_id)

Upvote a slang submission

Add an upvote to a pending slang submission (cannot upvote own submissions)

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.upvote_response import UpvoteResponse
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
    submission_id = 'submission_id_example' # str | The submission ID to upvote

    try:
        # Upvote a slang submission
        api_response = api_instance.slang_upvote_submission_id_post(submission_id)
        print("The response of SlangApi->slang_upvote_submission_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SlangApi->slang_upvote_submission_id_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **submission_id** | **str**| The submission ID to upvote |

### Return type

[**UpvoteResponse**](UpvoteResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Upvote added successfully |  -  |
**400** | Invalid request (already upvoted or own submission) |  -  |
**401** | Unauthorized |  -  |
**404** | Submission not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
