# Backend Quiz Service Documentation

## Overview

The Lingible Quiz Service is a gamified learning system that helps users test and improve their knowledge of Gen Z slang terms. The service generates quiz challenges, tracks user performance, and provides detailed feedback to enhance the learning experience.

## Architecture

### Components

1. **QuizService** (`src/services/quiz_service.py`)
   - Core business logic for quiz generation, scoring, and eligibility
   - Manages DynamoDB session storage for stateless quiz flow
   - Integrates with `SlangTermRepository` for term retrieval
   - Integrates with `UserService` for user tier validation

2. **API Handlers**
   - `quiz_history_api/handler.py` - GET `/quiz/history` - Retrieve user quiz statistics and eligibility
   - `quiz_challenge_api/handler.py` - GET `/quiz/question` - Get next question (creates/uses session)
   - `quiz_submit_api/handler.py` - POST `/quiz/answer` - Submit answer for one question
   - `quiz_progress_api/handler.py` - GET `/quiz/progress` - Get current session progress
   - `quiz_end_api/handler.py` - POST `/quiz/end` - End quiz session and get final results

3. **Data Models** (`src/models/quiz.py`)
   - Strongly typed Pydantic models for all quiz-related data structures
   - All response models inherit from `LingibleBaseModel` for consistent JSON serialization

4. **Repository Layer** (`src/repositories/slang_term_repository.py`)
   - Quiz history persistence
   - Quiz statistics tracking per term
   - Daily quiz count tracking

## Supported Quiz Types

### Current Implementation

**Multiple Choice (MVP)** ✅
- Users are presented with a slang term and must select the correct meaning from 4 options
- Options are shuffled to prevent pattern recognition
- Context hints available (example usage of the term)
- Per-question timer with visual countdown
- Timer expiration marks question as missed

### Future Quiz Types (Planned)

The quiz system is designed for extensibility with future quiz types:
- `DECODE_MESSAGE` - Decode a message containing multiple slang terms
- `TRUE_FALSE` - Simple true/false questions
- `MIXED` - Combination of different question types in one quiz

## Difficulty Levels

Three difficulty levels are supported:

1. **BEGINNER**
   - Basic, commonly used slang terms
   - Suitable for users new to Gen Z slang

2. **INTERMEDIATE**
   - More nuanced terms
   - Requires deeper understanding of context

3. **ADVANCED**
   - Niche or emerging slang terms
   - For experienced users seeking challenge

Quiz-eligible terms are filtered by difficulty level when retrieved from the lexicon.

## API Endpoints

### Stateless Per-Question API (New - Recommended)

The new stateless API provides a simpler, more flexible quiz experience. Users can start answering questions immediately without specifying a question count, and can exit the quiz at any time while maintaining progress.

#### GET `/quiz/question`

**Purpose:** Get the next question for the current session (creates session if none exists)

**Query Parameters:**
- `difficulty` (optional): `beginner` | `intermediate` | `advanced` (default: `beginner`)

**Response:** `QuizQuestionResponse`
```json
{
  "session_id": "session_abc123",
  "question": {
    "question_id": "q_xyz789",
    "slang_term": "bussin",
    "question_text": "What does 'bussin' mean?",
    "options": [
      {"id": "a", "text": "Really good"},
      {"id": "b", "text": "Bad"},
      {"id": "c", "text": "Okay"},
      {"id": "d", "text": "Average"}
    ],
    "context_hint": "That pizza was bussin!"
  }
}
```

**Behavior:**
- Checks free tier daily question limit before returning question
- Creates new session if none exists or previous session expired (>15 min inactive)
- Uses existing session if still active
- Validates user eligibility (free tier limits)
- Returns single question - client requests next question when ready

**Answer Formatting:**
- All options are normalized (first meaning extracted, consistent capitalization)
- Wrong options avoid duplicates across session
- Formatting matches correct answer style for fair challenge

#### POST `/quiz/answer`

**Purpose:** Submit answer for one question and receive immediate feedback

**Request Body:** `QuizAnswerRequest`
```json
{
  "session_id": "session_abc123",
  "question_id": "q_xyz789",
  "selected_option": "a",
  "time_taken_seconds": 5.2
}
```

**Response:** `QuizAnswerResponse`
```json
{
  "is_correct": true,
  "points_earned": 8.5,
  "explanation": "Really good",
  "running_stats": {
    "questions_answered": 1,
    "correct_count": 1,
    "total_score": 8.5,
    "accuracy": 1.0,
    "time_spent_seconds": 5.2
  }
}
```

