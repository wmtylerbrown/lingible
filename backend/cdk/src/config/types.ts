export interface BackendConfig {
  readonly environment: string;
  readonly llm: {
    readonly model: string;
    readonly max_tokens: number;
    readonly temperature: number;
    readonly top_p: number;
    readonly low_confidence_threshold: number;
  };
  readonly lexicon: {
    readonly s3_bucket: string;
    readonly s3_key: string;
  };
  readonly age_filtering: {
    readonly max_rating: string;
    readonly filter_mode: string;
  };
  readonly limits: {
    readonly free_daily_translations: number;
    readonly premium_daily_translations: number;
    readonly free_max_text_length: number;
    readonly premium_max_text_length: number;
    readonly free_history_retention_days: number;
    readonly premium_history_retention_days: number;
  };
  readonly security: {
    readonly sensitive_field_patterns: string[];
  };
  readonly observability: {
    readonly log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
    readonly enable_tracing: boolean;
  };
  readonly slang_validation: {
    readonly auto_approval_enabled: boolean;
    readonly auto_approval_threshold: number;
    readonly web_search_enabled: boolean;
    readonly max_search_results: number;
  };
  readonly quiz: {
    readonly free_daily_limit: number;
    readonly premium_unlimited: boolean;
    readonly questions_per_quiz: number;
    readonly time_limit_seconds: number;
    readonly points_per_correct: number;
    readonly enable_time_bonus: boolean;
  };
}

export interface InfrastructureConfig {
  readonly environment: string;
  readonly aws: {
    readonly region: string;
  };
  readonly bedrock: {
    readonly region: string;
  };
  readonly tables: {
    readonly users_table: { readonly name: string };
    readonly translations_table: { readonly name: string };
    readonly submissions_table: { readonly name: string };
    readonly lexicon_table: { readonly name: string };
    readonly trending_table: { readonly name: string };
    readonly terms_table?: { readonly name: string };
  };
  readonly apple: {
    readonly client_id: string;
    readonly team_id: string;
    readonly key_id: string;
    readonly in_app_purchase_key_id: string;
    readonly bundle_id: string;
    readonly issuer_id: string;
  };
  readonly api: {
    readonly base_url: string;
    readonly cors_origins: string[];
  };
}
