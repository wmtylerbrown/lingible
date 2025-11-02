# lingible_client.QuizApi

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**quiz_answer_post**](QuizApi.md#quiz_answer_post) | **POST** /quiz/answer | Submit answer for one question (stateless API)
[**quiz_end_post**](QuizApi.md#quiz_end_post) | **POST** /quiz/end | End quiz session and get final results (stateless API)
[**quiz_history_get**](QuizApi.md#quiz_history_get) | **GET** /quiz/history | Get quiz history and eligibility
[**quiz_progress_get**](QuizApi.md#quiz_progress_get) | **GET** /quiz/progress | Get current quiz session progress (stateless API)
[**quiz_question_get**](QuizApi.md#quiz_question_get) | **GET** /quiz/question | Get next quiz question (stateless API)


# **quiz_answer_post**
> QuizAnswerResponse quiz_answer_post(quiz_answer_request)

Submit answer for one question (stateless API)

Submit an answer for a single question and receive immediate feedback with running statistics.

**Response includes:**
- Whether the answer was correct
- Points earned (time-based scoring)
- Explanation of the correct answer
- Running statistics (score, accuracy, time spent)

**Scoring:**
- Points decrease based on time taken (faster = more points)
- Maximum 10 points per question
- Minimum 1 point even if timer expires
- Incorrect answers earn 0 points


### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.quiz_answer_request import QuizAnswerRequest
from lingible_client.models.quiz_answer_response import QuizAnswerResponse
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
    quiz_answer_request = lingible_client.QuizAnswerRequest() # QuizAnswerRequest |

    try:
        # Submit answer for one question (stateless API)
        api_response = api_instance.quiz_answer_post(quiz_answer_request)
        print("The response of QuizApi->quiz_answer_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling QuizApi->quiz_answer_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **quiz_answer_request** | [**QuizAnswerRequest**](QuizAnswerRequest.md)|  |

### Return type

[**QuizAnswerResponse**](QuizAnswerResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Answer submitted successfully |  -  |
**401** | Unauthorized |  -  |
**429** | Daily question limit reached (free tier) |  -  |
**400** | Invalid request, expired session, or question not found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **quiz_end_post**
> QuizResult quiz_end_post(quiz_end_request)

End quiz session and get final results (stateless API)

End the current quiz session and receive final results. Saves the session to history
for lifetime statistics tracking.

**Post-End Actions:**
- Session marked as completed
- Results saved to quiz history
- Statistics aggregated for user profile
- Shareable result text generated


### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.quiz_end_request import QuizEndRequest
from lingible_client.models.quiz_result import QuizResult
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
    quiz_end_request = lingible_client.QuizEndRequest() # QuizEndRequest |

    try:
        # End quiz session and get final results (stateless API)
        api_response = api_instance.quiz_end_post(quiz_end_request)
        print("The response of QuizApi->quiz_end_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling QuizApi->quiz_end_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **quiz_end_request** | [**QuizEndRequest**](QuizEndRequest.md)|  |

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
**200** | Session ended successfully |  -  |
**400** | Invalid session or no questions answered |  -  |
**401** | Unauthorized |  -  |

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

# **quiz_progress_get**
> QuizSessionProgress quiz_progress_get(session_id)

Get current quiz session progress (stateless API)

Get current progress statistics for an active quiz session.

Returns:
- Questions answered so far
- Correct count and accuracy
- Total score accumulated
- Time spent on quiz


### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.quiz_session_progress import QuizSessionProgress
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
    session_id = 'session_id_example' # str | Quiz session identifier

    try:
        # Get current quiz session progress (stateless API)
        api_response = api_instance.quiz_progress_get(session_id)
        print("The response of QuizApi->quiz_progress_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling QuizApi->quiz_progress_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **str**| Quiz session identifier |

### Return type

[**QuizSessionProgress**](QuizSessionProgress.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Progress retrieved successfully |  -  |
**400** | Missing session_id or invalid request |  -  |
**401** | Unauthorized |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **quiz_question_get**
> QuizQuestionResponse quiz_question_get(difficulty=difficulty)

Get next quiz question (stateless API)

Get the next question for the current quiz session. Creates a new session if none exists
or if the previous session has expired (>15 minutes inactive).

**Features:**
- No upfront question count required
- Automatic session management
- Validates free tier daily question limits
- Returns single question with normalized answer options

**Session Management:**
- One active session per user
- Auto-expires after 15 minutes of inactivity
- Sessions auto-cleanup via DynamoDB TTL (24 hours)


### Example

* Bearer (JWT) Authentication (BearerAuth):

```python
import lingible_client
from lingible_client.models.quiz_question_response import QuizQuestionResponse
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

    try:
        # Get next quiz question (stateless API)
        api_response = api_instance.quiz_question_get(difficulty=difficulty)
        print("The response of QuizApi->quiz_question_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling QuizApi->quiz_question_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **difficulty** | **str**| Quiz difficulty level | [optional] [default to beginner]

### Return type

[**QuizQuestionResponse**](QuizQuestionResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Question retrieved successfully |  -  |
**401** | Unauthorized |  -  |
**429** | Daily question limit reached (free tier) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
