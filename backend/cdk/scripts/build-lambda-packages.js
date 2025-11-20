#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const LAMBDA_DIR = path.join(REPO_ROOT, 'backend', 'lambda');
const SRC_DIR = path.join(LAMBDA_DIR, 'src');
const ARTIFACT_ROOT = path.resolve(__dirname, '..', 'artifacts');
const LAMBDA_LAYER_DIR = path.join(ARTIFACT_ROOT, 'lambda-layer');
const LAMBDA_PACKAGES_DIR = path.join(ARTIFACT_ROOT, 'lambda-packages');
const HASH_FILE = path.join(ARTIFACT_ROOT, 'lambda-hashes.json');
const VENV_ACTIVATE = path.join(REPO_ROOT, '.venv', 'bin', 'activate');

const LAYER_CONFIGS = {
  core: {
    name: 'Core Dependencies',
    description: 'Core dependencies for most Lambda functions',
    groups: ['main'],
    handlers: [
      'translate_api',
      'get_translation_history_api',
      'trending_api',
      'trending_job_async',
      'user_profile_api',
      'user_usage_api',
      'health_api',
      'delete_translation_api',
      'delete_translations_api',
      'cognito_post_confirmation_trigger',
      'submit_slang_api',
      'slang_upvote_api',
      'slang_pending_api',
      'slang_admin_approve_api',
      'slang_admin_reject_api',
      'quiz_challenge_api',
      'quiz_submit_api',
      'quiz_history_api',
      'quiz_progress_api',
      'quiz_end_api',
    ],
  },
  'receipt-validation': {
    name: 'Receipt Validation Dependencies',
    description: 'Dependencies for Apple/Google receipt validation',
    groups: ['main', 'receipt-validation'],
    handlers: ['user_upgrade_api', 'apple_webhook_api', 'user_account_deletion_api', 'user_data_cleanup_async'],
  },
  'slang-validation': {
    name: 'Slang Validation Dependencies',
    description: 'Dependencies for slang validation with web search (Tavily SDK)',
    groups: ['main', 'slang-validation'],
    handlers: ['slang_validation_async'],
  },
};

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
  return EXCLUDE_PATTERNS.some((pattern) => {
    if (pattern.includes('*')) {
      if (pattern.startsWith('*.')) {
        const extension = pattern.substring(1);
        return relativePath.endsWith(extension) || path.basename(relativePath).endsWith(extension);
      }
      const escapedPattern = pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\\\*/g, '.*');
      const regex = new RegExp(`^${escapedPattern}$`);
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

  fs.mkdirSync(dest, { recursive: true });

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
  fs.mkdirSync(ARTIFACT_ROOT, { recursive: true });
  fs.writeFileSync(HASH_FILE, JSON.stringify(hashes, null, 2));
}

function buildDependencyLayer(layerName, config) {
  console.log(`📦 Building ${config.name} layer...`);

  const layerDir = path.join(ARTIFACT_ROOT, `lambda-${layerName}-layer`);
  const layerHashKey = `${layerName}-layer`;

  if (fs.existsSync(layerDir)) {
    fs.rmSync(layerDir, { recursive: true, force: true });
  }
  fs.mkdirSync(layerDir, { recursive: true });

  console.log(`📦 Generating requirements.txt for ${layerName} layer...`);
  try {
    const requirementsPath = path.join(layerDir, 'requirements.txt');
    const groupsArg = config.groups.map((group) => `--with ${group}`).join(' ');
    const exportCmd = `cd "${LAMBDA_DIR}" && source "${VENV_ACTIVATE}" && poetry export ${groupsArg} --format=requirements.txt --output="${path.resolve(
      requirementsPath
    )}" --without-hashes`;

    execSync(exportCmd, {
      stdio: 'inherit',
      shell: true,
    });

    console.log(`✅ Generated requirements.txt for ${layerName} layer`);
  } catch (error) {
    console.error(`❌ Failed to generate requirements.txt for ${layerName} layer:`, error.message);
    return;
  }

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

  const sharedDirs = ['models', 'repositories', 'services', 'utils', 'data'];
  let sharedHash = '';

  for (const dirName of sharedDirs) {
    const srcDir = path.join(SRC_DIR, dirName);
    if (fs.existsSync(srcDir)) {
      sharedHash += calculateDirectoryHash(srcDir);
    }
  }

  const hashes = loadHashes();
  const layerHashKey = 'shared-layer';

  if (hashes[layerHashKey] === sharedHash) {
    console.log('✅ Shared layer unchanged, skipping rebuild');
    return;
  }

  if (fs.existsSync(layerDir)) {
    fs.rmSync(layerDir, { recursive: true, force: true });
  }

  fs.mkdirSync(pythonDir, { recursive: true });

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
  const handlerDirs = fs
    .readdirSync(handlersDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);

  for (const handlerName of handlerDirs) {
    const srcDir = path.join(handlersDir, handlerName);
    const packageDir = path.join(LAMBDA_PACKAGES_DIR, handlerName);

    const handlerHash = calculateDirectoryHash(srcDir);
    const handlerHashKey = `handler-${handlerName}`;

    if (hashes[handlerHashKey] === handlerHash) {
      console.log(`✅ Handler ${handlerName} unchanged, skipping rebuild`);
      continue;
    }

    if (fs.existsSync(packageDir)) {
      fs.rmSync(packageDir, { recursive: true, force: true });
    }

    fs.mkdirSync(packageDir, { recursive: true });

    copyDirectoryFiltered(srcDir, packageDir);

    const initFile = path.join(packageDir, '__init__.py');
    if (!fs.existsSync(initFile)) {
      fs.writeFileSync(initFile, '# Handler package\n');
    }

    hashes[handlerHashKey] = handlerHash;
    console.log(`✅ Handler ${handlerName} built successfully`);
  }

  saveHashes(hashes);
}

function ensureArtifactDirectories() {
  fs.mkdirSync(ARTIFACT_ROOT, { recursive: true });
  fs.mkdirSync(LAMBDA_LAYER_DIR, { recursive: true });
  fs.mkdirSync(LAMBDA_PACKAGES_DIR, { recursive: true });
}

function main() {
  console.log('🚀 Building Lambda packages with optimized dependencies (CDK)');
  console.log('='.repeat(70));

  if (!fs.existsSync(SRC_DIR)) {
    console.log(`❌ Error: Source directory ${SRC_DIR} not found`);
    process.exit(1);
  }

  if (!fs.existsSync(VENV_ACTIVATE)) {
    console.log(`❌ Error: Virtual environment not found at ${VENV_ACTIVATE}`);
    process.exit(1);
  }

  ensureArtifactDirectories();

  for (const [layerName, config] of Object.entries(LAYER_CONFIGS)) {
    buildDependencyLayer(layerName, config);
  }

  buildSharedLayer();
  buildHandlerPackages();

  console.log('\n🎉 Lambda package build completed successfully!');
  console.log(`Artifacts available in: ${ARTIFACT_ROOT}`);
  console.log('Remember to run this command before synth/deploy so CDK can bundle the latest bits.\n');
}

if (require.main === module) {
  main();
}

module.exports = { main };
