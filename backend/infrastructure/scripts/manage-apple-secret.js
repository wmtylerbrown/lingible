#!/usr/bin/env node

const readline = require('readline');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

async function getApplePrivateKey() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = (query) => {
    return new Promise((resolve) => {
      rl.question(query, resolve);
    });
  };

  console.log('🔐 Apple Private Key Manager');
  console.log('============================\n');
  console.log('How would you like to provide your Apple Private Key?');
  console.log('1. Paste the key content directly');
  console.log('2. Read from a .p8 file');

  const choice = await question('Enter choice (1 or 2): ');

  if (choice === '2') {
    const keyFilePath = await question('Enter path to your .p8 file: ');
    rl.close();

    try {
      const privateKey = readAppleKeyFile(keyFilePath.trim());
      console.log(`✅ Successfully read key file: ${keyFilePath}`);
      return privateKey;
    } catch (error) {
      console.error(`❌ Error reading key file: ${error.message}`);
      process.exit(1);
    }
  } else {
    console.log('\n📝 Please paste your Apple Private Key (press Enter twice when done):');
    const privateKeyLines = [];
    let lineCount = 0;

    while (lineCount < 100) { // Prevent infinite loop
      const line = await question(lineCount === 0 ? 'Private Key: ' : '');
      if (line === '' && lineCount > 0) {
        break;
      }
      privateKeyLines.push(line);
      lineCount++;
    }

    const privateKey = privateKeyLines.join('\n');
    rl.close();
    return privateKey;
  }
}


function readAppleKeyFile(keyFilePath) {
  try {
    const fullPath = path.resolve(keyFilePath);
    if (!fs.existsSync(fullPath)) {
      throw new Error(`Key file not found: ${fullPath}`);
    }

    const keyContent = fs.readFileSync(fullPath, 'utf8');

    // Validate that it looks like a private key
    if (!keyContent.includes('BEGIN PRIVATE KEY') || !keyContent.includes('END PRIVATE KEY')) {
      throw new Error('File does not appear to be a valid Apple private key file');
    }

    return keyContent;
  } catch (error) {
    throw new Error(`Error reading key file: ${error.message}`);
  }
}

async function createOrUpdateSecret(secretName, secretValue, region) {
  try {
    // Try to describe the secret to see if it exists
    execSync(`aws secretsmanager describe-secret --secret-id ${secretName} --region ${region}`, { stdio: 'pipe' });

    // Secret exists, update it
    console.log(`🔄 Updating existing secret: ${secretName}`);
    let secretJson;
    if (secretName.includes('webhook')) {
      secretJson = JSON.stringify({ webhookSecret: secretValue });
    } else if (secretName.includes('shared')) {
      secretJson = JSON.stringify({ sharedSecret: secretValue });
    } else {
      secretJson = JSON.stringify({ privateKey: secretValue });
    }
    execSync(`aws secretsmanager update-secret --secret-id ${secretName} --secret-string '${secretJson}' --region ${region}`, { stdio: 'inherit' });
    console.log('✅ Secret updated successfully!');
  } catch (error) {
    if (error.status === 254) { // AWS CLI returns 254 for ResourceNotFoundException
      // Secret doesn't exist, create it
      console.log(`🆕 Creating new secret: ${secretName}`);
      let secretJson;
      if (secretName.includes('webhook')) {
        secretJson = JSON.stringify({ webhookSecret: secretValue });
      } else if (secretName.includes('shared')) {
        secretJson = JSON.stringify({ sharedSecret: secretValue });
      } else {
        secretJson = JSON.stringify({ privateKey: secretValue });
      }

      let description;
      if (secretName.includes('iap')) {
        description = "Apple In-App Purchase private key for Lingible App Store Server API";
      } else if (secretName.includes('webhook')) {
        description = "Apple webhook secret for Lingible App Store Server Notifications";
      } else if (secretName.includes('shared')) {
        description = "Apple shared secret for Lingible App Store receipt validation";
      } else {
        description = "Apple Sign-In private key for Lingible Cognito";
      }
      execSync(`aws secretsmanager create-secret --name ${secretName} --description "${description}" --secret-string '${secretJson}' --region ${region}`, { stdio: 'inherit' });
      console.log('✅ Secret created successfully!');
    } else {
      throw error;
    }
  }
}

async function deleteSecret(secretName, region) {
  try {
    console.log(`🗑️  Deleting secret: ${secretName}`);
    execSync(`aws secretsmanager delete-secret --secret-id ${secretName} --force-delete-without-recovery --region ${region}`, { stdio: 'inherit' });
    console.log('✅ Secret deleted successfully!');
  } catch (error) {
    if (error.status === 254) {
      console.log('ℹ️  Secret does not exist, nothing to delete.');
    } else {
      throw error;
    }
  }
}

async function showSecretInfo(secretName, region) {
  try {
    console.log(`📋 Secret information for: ${secretName}`);
    const result = execSync(`aws secretsmanager describe-secret --secret-id ${secretName} --region ${region}`, { encoding: 'utf8' });
    const secretInfo = JSON.parse(result);

    console.log(`   Name: ${secretInfo.Name}`);
    console.log(`   Description: ${secretInfo.Description}`);
    console.log(`   Created: ${secretInfo.CreatedDate}`);
    console.log(`   Last Modified: ${secretInfo.LastModifiedDate}`);
    console.log(`   Version Count: ${secretInfo.VersionIdsToStages ? Object.keys(secretInfo.VersionIdsToStages).length : 0}`);
  } catch (error) {
    if (error.status === 254) {
      console.log('❌ Secret does not exist.');
    } else {
      throw error;
    }
  }
}

