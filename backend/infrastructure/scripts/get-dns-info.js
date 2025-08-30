#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');

function runCommand(command, description) {
  console.log(`\n🔄 ${description}...`);
  console.log(`   Command: ${command}`);

  try {
    const result = execSync(command, { encoding: 'utf8', stdio: 'pipe' });
    console.log(`✅ ${description} completed`);
    if (result.trim()) {
      console.log(`   Output: ${result.trim()}`);
    }
    return result;
  } catch (error) {
    console.log(`❌ Error: ${description}`);
    console.log(`   Error: ${error.stderr || error.message}`);
    process.exit(1);
  }
}

function getStackOutputs(stackName) {
  try {
    const result = execSync(`aws cloudformation describe-stacks --stack-name ${stackName} --query 'Stacks[0].Outputs' --output json`, { encoding: 'utf8' });
    return JSON.parse(result);
  } catch (error) {
    console.log(`❌ Error getting outputs for stack ${stackName}: ${error.message}`);
    return [];
  }
}

function main() {
  // Parse command line arguments
  const args = process.argv.slice(2);
  let environment = 'dev';

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--environment' && i + 1 < args.length) {
      environment = args[i + 1];
      break;
    }
  }

  if (!['dev', 'prod'].includes(environment)) {
    console.log('❌ Error: Environment must be "dev" or "prod"');
    process.exit(1);
  }

  console.log('🌐 Getting DNS Information for Lingible');
  console.log('='.repeat(50));

  // Get hosted zones stack outputs
  const hostedZonesStackName = `Lingible-${environment.charAt(0).toUpperCase() + environment.slice(1)}-HostedZones`;
  console.log(`\n📋 Getting outputs from ${hostedZonesStackName}...`);

  const hostedZonesOutputs = getStackOutputs(hostedZonesStackName);

  if (hostedZonesOutputs.length === 0) {
    console.log(`❌ No outputs found for stack ${hostedZonesStackName}`);
    console.log('   Make sure the hosted zones stack has been deployed first.');
    process.exit(1);
  }

  // Display hosted zones information
  console.log('\n🌐 Hosted Zones Information:');
  console.log('-'.repeat(30));

  for (const output of hostedZonesOutputs) {
    if (output.OutputKey === 'HostedZoneId') {
      console.log(`📍 Hosted Zone ID: ${output.OutputValue}`);
    } else if (output.OutputKey === 'HostedZoneNameServers') {
      console.log(`🌍 Name Servers: ${output.OutputValue}`);
    } else if (output.OutputKey === 'DeploymentInstructions') {
      console.log(`📝 Instructions: ${output.OutputValue}`);
    }
  }

  // Get backend stack outputs if it exists
  const backendStackName = `Lingible-${environment.charAt(0).toUpperCase() + environment.slice(1)}-Backend`;
  console.log(`\n📋 Getting outputs from ${backendStackName}...`);

  const backendStackOutputs = getStackOutputs(backendStackName);

  if (backendStackOutputs.length > 0) {
    console.log('\n🔗 Backend Stack Information:');
    console.log('-'.repeat(30));

    for (const output of backendStackOutputs) {
      if (output.OutputKey === 'ApiUrl') {
        console.log(`🚀 API Gateway URL: ${output.OutputValue}`);
      } else if (output.OutputKey === 'ApiDomainName') {
        console.log(`🌐 Custom Domain URL: https://${output.OutputValue}`);
      } else if (output.OutputKey === 'UserPoolId') {
        console.log(`👥 User Pool ID: ${output.OutputValue}`);
      } else if (output.OutputKey === 'UserPoolClientId') {
        console.log(`📱 User Pool Client ID: ${output.OutputValue}`);
      } else if (output.OutputKey === 'UsersTableName') {
        console.log(`🗄️ Users Table: ${output.OutputValue}`);
      } else if (output.OutputKey === 'TranslationsTableName') {
        console.log(`📚 Translations Table: ${output.OutputValue}`);
      } else if (output.OutputKey === 'DashboardName') {
        console.log(`📊 CloudWatch Dashboard: ${output.OutputValue}`);
      }
    }
  } else {
    console.log(`\n⚠️  Main stack ${mainStackName} not found or has no outputs.`);
    console.log('   This is normal if you only deployed the hosted zones stack.');
  }

  console.log('\n📱 Next Steps:');
  console.log('   1. Add NS record in Squarespace DNS for the hosted zone');
  console.log('   2. Wait for DNS propagation (5-10 minutes)');
  console.log('   3. Deploy the main application stack');
  console.log('   4. Test the API endpoints');

  console.log('\n🔗 Useful URLs:');
  console.log('   - Squarespace DNS: https://www.squarespace.com/domain-management');
  console.log('   - AWS Console: https://console.aws.amazon.com/route53');
  console.log('   - DNS Checker: https://www.whatsmydns.net/');
}

main();
