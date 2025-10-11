#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

// Configuration
const SRC_DIR = '../lambda/src';
const LAMBDA_LAYER_DIR = 'lambda-layer';
const LAMBDA_PACKAGES_DIR = 'lambda-packages';
const HASH_FILE = 'lambda-hashes.json';

// Layer configurations
const LAYER_CONFIGS = {
  'core': {
    name: 'Core Dependencies',
    description: 'Core dependencies for most Lambda functions',
    groups: ['main'],
    handlers: [
      'translate_api', 'get_translation_history', 'trending_api', 'trending_job',
      'user_profile_api', 'user_usage_api', 'health_api',
      'delete_translation', 'delete_translations', 'cognito_post_confirmation',
      'slang_upvote_api', 'slang_pending_api', 'slang_admin_approve_api', 'slang_admin_reject_api'
    ]
  },
  'receipt-validation': {
    name: 'Receipt Validation Dependencies',
    description: 'Dependencies for Apple/Google receipt validation',
    groups: ['main', 'receipt-validation'],
    handlers: ['user_upgrade_api', 'apple_webhook', 'user_account_deletion', 'user_data_cleanup',]
  },
  'slang-validation': {
    name: 'Slang Validation Dependencies',
    description: 'Dependencies for slang validation with web search (requests library)',
    groups: ['main', 'slang-validation', 'slang_admin_approve_api', 'slang_admin_reject_api', 'slang_pending_api', 'slang_upvote_api'],
    handlers: ['submit_slang_api']
  }
};

// Patterns to exclude from builds
const EXCLUDE_PATTERNS = [
  '__pycache__',
  '*.pyc',
  '*.pyo',
  '.pytest_cache',
  '.mypy_cache',
  '.coverage',
  'htmlcov',
  '.tox',
  '.venv',
  'venv',
  'node_modules',
  '.git',
  '.DS_Store',
  '*.log',
  '*.tmp',
  '*.swp',
  '*.swo',
];

function shouldExclude(filePath) {
  const relativePath = path.relative(SRC_DIR, filePath);
  return EXCLUDE_PATTERNS.some(pattern => {
    if (pattern.includes('*')) {
      if (pattern.startsWith('*.')) {
        const extension = pattern.substring(1);
        return relativePath.endsWith(extension) || path.basename(relativePath).endsWith(extension);
      }
      const escapedPattern = pattern
        .replace(/[.+?^${}()|[\]\\]/g, '\\$&')
        .replace(/\\\*/g, '.*');
      const regex = new RegExp('^' + escapedPattern + '$');
      return regex.test(path.basename(relativePath)) || regex.test(relativePath);
    }
    return relativePath.includes(pattern);
  });
}

function calculateDirectoryHash(dirPath) {
  if (!fs.existsSync(dirPath)) {
    return '';
  }

  const hash = crypto.createHash('sha256');
  const files = [];

  function walkDirectory(currentPath) {
    const entries = fs.readdirSync(currentPath, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(currentPath, entry.name);

      if (shouldExclude(fullPath)) {
        continue;
      }

      if (entry.isDirectory()) {
        walkDirectory(fullPath);
      } else {
        files.push(fullPath);
      }
    }
  }

  walkDirectory(dirPath);
  files.sort();

  for (const file of files) {
    const content = fs.readFileSync(file);
    hash.update(content);
  }

  return hash.digest('hex');
}

