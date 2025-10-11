#!/usr/bin/env node

const readline = require('readline');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const SECRET_TYPES = {
  'apple-private-key': {
    name: (env) => `lingible-apple-private-key-${env}`,
    description: 'Apple Sign-In private key for Lingible Cognito',
    jsonKey: 'privateKey',
    displayName: 'Apple Private Key (Cognito)',
  },
  'apple-iap-private-key': {
    name: (env) => `lingible-apple-iap-private-key-${env}`,
    description: 'Apple In-App Purchase private key for Lingible App Store Server API',
    jsonKey: 'privateKey',
    displayName: 'Apple In-App Purchase Private Key',
  },
  'tavily-api-key': {
    name: (env) => `lingible-tavily-api-key-${env}`,
    description: 'Tavily API key for Lingible slang validation web search',
    jsonKey: 'apiKey',
    displayName: 'Tavily API Key',
  },
};

async function getSecretValue(secretType) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = (query) => {
    return new Promise((resolve) => {
      rl.question(query, resolve);
    });
  };

  console.log(`🔐 ${SECRET_TYPES[secretType].displayName}`);
  console.log('='.repeat(SECRET_TYPES[secretType].displayName.length + 3));
  console.log('');

  // Handle private keys specially (can paste or read from file)
  if (secretType.includes('private-key')) {
    console.log('How would you like to provide your private key?');
    console.log('1. Paste the key content directly');
    console.log('2. Read from a .p8 file');

    const choice = await question('Enter choice (1 or 2): ');

    if (choice === '2') {
      const keyFilePath = await question('Enter path to your .p8 file: ');
      rl.close();

      try {
        const privateKey = readKeyFile(keyFilePath.trim());
        console.log(`✅ Successfully read key file: ${keyFilePath}`);
        return privateKey;
      } catch (error) {
        console.error(`❌ Error reading key file: ${error.message}`);
        process.exit(1);
      }
    } else {
      console.log('\n📝 Please paste your private key (press Enter twice when done):');
      const keyLines = [];
      let lineCount = 0;

      while (lineCount < 100) {
        const line = await question(lineCount === 0 ? 'Private Key: ' : '');
        if (line === '' && lineCount > 0) {
          break;
        }
        keyLines.push(line);
        lineCount++;
      }

      const privateKey = keyLines.join('\n');
      rl.close();
      return privateKey;
    }
  }

  // Handle other secret types
  if (secretType === 'tavily-api-key') {
    console.log('Get your Tavily API key from https://tavily.com');
    console.log('Sign up for free to get access to web search API.\n');
  }

  const secretValue = await question(`Enter your ${SECRET_TYPES[secretType].displayName}: `);
  rl.close();

  if (!secretValue.trim()) {
    throw new Error('Secret value cannot be empty');
  }

  return secretValue.trim();
}

function readKeyFile(keyFilePath) {
  try {
    const fullPath = path.resolve(keyFilePath);
    if (!fs.existsSync(fullPath)) {
      throw new Error(`Key file not found: ${fullPath}`);
    }

    const keyContent = fs.readFileSync(fullPath, 'utf8');

    // Validate that it looks like a private key
    if (!keyContent.includes('BEGIN PRIVATE KEY') || !keyContent.includes('END PRIVATE KEY')) {
      throw new Error('File does not appear to be a valid private key file');
    }

    return keyContent;
  } catch (error) {
    throw new Error(`Error reading key file: ${error.message}`);
  }
}

async function createOrUpdateSecret(secretType, secretValue, environment, region) {
  const config = SECRET_TYPES[secretType];
  const secretName = config.name(environment);

  try {
    // Try to describe the secret to see if it exists
    execSync(`aws secretsmanager describe-secret --secret-id ${secretName} --region ${region}`, { stdio: 'pipe' });

    // Secret exists, update it
    console.log(`🔄 Updating existing secret: ${secretName}`);
    const secretJson = JSON.stringify({ [config.jsonKey]: secretValue });
    execSync(`aws secretsmanager update-secret --secret-id ${secretName} --secret-string '${secretJson}' --region ${region}`, { stdio: 'inherit' });
    console.log('✅ Secret updated successfully!');
  } catch (error) {
    if (error.status === 254) {
      // Secret doesn't exist, create it
      console.log(`🆕 Creating new secret: ${secretName}`);
      const secretJson = JSON.stringify({ [config.jsonKey]: secretValue });
      execSync(`aws secretsmanager create-secret --name ${secretName} --description "${config.description}" --secret-string '${secretJson}' --region ${region}`, { stdio: 'inherit' });
      console.log('✅ Secret created successfully!');
    } else {
      throw error;
    }
  }
}

