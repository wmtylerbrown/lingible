#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { LingibleStack } from './stacks/lingible_stack';
import * as fs from 'fs';
import * as path from 'path';

const app = new cdk.App();

// Get environment from context or default to 'dev'
const environment = app.node.tryGetContext('environment') || 'dev';

// Check if we should deploy the full stack or just hosted zones
const deployBackend = app.node.tryGetContext('deploy-backend') !== false; // Default to true

// Load application configuration
let appConfig: any = {};
try {
  const configPath = path.join(__dirname, 'app-config.json');
  const configContent = fs.readFileSync(configPath, 'utf8');
  appConfig = JSON.parse(configContent);
} catch (error) {
  console.warn('⚠️  app-config.json not found or invalid. Using default values.');
  appConfig = {
    dev: { apple: { clientId: 'TO_BE_SET', teamId: 'TO_BE_SET', keyId: 'TO_BE_SET' } },
    prod: { apple: { clientId: 'TO_BE_SET', teamId: 'TO_BE_SET', keyId: 'TO_BE_SET' } }
  };
}

const envConfig = appConfig[environment] || appConfig.dev;
const appleCredentials = envConfig.apple || { clientId: 'TO_BE_SET', teamId: 'TO_BE_SET', keyId: 'TO_BE_SET' };

if (deployBackend) {
  // Full stack deployment (hosted zones + backend)
  new LingibleStack(app, `Lingible-${environment.charAt(0).toUpperCase() + environment.slice(1)}`, {
    description: `Lingible - ${environment.charAt(0).toUpperCase() + environment.slice(1)} Environment`,
    environment: environment,
    appleClientId: appleCredentials.clientId,
    appleTeamId: appleCredentials.teamId,
    appleKeyId: appleCredentials.keyId,
    env: {
      account: app.node.tryGetContext('account') || process.env.CDK_DEFAULT_ACCOUNT,
      region: app.node.tryGetContext('region') || process.env.CDK_DEFAULT_REGION || 'us-east-1',
    },
  });
} else {
  // Hosted zones only deployment
  const { HostedZonesStack } = require('./constructs/hosted_zones_stack');
  new HostedZonesStack(app, `Lingible-${environment.charAt(0).toUpperCase() + environment.slice(1)}-HostedZones`, {
    description: `Lingible Hosted Zones - ${environment.charAt(0).toUpperCase() + environment.slice(1)} Environment`,
    environment: environment,
    env: {
      account: app.node.tryGetContext('account') || process.env.CDK_DEFAULT_ACCOUNT,
      region: app.node.tryGetContext('region') || process.env.CDK_DEFAULT_REGION || 'us-east-1',
    },
  });
}

// Add tags to all resources
cdk.Tags.of(app).add('Application', 'Lingible');
cdk.Tags.of(app).add('Environment', environment);
cdk.Tags.of(app).add('ManagedBy', 'CDK');