**Behavior:**
- Validates session exists and belongs to user
- Validates session is still active (not expired >15 min)
- Compares answer to server-stored correct answer (never sent to client)
- Calculates points using per-question time-based scoring
- Updates session statistics in real-time
- Increments daily question count
- Returns immediate feedback with running totals

**Per-Question Scoring:**
- Max points: 10 (configurable)
- Time decay: Points decrease linearly as time increases
- Formula: `points = max_points * (1.0 - time_ratio * 0.9)` where `time_ratio = min(time_taken / 30s, 1.0)`
- Minimum: 1 point even if timer expires
- Incorrect answers: 0 points

#### GET `/quiz/progress`

**Purpose:** Get current session progress statistics

**Query Parameters:**
- `session_id` (required): Current quiz session ID

**Response:** `QuizSessionProgress`
```json
{
  "questions_answered": 5,
  "correct_count": 4,
  "total_score": 35.5,
  "accuracy": 0.8,
  "time_spent_seconds": 245.3
}
```

**Use Cases:**
- Display progress during quiz
- Show running score and accuracy
- Check time spent
- Update UI after each question

#### POST `/quiz/end`

**Purpose:** End current quiz session and receive final results

**Request Body:** `QuizEndRequest`
```json
{
  "session_id": "session_abc123"
}
```

**Response:** `QuizResult`
```json
{
  "session_id": "session_abc123",
  "score": 35.5,
  "total_possible": 50.0,
  "correct_count": 4,
  "total_questions": 5,
  "time_taken_seconds": 245.3,
  "share_text": "I scored 36/50 on the Lingible Slang Quiz! I got 4/5 right (80% accuracy). Can you beat me? 🔥"
}
```

**Behavior:**
- Validates session exists and belongs to user
- Requires at least one question answered
- Marks session as completed
- Saves results to history (for lifetime stats tracking)
- Calculates final statistics
- Returns final results with shareable text

### Session Management

**Session Storage** (DynamoDB):
- Partition Key: `USER#{user_id}`
- Sort Key: `SESSION#{session_id}`
- GSI6: `SESSION#{session_id}` for fast lookup
- TTL: `expires_at` field (24 hours) - auto-cleanup by DynamoDB

**Session Data:**
- `session_id`: Unique session identifier
- `user_id`: Owner of session
- `difficulty`: Quiz difficulty level
- `questions_answered`: Current count
- `correct_count`: Correct answers so far
- `total_score`: Running point total
- `correct_answers`: Dict mapping `question_id` → correct option (a/b/c/d) - server-side only
- `term_names`: Dict mapping `question_id` → slang_term (for explanations)
- `used_wrong_options`: List of normalized wrong options already used (prevents duplicates)
- `status`: `active` | `completed` | `expired`
- `started_at`: Session start timestamp
- `last_activity`: Last activity timestamp (for expiration check)
- `expires_at`: TTL timestamp (24 hours for auto-cleanup)

**Session Rules:**
- One active session per user (get_active_quiz_session enforces this)
- Auto-expire if `last_activity` > 15 minutes (prevents stale sessions)
- User can explicitly end session anytime via `/quiz/end`
- New question request after expiration auto-creates new session
- Sessions expire via TTL after 24 hours (automatic DynamoDB cleanup)

### Free Tier Limits (Updated)

**Per-Day Question Limits** (not per quiz):
- Free tier: Limited to `free_daily_limit` questions per day (default: 3)
- Premium tier: Unlimited questions
- Limit checked before each question (`GET /quiz/question`)
- Incremented after each answer (`POST /quiz/answer`)
- User can complete in-progress session even if limit reached mid-quiz
- New question requests blocked once limit reached

## Scoring System

### Stateless API Scoring (Per-Question, Time-Based)

**Time-Based Point Decay:**
- Maximum points per question: 10 (configurable via `QuizConfig.points_per_correct`)
- Question time limit: 30 seconds (per question)
- Starting points: 10
- Points decrease linearly as time increases
- Minimum points: 1 (even if timer expires)

**Formula:**
```python
time_ratio = min(time_taken_seconds / 30.0, 1.0)
points_earned = max_points * (1.0 - time_ratio * 0.9)  # 90% decay, 10% minimum
if is_correct:
    return max(1.0, points_earned)
else:
    return 0.0
```