async function deleteSecret(secretType, environment, region) {
  const config = SECRET_TYPES[secretType];
  const secretName = config.name(environment);

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

async function showSecretInfo(secretType, environment, region) {
  const config = SECRET_TYPES[secretType];
  const secretName = config.name(environment);

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

async function listAllSecrets(environment, region) {
  console.log(`📋 All Lingible secrets for environment: ${environment}`);
  console.log('='.repeat(50));
  console.log('');

  for (const [secretType, config] of Object.entries(SECRET_TYPES)) {
    const secretName = config.name(environment);
    try {
      execSync(`aws secretsmanager describe-secret --secret-id ${secretName} --region ${region}`, { stdio: 'pipe' });
      console.log(`✅ ${config.displayName}: ${secretName}`);
    } catch (error) {
      if (error.status === 254) {
        console.log(`❌ ${config.displayName}: Not configured`);
      }
    }
  }
}

function showUsage() {
  console.log('Usage: npm run secrets <command> <secret-type> <environment>');
  console.log('       npm run secrets list <environment>');
  console.log('');
  console.log('Commands:');
  console.log('  create  - Create a new secret');
  console.log('  update  - Update an existing secret');
  console.log('  delete  - Delete a secret');
  console.log('  info    - Show information about a secret');
  console.log('  list    - List all secrets for an environment');
  console.log('');
  console.log('Secret Types:');
  console.log('  apple-private-key      - Apple Sign-In private key (for Cognito)');
  console.log('  apple-iap-private-key  - In-App Purchase private key (for App Store Server API)');
  console.log('  tavily-api-key         - Tavily API key (for slang validation web search)');
  console.log('');
  console.log('Environment: dev or prod');
  console.log('');
  console.log('Examples:');
  console.log('  npm run secrets create apple-private-key dev');
  console.log('  npm run secrets update tavily-api-key dev');
  console.log('  npm run secrets info apple-iap-private-key prod');
  console.log('  npm run secrets list dev');
  console.log('  npm run secrets delete tavily-api-key dev');
}

async function main() {
  const command = process.argv[2];
  const secretType = process.argv[3];
  const environment = process.argv[4];

  // Handle list command (doesn't need secret type)
  if (command === 'list') {
    const env = secretType; // In list command, arg 3 is the environment
    if (!env || !['dev', 'prod'].includes(env)) {
      console.error('❌ Environment must be "dev" or "prod"');
      process.exit(1);
    }

    const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';
    await listAllSecrets(env, region);
    return;
  }

  // Validate command
  if (!command || !['create', 'update', 'delete', 'info'].includes(command)) {
    showUsage();
    process.exit(1);
  }

  // Validate secret type
  if (!secretType || !SECRET_TYPES[secretType]) {
    console.error(`❌ Invalid secret type: ${secretType}`);
    console.error(`   Valid types: ${Object.keys(SECRET_TYPES).join(', ')}`);
    process.exit(1);
  }

  // Validate environment
  if (!environment || !['dev', 'prod'].includes(environment)) {
    console.error('❌ Environment must be "dev" or "prod"');
    process.exit(1);
  }

  const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';
  const config = SECRET_TYPES[secretType];

  try {
    console.log('🔐 Lingible Secret Manager');
    console.log('==========================\n');
    console.log(`Secret Type: ${config.displayName}`);
    console.log(`Environment: ${environment}`);
    console.log(`Secret Name: ${config.name(environment)}`);
    console.log(`Region: ${region}\n`);

    switch (command) {
      case 'create':
      case 'update': {
        const secretValue = await getSecretValue(secretType);
        await createOrUpdateSecret(secretType, secretValue, environment, region);
        console.log('\n🎉 Secret stored successfully!');
        console.log(`📝 You can now deploy your infrastructure with: npm run deploy:${environment}`);

        // Type-specific tips
        if (secretType === 'apple-private-key') {
          console.log('💡 Remember to configure Client ID, Team ID, and Key ID in config files.');
        } else if (secretType === 'apple-iap-private-key') {
          console.log('💡 Remember to configure Key ID, Team ID, and Bundle ID in config files.');
        } else if (secretType === 'tavily-api-key') {
          console.log('💡 Make sure web_search_enabled is set to true in backend config.');
        }
        break;
      }

      case 'delete':
        await deleteSecret(secretType, environment, region);
        break;

      case 'info':
        await showSecretInfo(secretType, environment, region);
        break;
    }

  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();
