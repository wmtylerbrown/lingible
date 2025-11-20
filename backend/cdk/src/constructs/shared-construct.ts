import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { BaseStackProps, SharedResourceReferences } from '../types';

export class SharedConstruct extends Construct {
  public readonly shared: SharedResourceReferences;

  public constructor(scope: Construct, id: string, props: BaseStackProps) {
    super(scope, id);

    const layers = {
      core: this.createDependencyLayer('CoreLayer', `lingible-core-layer-${props.envContext.environment}`, 'artifacts/lambda-core-layer'),
      receiptValidation: this.createDependencyLayer('ReceiptValidationLayer', `lingible-receipt-validation-layer-${props.envContext.environment}`, 'artifacts/lambda-receipt-validation-layer'),
      slangValidation: this.createDependencyLayer('SlangValidationLayer', `lingible-slang-validation-layer-${props.envContext.environment}`, 'artifacts/lambda-slang-validation-layer'),
      shared: this.createSourceLayer('SharedLayer', `lingible-shared-layer-${props.envContext.environment}`, 'artifacts/lambda-layer'),
    };

    this.shared = {
      environment: props.envContext.environment,
      layers,
    };
  }

  private createDependencyLayer(id: string, layerName: string, assetPath: string): lambda.LayerVersion {
    return new lambda.LayerVersion(this, id, {
      layerVersionName: layerName,
      code: lambda.Code.fromAsset(assetPath, {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          platform: 'linux/arm64',
          command: [
            'bash',
            '-c',
            'rm -rf /asset-output/python && pip install --platform manylinux2014_aarch64 --implementation cp --python-version 3.13 --only-binary=:all: --upgrade --target /asset-output/python -r requirements.txt',
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: `${layerName} dependencies for Lingible Lambda functions`,
    });
  }

  private createSourceLayer(id: string, layerName: string, assetPath: string): lambda.LayerVersion {
    return new lambda.LayerVersion(this, id, {
      layerVersionName: layerName,
      code: lambda.Code.fromAsset(assetPath, {
        exclude: [
          '**/__pycache__/**',
          '**/*.pyc',
          '**/*.pyo',
          '**/*.pyd',
          '**/.pytest_cache/**',
          '**/.coverage',
          '**/.mypy_cache/**',
        ],
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Shared Python services, repositories, and models for Lingible Lambda functions',
    });
  }
}
