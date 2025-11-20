#!/usr/bin/env node

const readline = require('readline');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const STORAGE = {
  SECRETS_MANAGER: 'secretsmanager',
  PARAMETER_STORE: 'ssm',
};

const SECRET_ITEMS = {
  'apple-private-key': {
    storage: STORAGE.SECRETS_MANAGER,
    name: (env) => `lingible-apple-private-key-${env}`,
    description: 'Apple Sign-In private key for Cognito Auth',
    displayName: 'Apple Private Key (Cognito)',
    jsonKey: 'privateKey',
  },
  'apple-iap-private-key': {
    storage: STORAGE.PARAMETER_STORE,
    name: (env) => `/lingible/${env}/secrets/apple-iap-private-key`,
    description: 'Apple In-App Purchase private key for App Store Server API',
    displayName: 'Apple IAP Private Key (Parameter Store)',
  },
  'tavily-api-key': {
    storage: STORAGE.PARAMETER_STORE,
    name: (env) => `/lingible/${env}/secrets/tavily-api-key`,
    description: 'Tavily API key for slang validation web search',
    displayName: 'Tavily API Key (Parameter Store)',
  },
};

function showUsage() {
  console.log('Usage: npm run secrets <command> <secret-type> <environment>');
  console.log('       npm run secrets list <environment>');
  console.log('');
  console.log('Commands: create | update | delete | info | list');
  console.log('Secret Types:');
  console.log(Object.keys(SECRET_ITEMS).map((key) => `  - ${key}`).join('\n'));
  console.log('\nEnvironments: dev | prod');
}

function ensureEnv(env) {
  if (!['dev', 'prod'].includes(env)) {
    console.error('❌ Environment must be "dev" or "prod"');
    process.exit(1);
  }
}

async function promptForValue(label, allowFile = false) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const ask = (query) =>
    new Promise((resolve) => {
      rl.question(query, resolve);
    });

  try {
    if (allowFile) {
      console.log('How would you like to provide the key?');
      console.log('1. Paste key content');
      console.log('2. Read from .p8 file');
      const choice = (await ask('Enter choice (1 or 2): ')).trim();
      if (choice === '2') {
        const filePath = (await ask('Path to .p8 file: ')).trim();
        const resolved = path.resolve(filePath);
        if (!fs.existsSync(resolved)) {
          throw new Error(`Key file not found: ${resolved}`);
        }
        rl.close();
        return fs.readFileSync(resolved, 'utf8');
      }
      console.log('\nPaste key (press Enter twice to finish):');
      const lines = [];
      while (true) {
        const line = await ask(lines.length === 0 ? 'Key: ' : '');
        if (!line && lines.length > 0) {
          break;
        }
        lines.push(line);
      }
      rl.close();
      return lines.join('\n');
    }

    const value = (await ask(`Enter ${label}: `)).trim();
    rl.close();
    if (!value) {
      throw new Error(`${label} cannot be empty`);
    }
    return value;
  } catch (err) {
    rl.close();
    throw err;
  }
}

function runAws(command) {
  return execSync(command, { stdio: 'pipe', encoding: 'utf8' });
}

function secretExists(name, storage, region) {
  try {
    if (storage === STORAGE.SECRETS_MANAGER) {
      runAws(`aws secretsmanager describe-secret --secret-id ${name} --region ${region}`);
    } else {
      runAws(`aws ssm get-parameter --name ${name} --region ${region}`);
    }
    return true;
  } catch (err) {
    if (err.status === 254 || err.status === 255) {
      return false;
    }
    throw err;
  }
}

