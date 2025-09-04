import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';

export interface WebsiteStackProps extends cdk.StackProps {
  environment: string;
  domainName?: string;
}

export class WebsiteStack extends cdk.Stack {
  public readonly distribution: cloudfront.Distribution;
  public readonly bucket: s3.Bucket;

  private calculateWebAssetHash(): string {
    const buildDir = path.join(__dirname, '../../website/build');
    let hash = '';

    try {
      // Use content-based hashing instead of modification times
      if (fs.existsSync(buildDir)) {
        const files = fs.readdirSync(buildDir).sort();
        for (const file of files) {
          const filePath = path.join(buildDir, file);
          if (fs.statSync(filePath).isFile()) {
            const content = fs.readFileSync(filePath);
            const crypto = require('crypto');
            const fileHash = crypto.createHash('sha256').update(content).digest('hex').substring(0, 8);
            hash += `:${file}:${fileHash}`;
          }
        }
      }
    } catch (error) {
      console.warn('Could not calculate web asset hash:', error);
      // Use environment as fallback hash
      hash = `env-${this.environment}`;
    }

    return hash;
  }

  constructor(scope: Construct, id: string, props: WebsiteStackProps) {
    super(scope, id, props);

    const { environment, domainName } = props;

    // Determine domain name based on environment if not provided
    const finalDomainName = domainName || `${environment}.lingible.com`;

    // S3 bucket for website hosting (private)
    this.bucket = new s3.Bucket(this, 'WebsiteBucket', {
      bucketName: `lingible-website-${environment}-${this.account}-${this.region}`,
      publicReadAccess: false, // Keep bucket private
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL, // Block all public access
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      autoDeleteObjects: false,
    });

    // Get hosted zone for DNS records
    const hostedZone = route53.HostedZone.fromLookup(this, 'HostedZone', {
      domainName: `${environment}.lingible.com`,
    });

    // Create SSL certificate for the domain
    const certificate = new acm.Certificate(this, 'WebsiteCertificate', {
      domainName: finalDomainName,
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    // CloudFront distribution
    this.distribution = new cloudfront.Distribution(this, 'WebsiteDistribution', {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(this.bucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      errorResponses: [
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
        },
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
        },
      ],
      domainNames: [finalDomainName],
      certificate: certificate,
    });


    // Create Route53 A record pointing to CloudFront
    new route53.ARecord(this, 'WebsiteAliasRecord', {
      zone: hostedZone,
      recordName: finalDomainName,
      target: route53.RecordTarget.fromAlias(new route53Targets.CloudFrontTarget(this.distribution)),
    });

    // Deploy website files to S3 with conditional CloudFront cache invalidation
    new s3deploy.BucketDeployment(this, 'WebsiteDeployment', {
      sources: [s3deploy.Source.asset('../../website/build', {
        assetHash: this.calculateWebAssetHash()
      })],
      destinationBucket: this.bucket,
      destinationKeyPrefix: '', // Deploy to root of bucket
      prune: true, // Remove files that don't exist in source
      retainOnDelete: false,
      distribution: this.distribution, // Automatically invalidate CloudFront cache
      distributionPaths: ['/index.html', '/terms.html', '/privacy.html', '/*.png', '/*.js'], // Only invalidate specific paths that might change
      memoryLimit: 512 // Reduce memory usage
    });

    // Outputs
    new cdk.CfnOutput(this, 'WebsiteURL', {
      value: `https://${finalDomainName}`,
      description: 'Website URL',
    });

    new cdk.CfnOutput(this, 'CloudFrontURL', {
      value: `https://${this.distribution.distributionDomainName}`,
      description: 'CloudFront Distribution URL',
    });

    new cdk.CfnOutput(this, 'BucketName', {
      value: this.bucket.bucketName,
      description: 'S3 Bucket Name',
    });

    new cdk.CfnOutput(this, 'DistributionId', {
      value: this.distribution.distributionId,
      description: 'CloudFront Distribution ID',
    });

    new cdk.CfnOutput(this, 'DomainName', {
      value: finalDomainName,
      description: 'Website Domain Name',
    });
  }
}
