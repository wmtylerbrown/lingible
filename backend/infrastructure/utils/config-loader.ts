import * as fs from 'fs';
import * as path from 'path';

// App-wide configuration (never changes per environment)
export interface AppConfig {
  app: {
    name: string;
    version: string;
    description: string;
  };
  translation: {
    context: string;
    max_concurrent: number;
    timeout_seconds: number;
  };
  limits: {
    free_daily_translations: number;
    free_max_text_length: number;
    free_history_retention_days: number;
    premium_daily_translations: number;
    premium_max_text_length: number;
    premium_history_retention_days: number;
  };
  security: {
    sensitive_field_patterns: string[];
    bearer_prefix: string;
    jwt_expiration_seconds: number;
  };
  api: {
    cors_headers: string[];
    cors_methods: string[];
    pagination_default: number;
    pagination_max: number;
    timeout_ms: number;
    max_retries: number;
  };
  stores: {
    apple_verify_url: string;
    apple_sandbox_url: string;
    google_api_timeout: number;
  };
}

// Environment-specific configuration (varies per environment)
export interface EnvironmentConfig {
  environment: string;
  aws: {
    region: string;
  };
  bedrock: {
    model: string;
    region: string;
    max_tokens: number;
    temperature: number;
  };
  cognito: {
    user_pool_id: string;
    client_id: string;
  };
  users_table: {
    name: string;
    read_capacity: number;
    write_capacity: number;
  };
  translations_table: {
    name: string;
    read_capacity: number;
    write_capacity: number;
  };
  apple: {
    client_id: string;
    team_id: string;
    key_id: string;
    bundle_id: string;
    environment: 'sandbox' | 'production';
    shared_secret: string;
  };
  google: {
    package_name: string;
    service_account_key: string;
  };
  api: {
    base_url: string;
    cors_origins: string[];
  };
  observability: {
    debug_mode: boolean;
    log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
    enable_metrics: boolean;
    enable_tracing: boolean;
    log_retention_days: number;
    service_name: string;
  };
}

// Merged configuration (app + environment)
export interface MergedConfig extends AppConfig, EnvironmentConfig {
  // Inherits all properties from both AppConfig and EnvironmentConfig
}

export class ConfigLoader {
  private readonly projectRoot: string;

  constructor(projectRoot: string) {
    this.projectRoot = projectRoot;
  }

  /**
   * Deep merge two objects, with source values overriding target values
   */
  private deepMerge<T extends Record<string, any>>(target: T, source: Partial<T>): T {
    const result = { ...target };

    for (const key in source) {
      if (source.hasOwnProperty(key)) {
        const sourceValue = source[key];
        const targetValue = result[key];

        if (sourceValue && typeof sourceValue === 'object' && !Array.isArray(sourceValue) &&
            targetValue && typeof targetValue === 'object' && !Array.isArray(targetValue)) {
          // Recursively merge nested objects
          result[key] = this.deepMerge(targetValue, sourceValue);
        } else {
          // Override with source value (including arrays)
          result[key] = sourceValue;
        }
      }
    }

    return result;
  }

  public loadAppConfig(): AppConfig {
    const configPath = path.join(this.projectRoot, 'shared', 'config', 'app.json');
    const configContent = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(configContent);
  }

  public loadEnvironmentConfig(environment: string): EnvironmentConfig {
    // Map environment names to file names
    const envMap: Record<string, string> = {
      'development': 'dev',
      'production': 'prod',
      'dev': 'dev',
      'prod': 'prod'
    };

    const envFile = envMap[environment] || environment;
    const configPath = path.join(this.projectRoot, 'shared', 'config', 'environments', `${envFile}.json`);
    const configContent = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(configContent);
  }

  /**
   * Get merged configuration (app + environment) with proper deep merging
   */
  public getMergedConfig(environment: string): MergedConfig {
    const appConfig = this.loadAppConfig();
    const envConfig = this.loadEnvironmentConfig(environment);

    // Start with app config as base and deep merge environment overrides
    const merged = this.deepMerge(appConfig as any, envConfig as any);

    return merged as MergedConfig;
  }

  // Specific config getters for convenience
  public getAppConfig(): AppConfig['app'] {
    const appConfig = this.loadAppConfig();
    return appConfig.app;
  }

  public getBedrockConfig(environment: string): EnvironmentConfig['bedrock'] {
    const envConfig = this.loadEnvironmentConfig(environment);
    return envConfig.bedrock;
  }

  public getCognitoConfig(environment: string): EnvironmentConfig['cognito'] {
    const envConfig = this.loadEnvironmentConfig(environment);
    return envConfig.cognito;
  }

