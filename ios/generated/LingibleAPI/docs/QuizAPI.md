# QuizAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**quizAnswerPost**](QuizAPI.md#quizanswerpost) | **POST** /quiz/answer | Submit answer for one question (stateless API)
[**quizEndPost**](QuizAPI.md#quizendpost) | **POST** /quiz/end | End quiz session and get final results (stateless API)
[**quizHistoryGet**](QuizAPI.md#quizhistoryget) | **GET** /quiz/history | Get quiz history and eligibility
[**quizProgressGet**](QuizAPI.md#quizprogressget) | **GET** /quiz/progress | Get current quiz session progress (stateless API)
[**quizQuestionGet**](QuizAPI.md#quizquestionget) | **GET** /quiz/question | Get next quiz question (stateless API)


# **quizAnswerPost**
```swift
    open class func quizAnswerPost(quizAnswerRequest: QuizAnswerRequest, completion: @escaping (_ data: QuizAnswerResponse?, _ error: Error?) -> Void)
```

Submit answer for one question (stateless API)

Submit an answer for a single question and receive immediate feedback with running statistics.  **Response includes:** - Whether the answer was correct - Points earned (time-based scoring) - Explanation of the correct answer - Running statistics (score, accuracy, time spent)  **Scoring:** - Points decrease based on time taken (faster = more points) - Maximum 10 points per question - Minimum 1 point even if timer expires - Incorrect answers earn 0 points

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let quizAnswerRequest = QuizAnswerRequest(sessionId: "sessionId_example", questionId: "questionId_example", selectedOption: "selectedOption_example", timeTakenSeconds: 123) // QuizAnswerRequest |

// Submit answer for one question (stateless API)
QuizAPI.quizAnswerPost(quizAnswerRequest: quizAnswerRequest) { (response, error) in
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
 **quizAnswerRequest** | [**QuizAnswerRequest**](QuizAnswerRequest.md) |  |

### Return type

[**QuizAnswerResponse**](QuizAnswerResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **quizEndPost**
```swift
    open class func quizEndPost(quizEndRequest: QuizEndRequest, completion: @escaping (_ data: QuizResult?, _ error: Error?) -> Void)
```

End quiz session and get final results (stateless API)

End the current quiz session and receive final results. Saves the session to history for lifetime statistics tracking.  **Post-End Actions:** - Session marked as completed - Results saved to quiz history - Statistics aggregated for user profile - Shareable result text generated

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let quizEndRequest = QuizEndRequest(sessionId: "sessionId_example") // QuizEndRequest |

// End quiz session and get final results (stateless API)
QuizAPI.quizEndPost(quizEndRequest: quizEndRequest) { (response, error) in
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
 **quizEndRequest** | [**QuizEndRequest**](QuizEndRequest.md) |  |

### Return type

[**QuizResult**](QuizResult.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **quizHistoryGet**
```swift
    open class func quizHistoryGet(completion: @escaping (_ data: QuizHistory?, _ error: Error?) -> Void)
```

Get quiz history and eligibility

Get the user's quiz history, statistics, and eligibility status.  Returns: - Total quizzes taken - Average score and best score - Accuracy rate - Quizzes taken today - Whether user can take another quiz - Reason if quiz is not available

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI


// Get quiz history and eligibility
QuizAPI.quizHistoryGet() { (response, error) in
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

[**QuizHistory**](QuizHistory.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **quizProgressGet**
```swift
    open class func quizProgressGet(sessionId: String, completion: @escaping (_ data: QuizSessionProgress?, _ error: Error?) -> Void)
```

Get current quiz session progress (stateless API)

Get current progress statistics for an active quiz session.  Returns: - Questions answered so far - Correct count and accuracy - Total score accumulated - Time spent on quiz

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let sessionId = "sessionId_example" // String | Quiz session identifier

// Get current quiz session progress (stateless API)
QuizAPI.quizProgressGet(sessionId: sessionId) { (response, error) in
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
 **sessionId** | **String** | Quiz session identifier |

### Return type

[**QuizSessionProgress**](QuizSessionProgress.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **quizQuestionGet**
```swift
    open class func quizQuestionGet(difficulty: Difficulty_quizQuestionGet? = nil, completion: @escaping (_ data: QuizQuestionResponse?, _ error: Error?) -> Void)
```

Get next quiz question (stateless API)

Get the next question for the current quiz session. Creates a new session if none exists or if the previous session has expired (>15 minutes inactive).  **Features:** - No upfront question count required - Automatic session management - Validates free tier daily question limits - Returns single question with normalized answer options  **Session Management:** - One active session per user - Auto-expires after 15 minutes of inactivity - Sessions auto-cleanup via DynamoDB TTL (24 hours)

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let difficulty = "difficulty_example" // String | Quiz difficulty level (optional) (default to .beginner)

// Get next quiz question (stateless API)
QuizAPI.quizQuestionGet(difficulty: difficulty) { (response, error) in
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
 **difficulty** | **String** | Quiz difficulty level | [optional] [default to .beginner]

### Return type

[**QuizQuestionResponse**](QuizQuestionResponse.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
