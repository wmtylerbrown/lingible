#!/usr/bin/env node

const readline = require('readline');
const { execSync } = require('child_process');

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
  console.log('Note: Only the private key is stored in AWS Secrets Manager.');
  console.log('Client ID, Team ID, and Key ID should be configured separately.\n');

  console.log('📝 Please paste your Apple Private Key (press Enter twice when done):');
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

async function createOrUpdateSecret(secretName, privateKey, region) {
  try {
    // Try to describe the secret to see if it exists
    execSync(`aws secretsmanager describe-secret --secret-id ${secretName} --region ${region}`, { stdio: 'pipe' });

    // Secret exists, update it
    console.log(`🔄 Updating existing secret: ${secretName}`);
    execSync(`aws secretsmanager update-secret --secret-id ${secretName} --secret-string '{"privateKey":"${privateKey.replace(/"/g, '\\"')}"}' --region ${region}`, { stdio: 'inherit' });
    console.log('✅ Secret updated successfully!');
  } catch (error) {
    if (error.status === 254) { // AWS CLI returns 254 for ResourceNotFoundException
      // Secret doesn't exist, create it
      console.log(`🆕 Creating new secret: ${secretName}`);
      execSync(`aws secretsmanager create-secret --name ${secretName} --description "Apple Sign-In private key for Lingible Cognito" --secret-string '{"privateKey":"${privateKey.replace(/"/g, '\\"')}"}' --region ${region}`, { stdio: 'inherit' });
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

async function main() {
  const command = process.argv[2];
  const environment = process.argv[3];

  if (!command || !['create', 'update', 'delete', 'info'].includes(command)) {
    console.log('Usage: npm run apple-secret <command> <environment>');
    console.log('');
    console.log('Commands:');
    console.log('  create  - Create a new Apple secret');
    console.log('  update  - Update an existing Apple secret');
    console.log('  delete  - Delete an Apple secret');
    console.log('  info    - Show information about an Apple secret');
    console.log('');
    console.log('Environment: dev or prod');
    console.log('');
    console.log('Examples:');
    console.log('  npm run apple-secret create dev');
    console.log('  npm run apple-secret update prod');
    console.log('  npm run apple-secret info dev');
    process.exit(1);
  }

  if (!environment || !['dev', 'prod'].includes(environment)) {
    console.error('❌ Environment must be "dev" or "prod"');
    process.exit(1);
  }

  const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';
  const secretName = `lingible-apple-private-key-${environment}`;

  try {
    switch (command) {
      case 'create':
      case 'update': {
        const privateKey = await getApplePrivateKey();
        await createOrUpdateSecret(secretName, privateKey, region);
        console.log('\n🎉 Private key stored successfully!');
        console.log(`📝 You can now deploy your infrastructure with: npm run deploy:${environment}`);
        console.log('💡 Remember to configure Client ID, Team ID, and Key ID separately.');
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
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

main();
