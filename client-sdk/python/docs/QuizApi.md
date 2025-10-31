# lingible_client.QuizApi

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**quiz_challenge_get**](QuizApi.md#quiz_challenge_get) | **GET** /quiz/challenge | Get a quiz challenge
[**quiz_history_get**](QuizApi.md#quiz_history_get) | **GET** /quiz/history | Get quiz history and eligibility
[**quiz_submit_post**](QuizApi.md#quiz_submit_post) | **POST** /quiz/submit | Submit quiz answers


# **quiz_challenge_get**
> QuizChallenge quiz_challenge_get(difficulty=difficulty, type=type, count=count)

Get a quiz challenge

Generate a new quiz challenge for the authenticated user.

**Free Tier Features:**
- Limited to 3 quizzes per day
- Basic difficulty levels
- Standard question count (10 questions)

**Premium Tier Features:**
- Unlimited quizzes per day
- All difficulty levels (beginner, intermediate, advanced)
- Customizable question count (1-50 questions)
- Multiple challenge types


### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.quiz_challenge import QuizChallenge
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
    api_instance = lingible_client.QuizApi(api_client)
    difficulty = beginner # str | Quiz difficulty level (optional) (default to beginner)
    type = multiple_choice # str | Type of quiz challenge (optional) (default to multiple_choice)
    count = 10 # int | Number of questions in the quiz (1-50) (optional) (default to 10)

    try:
        # Get a quiz challenge
        api_response = api_instance.quiz_challenge_get(difficulty=difficulty, type=type, count=count)
        print("The response of QuizApi->quiz_challenge_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling QuizApi->quiz_challenge_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **difficulty** | **str**| Quiz difficulty level | [optional] [default to beginner]
 **type** | **str**| Type of quiz challenge | [optional] [default to multiple_choice]
 **count** | **int**| Number of questions in the quiz (1-50) | [optional] [default to 10]

### Return type

[**QuizChallenge**](QuizChallenge.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Quiz challenge generated successfully |  -  |
**401** | Unauthorized |  -  |
**400** | Invalid request parameters |  -  |
**403** | Daily quiz limit reached (free tier) or insufficient permissions |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **quiz_history_get**
> QuizHistory quiz_history_get()

Get quiz history and eligibility

Get the user's quiz history, statistics, and eligibility status.

Returns:
- Total quizzes taken
- Average score and best score
- Accuracy rate
- Quizzes taken today
- Whether user can take another quiz
- Reason if quiz is not available


### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.quiz_history import QuizHistory
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
    api_instance = lingible_client.QuizApi(api_client)

    try:
        # Get quiz history and eligibility
        api_response = api_instance.quiz_history_get()
        print("The response of QuizApi->quiz_history_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling QuizApi->quiz_history_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**QuizHistory**](QuizHistory.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Quiz history retrieved successfully |  -  |
**401** | Unauthorized |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **quiz_submit_post**
> QuizResult quiz_submit_post(quiz_submission_request)

Submit quiz answers

Submit answers for a quiz challenge and receive results.

The challenge must be valid and not expired. Results include:
- Score and accuracy
- Per-question feedback
- Explanations for each term
- Shareable result text


### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.quiz_result import QuizResult
from lingible_client.models.quiz_submission_request import QuizSubmissionRequest
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
    api_instance = lingible_client.QuizApi(api_client)
    quiz_submission_request = lingible_client.QuizSubmissionRequest() # QuizSubmissionRequest |

    try:
        # Submit quiz answers
        api_response = api_instance.quiz_submit_post(quiz_submission_request)
        print("The response of QuizApi->quiz_submit_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling QuizApi->quiz_submit_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **quiz_submission_request** | [**QuizSubmissionRequest**](QuizSubmissionRequest.md)|  |

### Return type

[**QuizResult**](QuizResult.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Quiz submitted successfully |  -  |
**401** | Unauthorized |  -  |
**400** | Invalid request or expired challenge |  -  |
**404** | Challenge not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
