# lingible_client.TranslationApi

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**translate_post**](TranslationApi.md#translate_post) | **POST** /translate | Translate teen slang
[**translations_delete_all_delete**](TranslationApi.md#translations_delete_all_delete) | **DELETE** /translations/delete-all | Clear all slang translations
[**translations_get**](TranslationApi.md#translations_get) | **GET** /translations | Get slang translation history
[**translations_translation_id_delete**](TranslationApi.md#translations_translation_id_delete) | **DELETE** /translations/{translationId} | Delete specific slang translation


# **translate_post**
> TranslationResponse translate_post(translation_request)

Translate teen slang

Translate GenZ/teen slang to formal English and vice versa using AWS Bedrock AI

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.translation_request import TranslationRequest
from lingible_client.models.translation_response import TranslationResponse
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
    api_instance = lingible_client.TranslationApi(api_client)
    translation_request = lingible_client.TranslationRequest() # TranslationRequest |

    try:
        # Translate teen slang
        api_response = api_instance.translate_post(translation_request)
        print("The response of TranslationApi->translate_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TranslationApi->translate_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **translation_request** | [**TranslationRequest**](TranslationRequest.md)|  |

### Return type

[**TranslationResponse**](TranslationResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Translation successful |  -  |
**400** | Invalid request |  -  |
**401** | Unauthorized |  -  |
**429** | Rate limit exceeded |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **translations_delete_all_delete**
> SuccessResponse translations_delete_all_delete()

Clear all slang translations

Delete all slang translations for the user (premium feature)

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.success_response import SuccessResponse
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
    api_instance = lingible_client.TranslationApi(api_client)

    try:
        # Clear all slang translations
        api_response = api_instance.translations_delete_all_delete()
        print("The response of TranslationApi->translations_delete_all_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TranslationApi->translations_delete_all_delete: %s\n" % e)
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

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | All translations deleted |  -  |
**401** | Unauthorized |  -  |
**403** | Premium feature required |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **translations_get**
> TranslationHistoryServiceResult translations_get(limit=limit, offset=offset)

Get slang translation history

Get user's slang translation history (premium feature)

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.translation_history_service_result import TranslationHistoryServiceResult
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
    api_instance = lingible_client.TranslationApi(api_client)
    limit = 20 # int | Number of translations to return (optional) (default to 20)
    offset = 0 # int | Number of translations to skip (optional) (default to 0)

    try:
        # Get slang translation history
        api_response = api_instance.translations_get(limit=limit, offset=offset)
        print("The response of TranslationApi->translations_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TranslationApi->translations_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int**| Number of translations to return | [optional] [default to 20]
 **offset** | **int**| Number of translations to skip | [optional] [default to 0]

### Return type

[**TranslationHistoryServiceResult**](TranslationHistoryServiceResult.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Translation history retrieved |  -  |
**401** | Unauthorized |  -  |
**403** | Premium feature required |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **translations_translation_id_delete**
> SuccessResponse translations_translation_id_delete(translation_id)

Delete specific slang translation

Delete a specific slang translation by ID

### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.success_response import SuccessResponse
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
    api_instance = lingible_client.TranslationApi(api_client)
    translation_id = 'translation_id_example' # str | Translation ID

    try:
        # Delete specific slang translation
        api_response = api_instance.translations_translation_id_delete(translation_id)
        print("The response of TranslationApi->translations_translation_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TranslationApi->translations_translation_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **translation_id** | **str**| Translation ID |

### Return type

[**SuccessResponse**](SuccessResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Translation deleted |  -  |
**401** | Unauthorized |  -  |
**404** | Slang translation not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
