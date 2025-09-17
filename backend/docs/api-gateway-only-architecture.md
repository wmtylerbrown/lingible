# API Gateway-Only Architecture

## 🎯 **Overview**

Lingible uses a **simplified architecture** where **all requests go through API Gateway**. This provides a clean, secure, and maintainable approach to handling mobile app requests.

## 🏗️ **Architecture Flow**

```mermaid
graph TD
    A[Mobile App] --> B[Apple Sign-In]
    B --> C[Cognito User Pool]
    C --> D[JWT ID Token]
    D --> E[API Gateway]
    E --> F[Native Cognito Authorizer]
    F --> G[Lambda Functions]
    G --> H[DynamoDB]
    G --> I[AWS Bedrock]
    G --> J[CloudWatch Logs]
```

## 🔐 **Authentication Flow**

### **1. User Authentication**
```javascript
// Mobile app authenticates with Apple Sign-In
const user = await Auth.signIn('APPLE');
const idToken = user.signInUserSession.idToken.jwtToken; // Use ID token for API calls
```

### **2. API Requests**
```javascript
// All API requests include JWT token
const response = await fetch('https://api.dev.lingible.com/translate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: 'Hello world',
    target_language: 'genz'
  })
});
```

### **3. Authorization**
```python
# API Gateway authorizer validates JWT token
@tracer.trace_lambda
def handler(event, context):
    # Validate JWT token
    token = event['authorizationToken']
    user_info = validate_jwt_token(token)

    # Return IAM policy for API Gateway
    return generate_policy(user_info)
```

## 🚀 **Benefits of API Gateway-Only**

### **✅ Security**
- **Centralized Authentication** - All requests go through API Gateway authorizer
- **JWT Validation** - Consistent token validation across all endpoints
- **Rate Limiting** - API Gateway provides built-in rate limiting
- **CORS Control** - Centralized CORS configuration

### **✅ Simplicity**
- **Single Entry Point** - All requests go through one URL
- **Consistent Interface** - RESTful API with standard HTTP methods
- **Easy Monitoring** - All traffic flows through API Gateway
- **Simple Mobile Integration** - One authentication flow

### **✅ Maintainability**
- **Business Logic in Lambda** - All complex logic in serverless functions
- **No Direct AWS Access** - Mobile apps don't need AWS SDK
- **Centralized Logging** - All requests logged in CloudWatch
- **Easy Testing** - Test API endpoints directly

### **✅ Cost Efficiency**
- **No Identity Pool** - Reduced AWS service costs
- **Optimized Lambda** - Only pay for actual processing time
- **Efficient Caching** - API Gateway response caching
- **Predictable Pricing** - Pay per API call

## 📱 **Mobile App Integration**

### **React Native Example**
```javascript
import { Auth } from 'aws-amplify';

class LingibleAPI {
  constructor() {
    this.baseURL = 'https://api.dev.lingible.com';
  }

  async getAuthHeaders() {
    const user = await Auth.currentAuthenticatedUser();
    const token = user.signInUserSession.idToken.jwtToken;
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async translateText(text, targetLanguage) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/translate`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ text, target_language: targetLanguage })
    });
    return response.json();
  }

  async getUserProfile() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/user/profile`, {
      method: 'GET',
      headers
    });
    return response.json();
  }

  async getTranslationHistory() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/translations/history`, {
      method: 'GET',
      headers
    });
    return response.json();
  }
}
```

### **Flutter Example**
```dart
import 'package:http/http.dart' as http;
import 'package:amazon_cognito_identity_dart/amazon_cognito_identity_dart.dart';

class LingibleAPI {
  static const String baseURL = 'https://api.dev.lingible.com';
  late CognitoUserPool userPool;
  late CognitoUser cognitoUser;

  Future<Map<String, String>> getAuthHeaders() async {
    final session = await cognitoUser.getSession();
    final token = session?.getAccessToken().getJwtToken();
    return {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json'
    };
  }

  Future<Map<String, dynamic>> translateText(String text, String targetLanguage) async {
    final headers = await getAuthHeaders();
    final response = await http.post(
      Uri.parse('$baseURL/translate'),
      headers: headers,
      body: jsonEncode({
        'text': text,
        'target_language': targetLanguage
      })
    );
    return jsonDecode(response.body);
  }
}
```

## 🔧 **API Endpoints**

### **Authentication**
- `POST /auth/login` - Apple Sign-In (handled by Cognito)
- `POST /auth/refresh` - Refresh JWT token

### **Translation**
- `POST /translate` - Translate text
- `GET /translations/history` - Get translation history
- `DELETE /translations/{id}` - Delete translation
- `DELETE /translations/all` - Delete all translations

### **User Management**
- `GET /user/profile` - Get user profile
- `PUT /user/profile` - Update user profile
- `GET /user/usage` - Get usage statistics
- `POST /user/upgrade` - Upgrade subscription

### **System**
- `GET /health` - Health check

## 🛡️ **Security Features**

### **1. JWT Token Validation**
```python
# API Gateway authorizer validates tokens
def validate_jwt_token(token):
    # Verify token signature using Cognito public keys
    # Check token expiration
    # Extract user information
    return user_info
```

### **2. Rate Limiting**
```python
# API Gateway usage plans
usage_plan = apigateway.UsagePlan(
    name="LingibleUsagePlan",
    throttle=apigateway.ThrottleSettings(
        rate_limit=100,  # requests per second
        burst_limit=20   # burst capacity
    )
)
```

### **3. CORS Configuration**
```python
# API Gateway CORS settings
api.add_cors_preflight(
    allow_origins=["https://app.dev.lingible.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"]
)
```

## 📊 **Monitoring & Observability**

### **1. API Gateway Metrics**
- Request count and latency
- Error rates and 4xx/5xx responses
- Cache hit/miss ratios
- Throttle count

### **2. Lambda Metrics**
- Invocation count and duration
- Error rates and concurrent executions
- Cold start frequency
- Memory usage

### **3. CloudWatch Logs**
- API Gateway access logs
- Lambda function logs
- Authorizer logs
- Custom application logs

## 🚀 **Deployment**

### **Development**
```bash
# Deploy with Apple credentials
python3 deploy-with-apple-credentials.py
```

### **Production**
```bash
# Set environment variables
export CDK_CONTEXT_APPLE_CLIENT_ID="com.lingible.lingible"
export CDK_CONTEXT_APPLE_TEAM_ID="YOUR_TEAM_ID"
export CDK_CONTEXT_APPLE_KEY_ID="YOUR_KEY_ID"
export CDK_CONTEXT_APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"

# Deploy
python3 deploy-prod.py
```

## 🎯 **Summary**

The **API Gateway-only architecture** provides:

- ✅ **Maximum Security** - All requests authenticated and authorized
- ✅ **Simplified Mobile Integration** - Standard HTTP/REST API
- ✅ **Centralized Control** - All business logic in Lambda functions
- ✅ **Cost Efficiency** - No unnecessary AWS services
- ✅ **Easy Monitoring** - Single point of observation
- ✅ **Scalability** - Serverless auto-scaling

This architecture is **perfect for mobile apps** that need a secure, scalable, and maintainable backend! 🚀
