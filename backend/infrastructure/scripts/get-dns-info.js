#!/usr/bin/env node

const { execSync } = require('child_process');

function getDnsInfo(environment) {
  const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';

  console.log(`🌐 DNS Information for ${environment} environment`);
  console.log('==========================================\n');

  try {
    // Get hosted zone information
    console.log('📋 Hosted Zone Information:');
    const hostedZoneOutput = execSync(`aws route53 list-hosted-zones --query "HostedZones[?Name=='${environment}.lingible.com.']" --output table --region ${region}`, { encoding: 'utf8' });
    console.log(hostedZoneOutput);

    // Get name servers
    console.log('\n🔗 Name Servers:');
    const nameServersOutput = execSync(`aws route53 get-hosted-zone --id $(aws route53 list-hosted-zones --query "HostedZones[?Name=='${environment}.lingible.com.'].Id" --output text --region ${region}) --query "DelegationSet.NameServers" --output table --region ${region}`, { encoding: 'utf8' });
    console.log(nameServersOutput);

    // Get DNS records
    console.log('\n📝 DNS Records:');
    const recordsOutput = execSync(`aws route53 list-resource-record-sets --hosted-zone-id $(aws route53 list-hosted-zones --query "HostedZones[?Name=='${environment}.lingible.com.'].Id" --output text --region ${region}) --query "ResourceRecordSets[?Type=='A' || Type=='CNAME' || Type=='AAAA']" --output table --region ${region}`, { encoding: 'utf8' });
    console.log(recordsOutput);

    console.log('\n💡 Next Steps:');
    console.log('1. Copy the name servers above');
    console.log('2. Add NS record in Squarespace DNS for ${environment}.lingible.com');
    console.log('3. Point the NS record to the name servers listed above');

  } catch (error) {
    console.error('❌ Error getting DNS information:', error.message);
    console.log('\n🔧 Troubleshooting:');
    console.log('1. Make sure AWS CLI is configured');
    console.log('2. Verify you have Route53 permissions');
    console.log('3. Check that the hosted zone exists');
    console.log('4. Try running: npm run deploy:hosted-zones:${environment}');
  }
}

function main() {
  const environment = process.argv[2];

  if (!environment || !['dev', 'prod'].includes(environment)) {
    console.log('Usage: npm run get-dns-info <environment>');
    console.log('');
    console.log('Environment: dev or prod');
    console.log('');
    console.log('Examples:');
    console.log('  npm run get-dns-info dev');
    console.log('  npm run get-dns-info prod');
    process.exit(1);
  }

  getDnsInfo(environment);
}

main();