function upsertSecret(itemConfig, value, environment, region) {
  const name = itemConfig.name(environment);
  if (itemConfig.storage === STORAGE.SECRETS_MANAGER) {
    const payload = JSON.stringify({ [itemConfig.jsonKey]: value });
    if (secretExists(name, STORAGE.SECRETS_MANAGER, region)) {
      console.log(`🔄 Updating secret: ${name}`);
      runAws(
        `aws secretsmanager update-secret --secret-id ${name} --secret-string '${payload}' --region ${region}`
      );
    } else {
      console.log(`🆕 Creating secret: ${name}`);
      runAws(
        `aws secretsmanager create-secret --name ${name} --description "${itemConfig.description}" --secret-string '${payload}' --region ${region}`
      );
    }
  } else {
    console.log(secretExists(name, STORAGE.PARAMETER_STORE, region) ? `🔄 Updating parameter: ${name}` : `🆕 Creating parameter: ${name}`);
    runAws(
      `aws ssm put-parameter --name ${name} --type SecureString --value '${value}' --overwrite --region ${region}`
    );
  }
  console.log('✅ Stored successfully!');
}

function deleteSecret(itemConfig, environment, region) {
  const name = itemConfig.name(environment);
  if (!secretExists(name, itemConfig.storage, region)) {
    console.log('ℹ️ Nothing to delete.');
    return;
  }
  if (itemConfig.storage === STORAGE.SECRETS_MANAGER) {
    runAws(`aws secretsmanager delete-secret --secret-id ${name} --force-delete-without-recovery --region ${region}`);
  } else {
    runAws(`aws ssm delete-parameter --name ${name} --region ${region}`);
  }
  console.log('🗑️ Deleted successfully.');
}

function showInfo(itemConfig, environment, region) {
  const name = itemConfig.name(environment);
  if (!secretExists(name, itemConfig.storage, region)) {
    console.log('❌ Entry does not exist.');
    return;
  }
  if (itemConfig.storage === STORAGE.SECRETS_MANAGER) {
    const info = JSON.parse(runAws(`aws secretsmanager describe-secret --secret-id ${name} --region ${region}`));
    console.log(`📋 ${name}`);
    console.log(`   Description: ${info.Description}`);
    console.log(`   Created: ${info.CreatedDate}`);
    console.log(`   Last Modified: ${info.LastModifiedDate}`);
  } else {
    const info = JSON.parse(
      runAws(`aws ssm get-parameter --name ${name} --with-decryption --region ${region}`)
    );
    console.log(`📋 ${name}`);
    console.log(`   Type: ${info.Parameter.Type}`);
    console.log(`   Last Modified: ${info.Parameter.LastModifiedDate}`);
  }
}

function listAll(env, region) {
  console.log(`📋 Lingible secrets/parameters for ${env}`);
  Object.entries(SECRET_ITEMS).forEach(([key, config]) => {
    const name = config.name(env);
    const exists = secretExists(name, config.storage, region);
    console.log(`${exists ? '✅' : '❌'} ${config.displayName}: ${name}`);
  });
}

async function main() {
  const [command, secretType, envArg] = process.argv.slice(2);

  if (!command) {
    showUsage();
    process.exit(1);
  }

  if (command === 'list') {
    ensureEnv(secretType);
    listAll(secretType, process.env.CDK_DEFAULT_REGION || 'us-east-1');
    return;
  }

  if (!['create', 'update', 'delete', 'info'].includes(command)) {
    showUsage();
    process.exit(1);
  }

  const item = SECRET_ITEMS[secretType];
  if (!item) {
    console.error(`❌ Unknown secret type: ${secretType}`);
    showUsage();
    process.exit(1);
  }

  ensureEnv(envArg);
  const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';

  console.log('🔐 Lingible Secret Manager');
  console.log('==========================');
  console.log(`Type: ${item.displayName}`);
  console.log(`Storage: ${item.storage === STORAGE.SECRETS_MANAGER ? 'Secrets Manager' : 'SSM Parameter Store'}`);
  console.log(`Environment: ${envArg}`);
  console.log(`Name: ${item.name(envArg)}`);
  console.log('');

  try {
    if (command === 'delete') {
      deleteSecret(item, envArg, region);
      return;
    }

    if (command === 'info') {
      showInfo(item, envArg, region);
      return;
    }

    const value = await promptForValue(
      item.displayName,
      secretType.includes('private-key')
    );
    upsertSecret(item, value, envArg, region);
    console.log(`\n🎉 ${command === 'create' ? 'Created' : 'Updated'} successfully.`);
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    process.exit(1);
  }
}

main();
