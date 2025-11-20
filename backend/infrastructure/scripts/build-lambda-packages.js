#!/usr/bin/env node

const path = require('path');

const { main } = require('../../cdk/scripts/build-lambda-packages.js');

console.warn('⚠️  backend/infrastructure/scripts/build-lambda-packages.js is deprecated. Use backend/cdk/scripts/build-lambda-packages.js instead.');
console.warn('   (This shim will call the new script automatically.)\n');

main();
