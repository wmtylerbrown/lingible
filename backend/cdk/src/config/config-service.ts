import * as fs from 'fs';
import * as path from 'path';
import { BackendConfig, InfrastructureConfig } from './types';

export class ConfigService {
  public constructor(private readonly projectRoot: string) {}

  public loadBackendConfig(environment: string): BackendConfig {
    return this.loadConfig<BackendConfig>('shared/config/backend', environment);
  }

  public loadInfrastructureConfig(environment: string): InfrastructureConfig {
    return this.loadConfig<InfrastructureConfig>('shared/config/infrastructure', environment);
  }

  private loadConfig<T>(relativePath: string, environment: string): T {
    const configPath = path.join(this.projectRoot, relativePath, `${environment}.json`);
    const fileContents = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(fileContents) as T;
  }
}
