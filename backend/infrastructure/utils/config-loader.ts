import * as fs from 'fs';
import * as path from 'path';

// Backend configuration (what Python Lambda uses)
export interface BackendConfig {
  environment: string;
  bedrock: {
    model: string;
    max_tokens: number;
    temperature: number;
  };
  limits: {
    free_daily_translations: number;
    premium_daily_translations: number;
    free_max_text_length: number;
    premium_max_text_length: number;
    free_history_retention_days: number;
    premium_history_retention_days: number;
  };
  security: {
    sensitive_field_patterns: string[];
  };
  observability: {
    log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
    enable_tracing: boolean;
  };
}

// Infrastructure configuration (what CDK uses)
export interface InfrastructureConfig {
  environment: string;
  aws: {
    region: string;
  };
  bedrock: {
    region: string;
  };
  tables: {
    users_table: { name: string };
    translations_table: { name: string };
    trending_table: { name: string };
  };
  apple: {
    client_id: string;
    team_id: string;
    key_id: string;
    in_app_purchase_key_id: string;
    bundle_id: string;
    issuer_id: string;
  };
  api: {
    base_url: string;
    cors_origins: string[];
  };
}

// iOS configuration (what iOS app uses)
export interface IOSConfig {
  environment: string;
  bundle_identifier: string;
  display_name: string;
  api_base_url: string;
  website_base_url: string;
  support_email: string;
  admob: {
    application_identifier: string;
    banner_ad_unit_id: string;
    interstitial_ad_unit_id: string;
  };
}

export class ConfigLoader {
  private readonly projectRoot: string;

  constructor(projectRoot: string) {
    this.projectRoot = projectRoot;
  }

  /**
   * Load backend configuration for Python Lambda functions
   */
  public loadBackendConfig(environment: string): BackendConfig {
    const configPath = path.join(this.projectRoot, 'shared', 'config', 'backend', `${environment}.json`);
    const configContent = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(configContent);
  }

  /**
   * Load infrastructure configuration for CDK
   */
  public loadInfrastructureConfig(environment: string): InfrastructureConfig {
    const configPath = path.join(this.projectRoot, 'shared', 'config', 'infrastructure', `${environment}.json`);
    const configContent = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(configContent);
  }

  /**
   * Load iOS configuration for iOS app
   */
  public loadIOSConfig(environment: string): IOSConfig {
    const configPath = path.join(this.projectRoot, 'shared', 'config', 'ios', `${environment}.json`);
    const configContent = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(configContent);
  }

  /**
   * Get merged configuration for CDK (infrastructure + backend model)
   */
  public getMergedConfig(environment: string): InfrastructureConfig & { bedrock: { model: string } } {
    const infrastructureConfig = this.loadInfrastructureConfig(environment);
    const backendConfig = this.loadBackendConfig(environment);

    return {
      ...infrastructureConfig,
      bedrock: {
        ...infrastructureConfig.bedrock,
        model: backendConfig.bedrock.model  // Get model from backend config
      }
    };
  }

  // Legacy methods for backwards compatibility
  /**
   * @deprecated Use loadInfrastructureConfig instead
   */
  public loadEnvironmentConfig(environment: string): InfrastructureConfig {
    return this.loadInfrastructureConfig(environment);
  }
}
