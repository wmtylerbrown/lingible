import * as fs from 'fs';
import * as path from 'path';

export interface AppConfig {
  app: {
    name: string;
    bundle_id: string;
    version: string;
    description: string;
  };
  translation: {
    type: string;
    source_language: string;
    target_language: string;
    context: string;
    directions: {
      genz_to_english: string;
      english_to_genz: string;
    };
    max_concurrent_translations: number;
    translation_timeout: number;
  };
  features: {
    translation_history: {
      free: boolean;
      premium: boolean;
    };
    custom_context: {
      free: boolean;
      premium: boolean;
    };
  };
  subscription: {
    platforms: string[];
    tiers: string[];
  };
  limits: {
    free_tier: {
      daily_translations: number;
      max_text_length: number;
      history_retention_days: number;
    };
    premium_tier: {
      daily_translations: number;
      max_text_length: number;
      history_retention_days: number;
    };
  };
}

export interface EnvironmentConfig {
  environment: string;
  api: {
    base_url: string;
    timeout: number;
    retries: number;
  };
  aws: {
    region: string;
    cognito: {
      user_pool_id: string;
      client_id: string;
    };
  };
  features: {
    debug_mode: boolean;
    analytics: boolean;
    crash_reporting: boolean;
  };
  apple: {
    clientId: string;
    teamId: string;
    keyId: string;
  };
}

export class ConfigLoader {
  private readonly projectRoot: string;

  constructor(projectRoot: string) {
    this.projectRoot = projectRoot;
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

  public getLambdaConfig(environment: string): Record<string, any> {
    const appConfig = this.loadAppConfig();
    const envConfig = this.loadEnvironmentConfig(environment);

    return {
      // App configuration
      app_name: appConfig.app.name,
      bundle_id: appConfig.app.bundle_id,
      version: appConfig.app.version,

      // API configuration
      api_base_url: envConfig.api.base_url,
      api_timeout: envConfig.api.timeout,
      api_retries: envConfig.api.retries,

      // Usage limits (from app config - same for all environments)
      usage_limits: {
        free: {
          daily_limit: appConfig.limits.free_tier.daily_translations,
          max_text_length: appConfig.limits.free_tier.max_text_length
        },
        premium: {
          daily_limit: appConfig.limits.premium_tier.daily_translations,
          max_text_length: appConfig.limits.premium_tier.max_text_length
        }
      },

      // Translation configuration (from app config)
      translation: {
        type: appConfig.translation.type,
        source_language: appConfig.translation.source_language,
        target_language: appConfig.translation.target_language,
        context: appConfig.translation.context,
        directions: appConfig.translation.directions,
        max_concurrent_translations: appConfig.translation.max_concurrent_translations,
        translation_timeout: appConfig.translation.translation_timeout
      },

      // Features (from app config)
      features: appConfig.features,

      // Subscription (from app config)
      subscription: appConfig.subscription
    };
  }

  public getAppleCredentials(environment: string): { clientId: string; teamId: string; keyId: string } {
    const envConfig = this.loadEnvironmentConfig(environment);
    return envConfig.apple;
  }
}