**Examples:**
- Fast answer (5s): ~8.5 points
- Medium answer (15s): ~5.5 points
- Slow answer (25s): ~2.5 points
- Timer expires (30s+): 1 point minimum
- Incorrect: 0 points

**Running Total:**
- Tracked in session (`total_score` field)
- Updated after each answer
- Shown in answer response (`running_stats.total_score`)
- Shown in progress endpoint

## Data Models

### Request Models
- `QuizAnswerRequest` - Submit answer for one question
- `QuizEndRequest` - End quiz session

### Response Models (All inherit from `LingibleBaseModel`)
- `QuizHistory` - User statistics and eligibility
- `QuizQuestionResponse` - Single question with session info
- `QuizAnswerResponse` - Immediate answer feedback with running stats
- `QuizSessionProgress` - Current session progress statistics
- `QuizResult` - Final quiz results with summary
- `QuizQuestion` - Individual question with options
- `QuizOption` - Answer option (a, b, c, d)

### Enum Types
- `QuizDifficulty`: `BEGINNER` | `INTERMEDIATE` | `ADVANCED`
- `QuizCategory`: Approval, Disapproval, Emotion, Food, Appearance, Social, Authenticity, Intensity, General

## Configuration

### QuizConfig
Stored in AWS Systems Manager Parameter Store, accessible via `ConfigService`:

```python
class QuizConfig:
    free_daily_limit: int = 3              # Free user daily quiz limit
    premium_unlimited: bool = True         # Premium users unlimited
    questions_per_quiz: int = 10           # Default question count
    time_limit_seconds: int = 60            # Total time limit per quiz
    points_per_correct: int = 10           # Points per correct answer
    enable_time_bonus: bool = True         # Enable time-based bonuses
```

## Data Persistence

### Quiz History
Stored in DynamoDB (`lingible-users-dev/prod` table):
- Partition Key: `USER#{user_id}`
- Sort Key: `QUIZ#{date}#{challenge_id}`
- Tracks: score, correct_count, time_taken, difficulty, challenge_type

### Daily Question Count (Updated for Stateless API)
Tracked per user per day:
- **Changed**: Now tracks questions answered (not quizzes taken)
- Used to enforce free user daily limits per question
- Incremented after each answer submission (`POST /quiz/answer`)
- Reset at midnight UTC
- Allows users to complete in-progress sessions even if limit reached mid-quiz

### Quiz Statistics (Per Term)
Tracked in `lingible-slang-terms-dev/prod` table:
- `times_in_quiz`: Number of times term appeared in quizzes
- `quiz_accuracy_rate`: User accuracy percentage for this term
- `last_used_at`: Last time term was used in a quiz

Used for:
- Identifying commonly confused terms
- Prioritizing terms for quiz generation
- Future: Adaptive difficulty based on user performance

## Answer Validation & Security

### Stateless API Validation

**Server-Side Answer Storage:**
- Correct answers stored in DynamoDB session (never sent to client)
- Format: `correct_answers[question_id] = option_id` (a/b/c/d after shuffling)
- Term names stored for explanations: `term_names[question_id] = slang_term`
- Validation occurs server-side on answer submission

**Security Features:**
- Correct answers never exposed to client
- Question IDs are UUIDs (non-predictable)
- Session ownership validated (user_id must match)
- Session expiration checked (>15 min inactive = expired)
- Session status validated (must be "active")

**Validation Process:**
1. Question generation: Server shuffles options, determines correct option ID
2. Storage: Correct option ID stored in session `correct_answers` dict
3. Client display: Only question and options sent (no correct answer)
4. Answer submission: Client sends selected option
5. Validation: Server compares to stored correct answer
6. Feedback: Server returns is_correct, points, explanation

### Stateless API Session Validation

Sessions are stored in DynamoDB for validation:
- Key: `USER#{user_id}` / `SESSION#{session_id}`
- Stores: `user_id`, `correct_answers`, `term_names`, `used_wrong_options`, `status`, `last_activity`
- TTL: 24 hours (automatic cleanup via DynamoDB TTL)
- Cleanup: Automatically removed after submission or expiration

**Why DynamoDB?**
- Persistent storage across Lambda invocations
- TTL-based automatic cleanup
- Prevents replay attacks (session expires)
- Ensures user owns the session
- Scalable across multiple Lambda instances

