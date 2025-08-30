#!/usr/bin/env ts-node

import { ConfigLoader } from './utils/config-loader';
import * as path from 'path';

async function testConfigLoader() {
  try {
    const projectRoot = path.join(__dirname, '../..');
    const configLoader = new ConfigLoader(projectRoot);

    console.log('Testing Config Loader...\n');

    // Test loading app config
    console.log('1. Loading app config:');
    const appConfig = configLoader.loadAppConfig();
    console.log('   App name:', appConfig.app.name);
    console.log('   Bundle ID:', appConfig.app.bundle_id);
    console.log('   Version:', appConfig.app.version);
    console.log('   Description:', appConfig.app.description);

    // Test loading environment configs
    console.log('\n2. Loading environment configs:');

    const devConfig = configLoader.loadEnvironmentConfig('dev');
    console.log('   Dev environment:', devConfig.environment);
    console.log('   Dev API URL:', devConfig.api.base_url);
    console.log('   Dev Apple Client ID:', devConfig.apple.clientId);

    const prodConfig = configLoader.loadEnvironmentConfig('prod');
    console.log('   Prod environment:', prodConfig.environment);
    console.log('   Prod API URL:', prodConfig.api.base_url);
    console.log('   Prod Apple Client ID:', prodConfig.apple.clientId);

    // Test Lambda config generation
    console.log('\n3. Testing Lambda config generation:');

    const devLambdaConfig = configLoader.getLambdaConfig('dev');
    console.log('   Dev usage limits:', JSON.stringify(devLambdaConfig.usage_limits, null, 2));
    console.log('   Dev translation config:', JSON.stringify(devLambdaConfig.translation, null, 2));

    const prodLambdaConfig = configLoader.getLambdaConfig('prod');
    console.log('   Prod usage limits:', JSON.stringify(prodLambdaConfig.usage_limits, null, 2));
    console.log('   Prod translation config:', JSON.stringify(prodLambdaConfig.translation, null, 2));

    // Test Apple credentials
    console.log('\n4. Testing Apple credentials:');

    const devAppleCreds = configLoader.getAppleCredentials('development');
    console.log('   Dev Apple credentials:', JSON.stringify(devAppleCreds, null, 2));

    const prodAppleCreds = configLoader.getAppleCredentials('production');
    console.log('   Prod Apple credentials:', JSON.stringify(prodAppleCreds, null, 2));

    console.log('\n✅ Config loader test completed successfully!');

  } catch (error) {
    console.error('❌ Config loader test failed:', error);
    process.exit(1);
  }
}

testConfigLoader();
