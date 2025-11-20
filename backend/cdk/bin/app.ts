import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as path from 'path';
import { BackendStack } from '../src/stacks/backend-stack';
import { WebsiteStack } from '../src/stacks/website-stack';
import { DeploymentEnvironment, EnvironmentContext } from '../src/types';
import { ConfigService } from '../src/config/config-service';

const app = new cdk.App();

const environment = (app.node.tryGetContext('environment') ?? 'dev') as DeploymentEnvironment;
const projectName = app.node.tryGetContext('projectName') ?? 'Lingible';
const stackSuffix = environment.charAt(0).toUpperCase() + environment.slice(1);

const projectRoot = path.resolve(process.cwd(), '..', '..');
const configService = new ConfigService(projectRoot);
const envContext: EnvironmentContext = {
  environment,
  projectName,
  backend: configService.loadBackendConfig(environment),
  infrastructure: configService.loadInfrastructureConfig(environment),
};

// Combined backend stack (Shared, Data, Async, Api) - deployed as one stack to avoid cross-stack reference issues
const backendStack = new BackendStack(app, `${projectName}-${stackSuffix}-Backend`, {
  envContext,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

const websiteStack = new WebsiteStack(app, `${projectName}-${stackSuffix}-Website`, {
  envContext,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
// WebsiteStack is independent, no dependencies