## Wrong Answer Generation & Formatting

The service uses **category-based wrong answer pools** stored in DynamoDB for efficient, varied question generation.

### Category-Based Wrong Answer Pools (Primary Method)

**Storage:**
- One pool record per quiz category (9 categories total)
- Each pool contains 50-100 curated wrong answer strings
- Stored in DynamoDB: `PK: QUIZPOOL#{category}`, `SK: CATEGORY#{category}`
- Loaded once per Lambda instance and cached in-memory

**Benefits:**
- **99% Storage Reduction**: 9 pool records vs ~1,500 per-term fields
- **Better Variety**: 50-100 options per category (vs 3 per term)
- **Faster Performance**: O(1) in-memory lookup (vs O(20) DynamoDB queries)
- **Consistent Quality**: Curated options ensure educational value

**Selection Process:**
1. Get category pool from in-memory cache
2. Filter out correct answer and already-used options
3. Shuffle remaining options and randomly select 3
4. Normalize all selected options (sentence case)

### Answer Normalization

**Consistent Formatting:**
- All options (correct and wrong) are normalized for fair challenge
- Extracts first meaning before semicolon: `"Really good; awesome"` → `"Really good"`
- Standardizes capitalization: Sentence case (first letter uppercase, rest lowercase)
- Example: `"really good"` → `"Really good"`, `"REALLY GOOD"` → `"Really good"`

**Duplicate Prevention:**
- Tracks used wrong options across session (`used_wrong_options` list in session)
- Avoids repeating wrong options within same session
- Filters out correct answer from wrong options pool
- Normalizes all options before comparison

### Fallback: Dynamic Generation

If category pool doesn't have enough available options:
1. Query similar terms from same category (GSI3)
2. Use their meanings as wrong options
3. Fall back to generic vocabulary (40+ hardcoded options)
4. Ensures at least 3 wrong options are always available

**Format Consistency:**
- Correct answers: Normalized to sentence case
- Wrong answers: Normalized to match correct answer format
- Length matching: Options chosen to have similar structure
- Style matching: Avoids "Really good" vs "bad" mismatches

## Frontend Integration

### Stateless API Flow (Recommended)

**Simplified User Experience:**
- No upfront question count selection
- Start answering immediately
- Exit anytime (progress saved)
- See running stats after each question

**Typical Flow:**
1. User taps "Start Quiz" (no question count asked)
2. `GET /quiz/question` → Receives first question + `session_id`
3. User selects answer → Timer tracks per-question time
4. `POST /quiz/answer` → Immediate feedback + running stats
5. Repeat steps 2-4 (next question, answer, feedback)
6. Optional: `GET /quiz/progress` to check stats anytime
7. User exits → `POST /quiz/end` → Final results saved

**Benefits:**
- More flexible: User controls quiz length
- Real-time feedback: Know score and accuracy immediately
- Progress tracking: Can pause and resume (within 15 min)
- No stuck users: Can exit anytime

### State Management

**Stateless API State:**
- `session_id`: Current quiz session
- `current_question`: Latest question from API
- `running_stats`: Progress statistics
- `selected_answers`: Map of `question_id` → selected option
- Per-question timers: Track time for scoring


## Error Handling

### Common Errors

1. **InsufficientPermissionsError (403)**
   - Daily limit reached for free users
   - Message: "Daily limit of 3 quizzes reached. Upgrade to Premium for unlimited quizzes!"

2. **ValidationError (422)**
   - Not enough terms available for difficulty level
   - Invalid or expired challenge ID
   - Challenge doesn't belong to user
   - Challenge expired (>1 hour)

3. **SystemError (500)**
   - Database operation failures
   - Service initialization errors

## Security Considerations

1. **Challenge Ownership Validation**
   - Each challenge cached with `user_id`
   - Submission validates challenge belongs to user
   - Prevents answer sharing between users

2. **Challenge Expiration**
   - 1-hour expiration prevents stale challenges
   - Forces fresh challenge generation
   - Reduces replay attack surface

3. **Authentication Required**
   - All endpoints protected by API Gateway authorizer
   - User ID extracted from Cognito JWT token
   - No anonymous quiz access

## Performance Optimizations

1. **In-Memory Challenge Cache**
   - Fast validation (no database lookup)
   - Auto-expires after 1 hour
   - Cleans up after submission