  public getUsersTableConfig(environment: string): EnvironmentConfig['users_table'] {
    const envConfig = this.loadEnvironmentConfig(environment);
    return envConfig.users_table;
  }

  public getTranslationsTableConfig(environment: string): EnvironmentConfig['translations_table'] {
    const envConfig = this.loadEnvironmentConfig(environment);
    return envConfig.translations_table;
  }

  public getAppleConfig(environment: string): EnvironmentConfig['apple'] {
    const envConfig = this.loadEnvironmentConfig(environment);
    return envConfig.apple;
  }

  public getGoogleConfig(environment: string): EnvironmentConfig['google'] {
    const envConfig = this.loadEnvironmentConfig(environment);
    return envConfig.google;
  }

  public getApiConfig(environment: string): AppConfig['api'] & EnvironmentConfig['api'] {
    const merged = this.getMergedConfig(environment);
    return {
      // From app config
      cors_headers: merged.api.cors_headers,
      cors_methods: merged.api.cors_methods,
      pagination_default: merged.api.pagination_default,
      pagination_max: merged.api.pagination_max,
      timeout_ms: merged.api.timeout_ms,
      max_retries: merged.api.max_retries,
      // From environment config
      base_url: merged.api.base_url,
      cors_origins: merged.api.cors_origins
    };
  }

  public getObservabilityConfig(environment: string): EnvironmentConfig['observability'] {
    const envConfig = this.loadEnvironmentConfig(environment);
    return envConfig.observability;
  }

  public getSecurityConfig(environment: string): AppConfig['security'] {
    const appConfig = this.loadAppConfig();
    return appConfig.security;
  }

  public getTranslationConfig(environment: string): AppConfig['translation'] {
    const appConfig = this.loadAppConfig();
    return appConfig.translation;
  }

  public getLimitsConfig(environment: string): AppConfig['limits'] {
    const appConfig = this.loadAppConfig();
    return appConfig.limits;
  }

  public getStoresConfig(environment: string): AppConfig['stores'] {
    const appConfig = this.loadAppConfig();
    return appConfig.stores;
  }

  /**
   * @deprecated Use getMergedConfig and specific getters instead
   */
  public getLambdaConfig(environment: string): Record<string, any> {
    const merged = this.getMergedConfig(environment);

    // Convert to the old format for backwards compatibility
    return {
      app_name: merged.app.name,
      version: merged.app.version,
      environment: merged.environment,

      // Bedrock config
      bedrock: merged.bedrock,

      // Database configs
      users_table: merged.users_table,
      translations_table: merged.translations_table,

      // API config
      api: merged.api,

      // Other configs
      translation: merged.translation,
      limits: merged.limits,
      security: merged.security,
      stores: merged.stores,
      apple: merged.apple,
      google: merged.google,
      observability: merged.observability,
      aws: merged.aws,
      cognito: merged.cognito
    };
  }

  // Legacy methods for backwards compatibility
  /**
   * @deprecated Use getUsersTableConfig instead
   */
  public getDatabaseConfig(environment: string): { users_table: string; translations_table: string } {
    const envConfig = this.loadEnvironmentConfig(environment);
    return {
      users_table: envConfig.users_table.name,
      translations_table: envConfig.translations_table.name
    };
  }

  /**
   * @deprecated Use getAppleConfig instead
   */
  public getAppleCredentials(environment: string): { clientId: string; teamId: string; keyId: string } {
    const envConfig = this.loadEnvironmentConfig(environment);
    return {
      clientId: envConfig.apple.client_id,
      teamId: envConfig.apple.team_id,
      keyId: envConfig.apple.key_id
    };
  }

  /**
   * @deprecated Use getObservabilityConfig instead
   */
  public getLoggingConfig(environment: string): { level: string } {
    const envConfig = this.loadEnvironmentConfig(environment);
    return {
      level: envConfig.observability.log_level
    };
  }

  /**
   * @deprecated Use getObservabilityConfig instead
   */
  public getMonitoringConfig(environment: string): { enable_metrics: boolean } {
    const envConfig = this.loadEnvironmentConfig(environment);
    return {
      enable_metrics: envConfig.observability.enable_metrics
    };
  }

  /**
   * @deprecated Use getObservabilityConfig instead
   */
  public getTracingConfig(environment: string): { enabled: boolean; service_name: string } {
    const envConfig = this.loadEnvironmentConfig(environment);
    return {
      enabled: envConfig.observability.enable_tracing,
      service_name: envConfig.observability.service_name
    };
  }
}
