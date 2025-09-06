// Lingible API Type Definitions
// Shared TypeScript types for API requests and responses

// Base API Response
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
}

// API Error
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// Error Response (matches backend ErrorResponse model)
export interface ErrorResponse {
  success: false;
  message: string;
  error_code: string;
  status_code: number;
  details?: Record<string, any>;
  timestamp: Date;
}

// Health Check
export interface HealthResponse {
  status: string;
}

// Translation Types
export type TranslationDirection = 'english_to_genz' | 'genz_to_english';

export interface TranslationRequest {
  text: string;
  direction: TranslationDirection;
}

export interface TranslationResponse {
  translation_id: string;
  original_text: string;
  translated_text: string;
  direction: TranslationDirection;
  confidence_score?: number;
  created_at: Date;
  processing_time_ms?: number;
  model_used?: string;
}

export interface TranslationHistoryItemResponse {
  translation_id: string;
  user_id: string;
  original_text: string;
  translated_text: string;
  direction: TranslationDirection;
  confidence_score?: number;
  created_at: Date;
  model_used?: string;
}

export interface TranslationHistoryResponse {
  translations: TranslationHistoryItemResponse[];
  total_count: number;
  has_more: boolean;
}

export interface PaginationInfo {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// User Types
export interface UserProfileResponse {
  user_id: string;
  email: string;
  username: string;
  tier: UserTier;
  status: UserStatus;
  created_at: Date;
  updated_at: Date;
}

export type UserTier = 'free' | 'premium';
export type UserStatus = 'active' | 'cancelled' | 'suspended';

// Usage Types
export interface UsageResponse {
  tier: UserTier;
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  reset_date: string; // ISO format
  current_max_text_length: number;
  free_tier_max_length: number;
  premium_tier_max_length: number;
  free_daily_limit: number;
  premium_daily_limit: number;
}

export interface UsageLimits {
  free_tier: number;  // Daily translations for free tier
  premium_tier: number;  // Daily translations for premium tier
}

// Subscription Types
export interface UpgradeRequest {
  platform: 'apple' | 'google';
  receipt_data: string;
  transaction_id: string;
}

export interface UpgradeResponse {
  success: boolean;
  tier: 'premium';
  expires_at: string;
}

// Trending Types
export type TrendingCategory = 'slang' | 'meme' | 'expression' | 'hashtag' | 'phrase';

export interface TrendingTermResponse {
  term: string;
  definition: string;
  category: TrendingCategory;
  popularity_score: number;
  search_count: number; // 0 for free users, actual count for premium
  translation_count: number; // 0 for free users, actual count for premium
  first_seen: Date;
  last_updated: Date;
  is_active: boolean;
  example_usage?: string; // null for free users, actual examples for premium
  origin?: string; // null for free users, actual origin for premium
  related_terms: string[]; // empty for free users, actual terms for premium
}

export interface TrendingListResponse {
  terms: TrendingTermResponse[];
  total_count: number;
  last_updated: Date;
  category_filter?: TrendingCategory;
}

// Success Response
export interface SuccessResponse {
  success: boolean;
  message: string;
}

// Apple Webhook Types
export type AppleNotificationType =
  | 'INITIAL_BUY'
  | 'RENEWAL'
  | 'CANCEL'
  | 'INTERACTIVE_RENEWAL'
  | 'DID_CHANGE_RENEWAL_PREF'
  | 'DID_CHANGE_RENEWAL_STATUS'
  | 'PRICE_INCREASE_CONSENT'
  | 'REFUND'
  | 'FAILED_PAYMENT'
  | 'REFUND_DECLINED'
  | 'CONSUMPTION_REQUEST';

export type Environment = 'sandbox' | 'production';

export interface AppleWebhookRequest {
  notification_type: AppleNotificationType;
  transaction_id: string;
  receipt_data: string;
  environment?: Environment;
}

export interface WebhookResponse {
  success: boolean;
  message: string;
}

// Subscription Types
export type SubscriptionProvider = 'apple' | 'google';
export type SubscriptionStatus = 'active' | 'expired' | 'cancelled';
export type ReceiptValidationStatus = 'valid' | 'invalid' | 'expired' | 'already_used' | 'environment_mismatch' | 'retryable_error';

export interface UserSubscriptionResponse {
  provider: SubscriptionProvider;
  transaction_id: string;
  status: SubscriptionStatus;
  start_date: Date;
  end_date?: Date;
  created_at: Date;
}

export interface ReceiptValidationResponse {
  is_valid: boolean;
  status: ReceiptValidationStatus;
  transaction_id: string;
  product_id?: string;
  purchase_date?: Date;
  expiration_date?: Date;
  environment?: Environment;
  error_message?: string;
  retry_after?: number;
}

// API Endpoints
export const API_ENDPOINTS = {
  HEALTH: '/health',
  TRANSLATE: '/translate',
  TRANSLATIONS: '/translations',
  TRANSLATIONS_DELETE_ALL: '/translations/delete-all',
  TRANSLATION_BY_ID: (id: string) => `/translations/${id}`,
  USER_PROFILE: '/user/profile',
  USER_USAGE: '/user/usage',
  USER_UPGRADE: '/user/upgrade',
  TRENDING: '/trending',
  WEBHOOK_APPLE: '/webhook/apple',
} as const;

// HTTP Methods
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

// API Configuration
export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
  headers?: Record<string, string>;
}

// Request Options
export interface RequestOptions {
  method: HttpMethod;
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
}

// API Client Interface
export interface ApiClient {
  get<T>(endpoint: string, options?: Partial<RequestOptions>): Promise<ApiResponse<T>>;
  post<T>(endpoint: string, data?: any, options?: Partial<RequestOptions>): Promise<ApiResponse<T>>;
  put<T>(endpoint: string, data?: any, options?: Partial<RequestOptions>): Promise<ApiResponse<T>>;
  delete<T>(endpoint: string, options?: Partial<RequestOptions>): Promise<ApiResponse<T>>;
}

// Error Codes
export const ERROR_CODES = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  RATE_LIMIT_EXCEEDED: 'RATE_LIMIT_EXCEEDED',
  INTERNAL_SERVER_ERROR: 'INTERNAL_SERVER_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
} as const;

export type ErrorCode = typeof ERROR_CODES[keyof typeof ERROR_CODES];

// HTTP Status Codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  RATE_LIMIT_EXCEEDED: 429,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
} as const;

export type HttpStatus = typeof HTTP_STATUS[keyof typeof HTTP_STATUS];
