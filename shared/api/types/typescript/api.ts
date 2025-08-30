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

// Health Check
export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  service: string;
  version: string;
}

// Translation Types
export interface TranslationRequest {
  text: string;
  source_language: string;
  target_language: string;
  context?: string;
}

export interface TranslationResponse {
  id: string;
  original_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  confidence: number;
  created_at: string;
}

export interface TranslationHistoryResponse {
  translations: TranslationResponse[];
  pagination: PaginationInfo;
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
  tier: UserTier;
  status: UserStatus;
  created_at: string;
  updated_at: string;
}

export type UserTier = 'free' | 'premium';
export type UserStatus = 'active' | 'cancelled' | 'suspended';

// Usage Types
export interface UsageResponse {
  current_period: UsagePeriod;
  limits: UsageLimits;
}

export interface UsagePeriod {
  translations_used: number;
  translations_limit: number;
  period_start: string;
  period_end: string;
}

export interface UsageLimits {
  free_tier: number;  // Daily translations for free tier
  premium_tier: number;  // Daily translations for premium tier
}

// Subscription Types
export interface UpgradeRequest {
  platform: 'apple' | 'google';
  receipt_data: string;
}

export interface UpgradeResponse {
  success: boolean;
  tier: 'premium';
  expires_at: string;
}

// Success Response
export interface SuccessResponse {
  success: boolean;
  message: string;
}

// API Endpoints
export const API_ENDPOINTS = {
  HEALTH: '/health',
  TRANSLATE: '/translate',
  TRANSLATIONS: '/translations',
  TRANSLATION_BY_ID: (id: string) => `/translations/${id}`,
  USER_PROFILE: '/user/profile',
  USER_USAGE: '/user/usage',
  USER_UPGRADE: '/user/upgrade',
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