function copyDirectoryFiltered(src, dest) {
  if (!fs.existsSync(src)) {
    return;
  }

  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (shouldExclude(srcPath)) {
      continue;
    }

    if (entry.isDirectory()) {
      copyDirectoryFiltered(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function loadHashes() {
  if (fs.existsSync(HASH_FILE)) {
    try {
      return JSON.parse(fs.readFileSync(HASH_FILE, 'utf8'));
    } catch (error) {
      console.log('Warning: Could not parse hash file, starting fresh');
    }
  }
  return {};
}

function saveHashes(hashes) {
  fs.writeFileSync(HASH_FILE, JSON.stringify(hashes, null, 2));
}

function buildDependencyLayer(layerName, config) {
  console.log(`📦 Building ${config.name} layer...`);

  const layerDir = `lambda-${layerName}-layer`;
  const layerHashKey = `${layerName}-layer`;

  // Create layer directory first
  if (fs.existsSync(layerDir)) {
    fs.rmSync(layerDir, { recursive: true, force: true });
  }
  fs.mkdirSync(layerDir, { recursive: true });

  // Generate requirements.txt for this layer
  console.log(`📦 Generating requirements.txt for ${layerName} layer...`);
  try {
    const lambdaDir = path.join(__dirname, '..', '..', 'lambda');
    const venvPath = path.join(__dirname, '..', '..', '..', '.venv', 'bin', 'activate');
    const requirementsPath = path.join(layerDir, 'requirements.txt');

    // Build poetry export command with specific groups
    const groupsArg = config.groups.map(group => `--with ${group}`).join(' ');
    const exportCmd = `cd "${lambdaDir}" && source "${venvPath}" && poetry export ${groupsArg} --format=requirements.txt --output="${path.resolve(requirementsPath)}" --without-hashes`;

    execSync(exportCmd, {
      stdio: 'inherit',
      shell: true
    });

    console.log(`✅ Generated requirements.txt for ${layerName} layer`);
  } catch (error) {
    console.error(`❌ Failed to generate requirements.txt for ${layerName} layer:`, error.message);
    return;
  }

  // Calculate hash for requirements.txt
  const requirementsPath = path.join(layerDir, 'requirements.txt');
  const content = fs.readFileSync(requirementsPath);
  const requirementsHash = crypto.createHash('sha256').update(content).digest('hex');

  const hashes = loadHashes();

  if (hashes[layerHashKey] === requirementsHash) {
    console.log(`✅ ${config.name} layer unchanged, skipping rebuild`);
    return;
  }

  hashes[layerHashKey] = requirementsHash;
  saveHashes(hashes);

  console.log(`✅ ${config.name} layer built successfully`);
}

function buildSharedLayer() {
  console.log('📦 Building shared code Lambda layer...');

  const layerDir = LAMBDA_LAYER_DIR;
  const pythonDir = path.join(layerDir, 'python');

  // Calculate hash for shared code
  const sharedDirs = ['models', 'repositories', 'services', 'utils', 'data'];
  let sharedHash = '';

  for (const dirName of sharedDirs) {
    const srcDir = path.join(SRC_DIR, dirName);
    if (fs.existsSync(srcDir)) {
      sharedHash += calculateDirectoryHash(srcDir);
    }
  }

  // Check if layer needs rebuilding
  const hashes = loadHashes();
  const layerHashKey = 'shared-layer';

  if (hashes[layerHashKey] === sharedHash) {
    console.log('✅ Shared layer unchanged, skipping rebuild');
    return;
  }

  // Clean and rebuild layer
  if (fs.existsSync(layerDir)) {
    fs.rmSync(layerDir, { recursive: true, force: true });
  }

  fs.mkdirSync(pythonDir, { recursive: true });

  // Copy shared code to layer
  for (const dirName of sharedDirs) {
    const srcDir = path.join(SRC_DIR, dirName);
    if (fs.existsSync(srcDir)) {
      copyDirectoryFiltered(srcDir, path.join(pythonDir, dirName));
    }
  }

  hashes[layerHashKey] = sharedHash;
  saveHashes(hashes);

  console.log('✅ Shared code layer built successfully');
}

function buildHandlerPackages() {
  console.log('📦 Building handler packages...');

  const handlersDir = path.join(SRC_DIR, 'handlers');
  if (!fs.existsSync(handlersDir)) {
    console.log('❌ Handlers directory not found');
    return;
  }

  const hashes = loadHashes();
  const handlerDirs = fs.readdirSync(handlersDir, { withFileTypes: true })
    .filter(entry => entry.isDirectory())
    .map(entry => entry.name);

  for (const handlerName of handlerDirs) {
    const srcDir = path.join(handlersDir, handlerName);
    const packageDir = path.join(LAMBDA_PACKAGES_DIR, handlerName);

    // Calculate hash for handler
    const handlerHash = calculateDirectoryHash(srcDir);
    const handlerHashKey = `handler-${handlerName}`;

    if (hashes[handlerHashKey] === handlerHash) {
      console.log(`✅ Handler ${handlerName} unchanged, skipping rebuild`);
      continue;
    }

    // Clean and rebuild handler package
    if (fs.existsSync(packageDir)) {
      fs.rmSync(packageDir, { recursive: true, force: true });
    }

    fs.mkdirSync(packageDir, { recursive: true });

    // Copy handler code
    copyDirectoryFiltered(srcDir, packageDir);

    // Create __init__.py if it doesn't exist
    const initFile = path.join(packageDir, '__init__.py');
    if (!fs.existsSync(initFile)) {
      fs.writeFileSync(initFile, '# Handler package\n');
    }

    hashes[handlerHashKey] = handlerHash;
    console.log(`✅ Handler ${handlerName} built successfully`);
  }

  saveHashes(hashes);
}

function main() {
  console.log('🚀 Building Lambda packages with optimized dependencies');
  console.log('='.repeat(60));

  // Check if we're in the right directory
  if (!fs.existsSync('app.js')) {
    console.log('❌ Error: Please run this script from the infrastructure directory');
    process.exit(1);
  }

  // Check if source directory exists
  if (!fs.existsSync(SRC_DIR)) {
    console.log(`❌ Error: Source directory ${SRC_DIR} not found`);
    process.exit(1);
  }

  // Create output directories
  if (!fs.existsSync(LAMBDA_PACKAGES_DIR)) {
    fs.mkdirSync(LAMBDA_PACKAGES_DIR, { recursive: true });
  }

  // Build dependency layers
  for (const [layerName, config] of Object.entries(LAYER_CONFIGS)) {
    buildDependencyLayer(layerName, config);
  }

  // Build shared code layer
  buildSharedLayer();

  // Build handler packages
  buildHandlerPackages();

  console.log('\n🎉 Lambda package build completed successfully!');
  console.log('\n📁 Generated artifacts:');
  for (const [layerName, config] of Object.entries(LAYER_CONFIGS)) {
    console.log(`   - ${config.name}: lambda-${layerName}-layer/`);
  }
  console.log(`   - Shared code layer: ${LAMBDA_LAYER_DIR}/`);
  console.log(`   - Handler packages: ${LAMBDA_PACKAGES_DIR}/`);
  console.log(`   - Build hashes: ${HASH_FILE}`);

  console.log('\n📊 Layer Usage:');
  for (const [layerName, config] of Object.entries(LAYER_CONFIGS)) {
    console.log(`   - ${config.name}: ${config.handlers.join(', ')}`);
  }
}

main();
