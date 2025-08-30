#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

// Configuration
const SRC_DIR = '../src';
const LAMBDA_LAYER_DIR = 'lambda-layer';
const LAMBDA_PACKAGES_DIR = 'lambda-packages';
const HASH_FILE = 'lambda-hashes.json';

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
      const regex = new RegExp(pattern.replace(/\*/g, '.*'));
      return regex.test(relativePath);
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

  // Sort files for consistent hashing
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

function buildSharedLayer() {
  console.log('📦 Building shared Lambda layer...');

  const layerDir = LAMBDA_LAYER_DIR;
  const pythonDir = path.join(layerDir, 'python');

  // Calculate hash for shared code
  const sharedDirs = ['models', 'repositories', 'services', 'utils'];
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

  // Copy requirements.txt for layer dependencies
  const requirementsPath = path.join(SRC_DIR, 'requirements.txt');
  if (fs.existsSync(requirementsPath)) {
    fs.copyFileSync(requirementsPath, path.join(layerDir, 'requirements.txt'));
  }

  hashes[layerHashKey] = sharedHash;
  saveHashes(hashes);

  console.log('✅ Shared layer built successfully');
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
  console.log('🚀 Building Lambda packages with smart change detection');
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

  // Build shared layer
  buildSharedLayer();

  // Build handler packages
  buildHandlerPackages();

  console.log('\n🎉 Lambda package build completed successfully!');
  console.log('\n📁 Generated artifacts:');
  console.log(`   - Shared layer: ${LAMBDA_LAYER_DIR}/`);
  console.log(`   - Handler packages: ${LAMBDA_PACKAGES_DIR}/`);
  console.log(`   - Build hashes: ${HASH_FILE}`);
}

main();
