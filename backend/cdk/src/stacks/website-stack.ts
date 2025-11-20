import { CfnOutput, RemovalPolicy, Stack } from 'aws-cdk-lib';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';
import { BaseStackProps } from '../types';

export class WebsiteStack extends Stack {
  public readonly distribution: cloudfront.Distribution;
  public readonly bucket: s3.Bucket;

  public constructor(scope: Construct, id: string, props: BaseStackProps) {
    super(scope, id, props);

    const environment = props.envContext.environment;
    const projectRoot = path.resolve(__dirname, '../../../..');
    const websiteBuildPath = path.join(projectRoot, 'website', 'build');
    const domain = environment === 'prod' ? 'lingible.com' : `${environment}.lingible.com`;

    this.bucket = new s3.Bucket(this, 'WebsiteBucket', {
      bucketName: `lingible-website-${environment}-${this.account}-${this.region}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      publicReadAccess: false,
      autoDeleteObjects: false,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    const certificate = new acm.Certificate(this, 'WebsiteCertificate', {
      domainName: domain,
      subjectAlternativeNames: environment === 'prod' ? [`www.${domain}`] : undefined,
      validation: acm.CertificateValidation.fromDns(),
    });

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
      domainNames: environment === 'prod' ? [domain, `www.${domain}`] : [domain],
      certificate,
    });

    new s3deploy.BucketDeployment(this, 'WebsiteDeployment', {
      sources: [
        s3deploy.Source.asset(websiteBuildPath, {
          assetHash: this.calculateAssetHash(websiteBuildPath),
        }),
      ],
      destinationBucket: this.bucket,
      prune: true,
      retainOnDelete: false,
      distribution: this.distribution,
      distributionPaths: ['/index.html', '/terms.html', '/privacy.html', '/*.png', '/*.js'],
    });

    new CfnOutput(this, 'WebsiteURL', {
      value: `https://${domain}`,
    });

    new CfnOutput(this, 'CloudFrontURL', {
      value: `https://${this.distribution.distributionDomainName}`,
    });

    new CfnOutput(this, 'BucketName', {
      value: this.bucket.bucketName,
    });

    new CfnOutput(this, 'DistributionId', {
      value: this.distribution.distributionId,
    });

    const dnsInstruction =
      environment === 'prod'
        ? `Squarespace: point lingible.com (A) and www.lingible.com (CNAME) to ${this.distribution.distributionDomainName}.`
        : `Create a CNAME for ${domain} pointing to ${this.distribution.distributionDomainName}.`;

    new CfnOutput(this, 'ManualDNSInstructions', {
      value: `${dnsInstruction} CloudFormation will wait for ACM DNS validation records that you add manually in Squarespace.`,
    });
  }

  private calculateAssetHash(buildDir: string): string {
    if (!fs.existsSync(buildDir)) {
      return `missing-${Date.now()}`;
    }

    const entries = fs.readdirSync(buildDir).sort();
    const hashes = entries
      .filter((entry) => fs.statSync(path.join(buildDir, entry)).isFile())
      .map((entry) => {
        const content = fs.readFileSync(path.join(buildDir, entry), { encoding: 'utf8' });
        return crypto.createHash('sha256').update(content, 'utf8').digest('hex').substring(0, 8);
      });

    return hashes.join(':') || `empty-${Date.now()}`;
  }
}