2. **Bulk Term Retrieval**
   - Retrieves 3x question count for variety
   - Randomly samples from larger pool
   - Ensures diverse question sets

3. **Efficient Statistics Tracking**
   - Updates term statistics incrementally
   - Uses DynamoDB update expressions
   - No full table scans

## Future Enhancements

### Planned Features

1. **Additional Quiz Types**
   - **Decode Message**: User decodes a sentence containing multiple slang terms
   - **True/False**: Simple binary questions
   - **Fill in the Blank**: Complete sentences with slang terms
   - **Mixed Mode**: Combination of different types

2. **Adaptive Difficulty**
   - Adjust difficulty based on user performance history
   - Personalize question selection
   - Track weak areas and focus quizzes

3. **Social Features**
   - Leaderboards (daily, weekly, all-time)
   - Friend challenges
   - Share results with shareable URLs
   - Quiz of the day (all users same quiz)

4. **Enhanced Analytics**
   - Detailed performance breakdowns
   - Learning progress tracking
   - Weak term identification
   - Study recommendations

5. **Gamification Enhancements**
   - Achievements/badges
   - Streaks (daily quiz completion)
   - Levels/progression system
   - Unlockable content

6. **Question Improvements**
   - Image-based questions (show meme, identify slang)
   - Audio questions (pronunciation challenges)
   - Video context (real-world usage examples)
   - Multiple correct answers (synonyms)

7. **Advanced Scoring**
   - Difficulty multipliers (harder questions worth more)
   - Streak bonuses
   - Perfect quiz bonuses
   - Weekly challenges with special rewards

8. **Personalization**
   - Category-based quizzes (focus on specific interests)
   - Review mode (practice previously missed terms)
   - Spaced repetition algorithm
   - Custom quiz creation

9. **Offline Support**
   - Download quiz challenges for offline play
   - Sync results when online
   - Cached term definitions

10. **Learning Paths**
    - Structured curriculum
    - Beginner → Intermediate → Advanced progression
    - Unlock advanced content through mastery

## Testing

### Test Coverage

- **Handler Tests** (`test_quiz_handlers.py`): 17 tests covering all API endpoints
- **Service Tests** (`test_quiz_service.py`): Comprehensive business logic tests
- **Model Tests** (`test_utils.py`): Serialization and response format tests

### Key Test Scenarios

1. Eligibility checking (free vs premium users)
2. Challenge generation with different difficulties
3. Scoring calculations (base + time bonus)
4. Challenge validation and expiration
5. Wrong answer generation edge cases
6. Statistics tracking accuracy
7. Model serialization (all response models)

## Monitoring and Observability

### Business Events Logged

1. **quiz_challenge_generated**
   - `user_id`, `challenge_id`, `difficulty`, `question_count`

2. **quiz_completed**
   - `user_id`, `score`, `correct_count`, `total_questions`

### Error Tracking

All errors are logged with:
- Error type and message
- User ID (when available)
- Request ID for tracing
- Context (operation, parameters)

## API Contract

All endpoints follow RESTful conventions:
- **GET** for retrieving data (history, challenge)
- **POST** for submitting data (answers)
- Consistent error response format
- JSON request/response bodies
- Standard HTTP status codes

### Response Wrapping

All successful responses are wrapped by `api_handler` decorator:
```json
{
  "success": true,
  "data": { /* model data */ }
}
```

Error responses:
```json
{
  "success": false,
  "error": {
    "message": "Error message",
    "code": "ERROR_CODE",
    "status_code": 422
  }
}
```

## Configuration Management

Quiz configuration is stored in AWS Systems Manager Parameter Store:
- Environment-specific (dev/prod)
- Accessed via `ConfigService`
- Type-safe Pydantic models
- Easy to update without code changes

## Summary

The Lingible Quiz Service provides a robust, scalable gamified learning experience for Gen Z slang. It balances user engagement (time bonuses, progress tracking) with educational value (detailed explanations, adaptive difficulty). The architecture is designed for extensibility, allowing new quiz types and features to be added without major refactoring.

Key strengths:
- ✅ Strongly typed models (Pydantic)
- ✅ Comprehensive error handling
- ✅ Efficient caching strategy
- ✅ Flexible scoring system
- ✅ Extensible quiz type architecture
- ✅ User tier-based access control
- ✅ Detailed analytics and statistics

The service is production-ready and provides a solid foundation for future gamification enhancements.
