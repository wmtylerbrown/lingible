import { AsyncResourceReferences, DataResourceReferences, EnvironmentContext } from '../../types';

export const enum EnvGroup {
  Core = 'core',
}

interface EnvironmentBuilderContext {
  readonly ctx: EnvironmentContext;
  readonly data: DataResourceReferences;
  readonly asyncResources?: AsyncResourceReferences;
}

export class LambdaEnvironmentBuilder {
  private readonly ctx: EnvironmentContext;

  private readonly data: DataResourceReferences;

  private readonly asyncResources?: AsyncResourceReferences;

  private readonly envVars: Record<string, string>;

  public constructor(builderContext: EnvironmentBuilderContext) {
    this.ctx = builderContext.ctx;
    this.data = builderContext.data;
    this.asyncResources = builderContext.asyncResources;
    this.envVars = {
      ENVIRONMENT: this.ctx.environment,
      LOG_LEVEL: this.ctx.backend.observability.log_level,
      ENABLE_TRACING: this.ctx.backend.observability.enable_tracing.toString(),
    };
  }

  public includeUsersTable(): this {
    this.envVars.USERS_TABLE = this.data.usersTable.tableName;
    return this;
  }

  public includeTranslationsTable(): this {
    this.envVars.TRANSLATIONS_TABLE = this.data.translationsTable.tableName;
    return this;
  }

  public includeSubmissionsTable(): this {
    this.envVars.SUBMISSIONS_TABLE = this.data.submissionsTable.tableName;
    return this;
  }

  public includeLexiconTable(): this {
    this.envVars.LEXICON_TABLE = this.data.lexiconTable.tableName;
    return this;
  }

  public includeTrendingTable(): this {
    this.envVars.TRENDING_TABLE = this.data.trendingTable.tableName;
    return this;
  }

  public includeAllTables(): this {
    return this.includeUsersTable()
      .includeTranslationsTable()
      .includeSubmissionsTable()
      .includeLexiconTable()
      .includeTrendingTable();
  }

  /**
   * @deprecated Use the specific include*Table helpers instead.
   */
  public includeTables(): this {
    return this.includeAllTables();
  }

  public includeUsageLimits(): this {
    this.envVars.FREE_DAILY_TRANSLATIONS = this.ctx.backend.limits.free_daily_translations.toString();
    this.envVars.PREMIUM_DAILY_TRANSLATIONS = this.ctx.backend.limits.premium_daily_translations.toString();
    this.envVars.FREE_MAX_TEXT_LENGTH = this.ctx.backend.limits.free_max_text_length.toString();
    this.envVars.PREMIUM_MAX_TEXT_LENGTH = this.ctx.backend.limits.premium_max_text_length.toString();
    this.envVars.FREE_HISTORY_RETENTION_DAYS = this.ctx.backend.limits.free_history_retention_days.toString();
    this.envVars.PREMIUM_HISTORY_RETENTION_DAYS = this.ctx.backend.limits.premium_history_retention_days.toString();
    this.envVars.AGE_MAX_RATING = this.ctx.backend.age_filtering.max_rating;
    this.envVars.AGE_FILTER_MODE = this.ctx.backend.age_filtering.filter_mode;
    return this;
  }

  public includeLexicon(): this {
    this.envVars.LEXICON_S3_BUCKET = this.ctx.backend.lexicon.s3_bucket;
    this.envVars.LEXICON_S3_KEY = this.ctx.backend.lexicon.s3_key;
    return this;
  }

  public includeLlm(): this {
    this.envVars.LLM_MODEL_ID = this.ctx.backend.llm.model;
    this.envVars.LLM_MAX_TOKENS = this.ctx.backend.llm.max_tokens.toString();
    this.envVars.LLM_TEMPERATURE = this.ctx.backend.llm.temperature.toString();
    this.envVars.LLM_TOP_P = this.ctx.backend.llm.top_p.toString();
    this.envVars.LLM_LOW_CONFIDENCE_THRESHOLD = this.ctx.backend.llm.low_confidence_threshold.toString();
    return this;
  }

  public includeSecurity(): this {
    this.envVars.SENSITIVE_FIELD_PATTERNS = JSON.stringify(this.ctx.backend.security.sensitive_field_patterns);
    return this;
  }

  public includeSlangValidation(): this {
    this.envVars.SLANG_VALIDATION_AUTO_APPROVAL_ENABLED = this.ctx.backend.slang_validation.auto_approval_enabled.toString();
    this.envVars.SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD = this.ctx.backend.slang_validation.auto_approval_threshold.toString();
    this.envVars.SLANG_VALIDATION_WEB_SEARCH_ENABLED = this.ctx.backend.slang_validation.web_search_enabled.toString();
    this.envVars.SLANG_VALIDATION_MAX_SEARCH_RESULTS = this.ctx.backend.slang_validation.max_search_results.toString();
    return this;
  }

  public includeQuiz(): this {
    this.envVars.QUIZ_FREE_DAILY_LIMIT = this.ctx.backend.quiz.free_daily_limit.toString();
    this.envVars.QUIZ_PREMIUM_UNLIMITED = this.ctx.backend.quiz.premium_unlimited.toString();
    this.envVars.QUIZ_QUESTIONS_PER_QUIZ = this.ctx.backend.quiz.questions_per_quiz.toString();
    this.envVars.QUIZ_TIME_LIMIT_SECONDS = this.ctx.backend.quiz.time_limit_seconds.toString();
    this.envVars.QUIZ_POINTS_PER_CORRECT = this.ctx.backend.quiz.points_per_correct.toString();
    this.envVars.QUIZ_ENABLE_TIME_BONUS = this.ctx.backend.quiz.enable_time_bonus.toString();
    return this;
  }

  public includeApple(): this {
    this.envVars.APPLE_KEY_ID = this.ctx.infrastructure.apple.in_app_purchase_key_id;
    this.envVars.APPLE_ISSUER_ID = this.ctx.infrastructure.apple.issuer_id;
    this.envVars.APPLE_BUNDLE_ID = this.ctx.infrastructure.apple.bundle_id;
    return this;
  }

  public includeSnsTopics(): this {
    if (!this.asyncResources) {
      throw new Error('SNS environment variables requested but async resources not provided');
    }
    this.envVars.SLANG_SUBMISSIONS_TOPIC_ARN = this.asyncResources.slangSubmissionsTopic.topicArn;
    this.envVars.SLANG_VALIDATION_REQUEST_TOPIC_ARN = this.asyncResources.slangValidationRequestTopic.topicArn;
    return this;
  }

  public includeCustom(key: string, value: string): this {
    this.envVars[key] = value;
    return this;
  }

  public includeMany(entries: Record<string, string | undefined>): this {
    Object.entries(entries).forEach(([key, value]) => {
      if (value !== undefined) {
        this.envVars[key] = value;
      }
    });
    return this;
  }

  public build(): Record<string, string> {
    return { ...this.envVars };
  }
}

export function buildLambdaEnvironment(
  ctx: EnvironmentContext,
  data: DataResourceReferences,
  asyncResources?: AsyncResourceReferences
): LambdaEnvironmentBuilder {
  return new LambdaEnvironmentBuilder({ ctx, data, asyncResources });
}
