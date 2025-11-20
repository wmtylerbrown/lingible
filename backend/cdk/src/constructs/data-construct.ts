import { RemovalPolicy } from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import {
  BaseStackProps,
  DataResourceReferences,
  SharedResourceReferences,
} from '../types';

export interface DataConstructProps extends BaseStackProps {
  readonly shared: SharedResourceReferences;
}

export class DataConstruct extends Construct {
  public readonly data: DataResourceReferences;
  private readonly usersTable: dynamodb.Table;
  private readonly translationsTable: dynamodb.Table;
  private readonly submissionsTable: dynamodb.Table;
  private readonly lexiconTable: dynamodb.Table;
  private readonly trendingTable: dynamodb.Table;
  private readonly lexiconBucket: s3.Bucket;

  public constructor(scope: Construct, id: string, props: DataConstructProps) {
    super(scope, id);

    const { envContext } = props;
    this.usersTable = this.createUsersTable(envContext);
    this.translationsTable = this.createTranslationsTable(envContext);
    this.submissionsTable = this.createSubmissionsTable(envContext);
    this.lexiconTable = this.createLexiconTable(envContext);
    this.trendingTable = this.createTrendingTable(envContext);
    this.lexiconBucket = this.createLexiconBucket(envContext);

    this.data = {
      environment: envContext.environment,
      usersTable: this.usersTable,
      translationsTable: this.translationsTable,
      submissionsTable: this.submissionsTable,
      lexiconTable: this.lexiconTable,
      trendingTable: this.trendingTable,
      lexiconBucket: this.lexiconBucket,
    };
  }

  private createUsersTable(envContext: DataConstructProps['envContext']): dynamodb.Table {
    return new dynamodb.Table(this, 'UsersTable', {
      tableName: envContext.infrastructure.tables.users_table.name,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
      timeToLiveAttribute: 'ttl',
    });
  }

  private createTranslationsTable(envContext: DataConstructProps['envContext']): dynamodb.Table {
    return new dynamodb.Table(this, 'TranslationsTable', {
      tableName: envContext.infrastructure.tables.translations_table.name,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
    });
  }

  private createSubmissionsTable(envContext: DataConstructProps['envContext']): dynamodb.Table {
    const table = new dynamodb.Table(this, 'SubmissionsTable', {
      tableName: envContext.infrastructure.tables.submissions_table.name,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
      timeToLiveAttribute: 'ttl',
    });

    table.addGlobalSecondaryIndex({
      indexName: 'SubmissionsStatusIndex',
      partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status_created_at', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.INCLUDE,
      nonKeyAttributes: ['submission_id', 'user_id', 'slang_term', 'context'],
    });

    table.addGlobalSecondaryIndex({
      indexName: 'SubmissionsByUserIndex',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'user_created_at', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.KEYS_ONLY,
    });

    table.addGlobalSecondaryIndex({
      indexName: 'SubmissionsByIdIndex',
      partitionKey: { name: 'submission_id', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    table.addGlobalSecondaryIndex({
      indexName: 'ValidationStatusIndex',
      partitionKey: { name: 'llm_validation_status', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.INCLUDE,
      nonKeyAttributes: ['submission_id', 'user_id', 'slang_term'],
    });

    return table;
  }

  private createLexiconTable(envContext: DataConstructProps['envContext']): dynamodb.Table {
    const table = new dynamodb.Table(this, 'LexiconTable', {
      tableName: envContext.infrastructure.tables.lexicon_table.name,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
    });

    table.addGlobalSecondaryIndex({
      indexName: 'LexiconSourceIndex',
      partitionKey: { name: 'source', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'term', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.KEYS_ONLY,
    });

    table.addGlobalSecondaryIndex({
      indexName: 'LexiconQuizDifficultyIndex',
      partitionKey: { name: 'quiz_difficulty', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'quiz_score', type: dynamodb.AttributeType.NUMBER },
      projectionType: dynamodb.ProjectionType.INCLUDE,
      nonKeyAttributes: ['term', 'gloss', 'examples', 'tags', 'is_quiz_eligible'],
    });

    table.addGlobalSecondaryIndex({
      indexName: 'LexiconQuizCategoryIndex',
      partitionKey: { name: 'quiz_category', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'quiz_score', type: dynamodb.AttributeType.NUMBER },
      projectionType: dynamodb.ProjectionType.INCLUDE,
      nonKeyAttributes: ['term', 'gloss', 'examples', 'tags', 'is_quiz_eligible'],
    });

    return table;
  }

  private createTrendingTable(envContext: DataConstructProps['envContext']): dynamodb.Table {
    const table = new dynamodb.Table(this, 'TrendingTable', {
      tableName: envContext.infrastructure.tables.trending_table.name,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
      timeToLiveAttribute: 'ttl',
    });

    table.addGlobalSecondaryIndex({
      indexName: 'TrendingActiveIndex',
      partitionKey: { name: 'is_active', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'popularity_score', type: dynamodb.AttributeType.NUMBER },
      projectionType: dynamodb.ProjectionType.INCLUDE,
      nonKeyAttributes: ['term', 'category', 'definition'],
    });

    table.addGlobalSecondaryIndex({
      indexName: 'TrendingCategoryIndex',
      partitionKey: { name: 'category', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'popularity_score', type: dynamodb.AttributeType.NUMBER },
      projectionType: dynamodb.ProjectionType.INCLUDE,
      nonKeyAttributes: ['term', 'definition', 'is_active'],
    });

    return table;
  }

  private createLexiconBucket(envContext: DataConstructProps['envContext']): s3.Bucket {
    return new s3.Bucket(this, 'LexiconBucket', {
      bucketName: envContext.backend.lexicon.s3_bucket,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });
  }
}