async function getAppleSharedSecret() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = (query) => {
    return new Promise((resolve) => {
      rl.question(query, resolve);
    });
  };

  console.log('🔐 Apple Shared Secret Manager');
  console.log('===============================\n');
  console.log('Note: This is the App Store shared secret for receipt validation.');
  console.log('You can find this in your App Store Connect account.\n');

  const sharedSecret = await question('Enter your Apple Shared Secret: ');
  rl.close();

  return sharedSecret.trim();
}

async function getAppleWebhookSecret() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = (query) => {
    return new Promise((resolve) => {
      rl.question(query, resolve);
    });
  };

  console.log('🔐 Apple Webhook Secret Manager');
  console.log('===============================\n');
  console.log('This is a custom secret for webhook signature verification.');
  console.log('You can generate one with: openssl rand -hex 32\n');

  const webhookSecret = await question('Enter your Apple Webhook Secret: ');
  rl.close();

  return webhookSecret.trim();
}

async function main() {
  const command = process.argv[2];
  const secretType = process.argv[3];
  const environment = process.argv[4];

  if (!command || !['create', 'update', 'delete', 'info'].includes(command)) {
    console.log('Usage: npm run apple-secret <command> <secret-type> <environment>');
    console.log('');
    console.log('Commands:');
    console.log('  create  - Create a new Apple secret');
    console.log('  update  - Update an existing Apple secret');
    console.log('  delete  - Delete an Apple secret');
    console.log('  info    - Show information about an Apple secret');
    console.log('');
    console.log('Secret Types:');
    console.log('  private-key  - Apple private key (for Cognito Apple Sign-In)');
    console.log('  shared-secret - Apple shared secret (for App Store receipt validation)');
    console.log('  iap-private-key - Apple In-App Purchase private key (for App Store Server API)');
    console.log('  webhook-secret - Apple webhook secret (for webhook signature verification)');
    console.log('');
    console.log('Environment: dev or prod');
    console.log('');
    console.log('Examples:');
    console.log('  npm run apple-secret create private-key dev');
    console.log('  npm run apple-secret create shared-secret dev');
    console.log('  npm run apple-secret create iap-private-key dev');
    console.log('  npm run apple-secret create webhook-secret dev');
    console.log('  npm run apple-secret update private-key prod');
    console.log('  npm run apple-secret info private-key dev');
    process.exit(1);
  }

  if (!secretType || !['private-key', 'shared-secret', 'iap-private-key', 'webhook-secret'].includes(secretType)) {
    console.error('❌ Secret type must be "private-key", "shared-secret", "iap-private-key", or "webhook-secret"');
    process.exit(1);
  }

  if (!environment || !['dev', 'prod'].includes(environment)) {
    console.error('❌ Environment must be "dev" or "prod"');
    process.exit(1);
  }

  const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';
  let secretName;
  if (secretType === 'private-key') {
    secretName = `lingible-apple-private-key-${environment}`;
  } else if (secretType === 'shared-secret') {
    secretName = `lingible-apple-shared-secret-${environment}`;
  } else if (secretType === 'iap-private-key') {
    secretName = `lingible-apple-iap-private-key-${environment}`;
  } else if (secretType === 'webhook-secret') {
    secretName = `lingible-apple-webhook-secret-${environment}`;
  }

  try {
    console.log('🔐 Apple Secret Manager');
    console.log('========================\n');
    let secretTypeDescription;
    if (secretType === 'private-key') {
      secretTypeDescription = 'Private Key (Cognito)';
    } else if (secretType === 'shared-secret') {
      secretTypeDescription = 'Shared Secret (App Store)';
    } else if (secretType === 'iap-private-key') {
      secretTypeDescription = 'In-App Purchase Private Key (App Store Server API)';
    } else if (secretType === 'webhook-secret') {
      secretTypeDescription = 'Webhook Secret (App Store Server Notifications)';
    }

    console.log(`Secret Type: ${secretTypeDescription}`);
    console.log(`Environment: ${environment}`);
    console.log(`Secret Name: ${secretName}\n`);

    switch (command) {
      case 'create':
      case 'update': {
        let secretValue;

        if (secretType === 'private-key' || secretType === 'iap-private-key') {
          secretValue = await getApplePrivateKey();
        } else if (secretType === 'shared-secret') {
          secretValue = await getAppleSharedSecret();
        } else if (secretType === 'webhook-secret') {
          secretValue = await getAppleWebhookSecret();
        }

        await createOrUpdateSecret(secretName, secretValue, region);
        console.log('\n🎉 Secret stored successfully!');
        console.log(`📝 You can now deploy your infrastructure with: npm run deploy:${environment}`);

        if (secretType === 'private-key') {
          console.log('💡 Remember to configure Client ID, Team ID, and Key ID separately.');
        } else if (secretType === 'iap-private-key') {
          console.log('💡 Remember to configure Key ID, Team ID, and Bundle ID separately.');
        } else if (secretType === 'webhook-secret') {
          console.log('💡 The webhook secret is now stored securely in AWS Secrets Manager.');
          console.log('💡 Use this same secret when configuring webhook URL in App Store Connect.');
        } else {
          console.log('💡 The shared secret is now stored securely in AWS Secrets Manager.');
        }
        break;
      }

      case 'delete':
        await deleteSecret(secretName, region);
        break;

      case 'info':
        await showSecretInfo(secretName, region);
        break;
    }

  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();
