# QuizAPI

All URIs are relative to *https://api.dev.lingible.com*

Method | HTTP request | Description
------------- | ------------- | -------------
[**quizChallengeGet**](QuizAPI.md#quizchallengeget) | **GET** /quiz/challenge | Get a quiz challenge
[**quizHistoryGet**](QuizAPI.md#quizhistoryget) | **GET** /quiz/history | Get quiz history and eligibility
[**quizSubmitPost**](QuizAPI.md#quizsubmitpost) | **POST** /quiz/submit | Submit quiz answers


# **quizChallengeGet**
```swift
    open class func quizChallengeGet(difficulty: Difficulty_quizChallengeGet? = nil, type: ModelType_quizChallengeGet? = nil, count: Int? = nil, completion: @escaping (_ data: QuizChallenge?, _ error: Error?) -> Void)
```

Get a quiz challenge

Generate a new quiz challenge for the authenticated user.  **Free Tier Features:** - Limited to 3 quizzes per day - Basic difficulty levels - Standard question count (10 questions)  **Premium Tier Features:** - Unlimited quizzes per day - All difficulty levels (beginner, intermediate, advanced) - Customizable question count (1-50 questions) - Multiple challenge types

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let difficulty = "difficulty_example" // String | Quiz difficulty level (optional) (default to .beginner)
let type = "type_example" // String | Type of quiz challenge (optional) (default to .multipleChoice)
let count = 987 // Int | Number of questions in the quiz (1-50) (optional) (default to 10)

// Get a quiz challenge
QuizAPI.quizChallengeGet(difficulty: difficulty, type: type, count: count) { (response, error) in
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
 **type** | **String** | Type of quiz challenge | [optional] [default to .multipleChoice]
 **count** | **Int** | Number of questions in the quiz (1-50) | [optional] [default to 10]

### Return type

[**QuizChallenge**](QuizChallenge.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
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

# **quizSubmitPost**
```swift
    open class func quizSubmitPost(quizSubmissionRequest: QuizSubmissionRequest, completion: @escaping (_ data: QuizResult?, _ error: Error?) -> Void)
```

Submit quiz answers

Submit answers for a quiz challenge and receive results.  The challenge must be valid and not expired. Results include: - Score and accuracy - Per-question feedback - Explanations for each term - Shareable result text

### Example
```swift
// The following code samples are still beta. For any issue, please report via http://github.com/OpenAPITools/openapi-generator/issues/new
import LingibleAPI

let quizSubmissionRequest = QuizSubmissionRequest(challengeId: "challengeId_example", answers: [QuizAnswer(questionId: "questionId_example", selected: "selected_example")], timeTakenSeconds: 123) // QuizSubmissionRequest |

// Submit quiz answers
QuizAPI.quizSubmitPost(quizSubmissionRequest: quizSubmissionRequest) { (response, error) in
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
 **quizSubmissionRequest** | [**QuizSubmissionRequest**](QuizSubmissionRequest.md) |  |

### Return type

[**QuizResult**](QuizResult.md)

### Authorization

[BearerAuth](../README.md#BearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
