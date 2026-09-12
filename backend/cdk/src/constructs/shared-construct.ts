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
    // No `bundling` block: `backend/cdk/scripts/build-lambda-packages.js` already installs this
    // layer's dependencies into `assetPath/python` itself, via a host-side `uv pip install
    // --python-platform aarch64-manylinux2014 --only-binary=:all:` (pure wheel resolution, no
    // compilation) -- so neither `cdk synth` nor `cdk deploy` needs a Docker daemon (see
    // specs/backend-python-toolchain.md). `requirements.txt` (also written by that script, for
    // its own hash-based rebuild check) is excluded from the asset; only `python/` belongs in a
    // Lambda layer.
    return new lambda.LayerVersion(this, id, {
      layerVersionName: layerName,
      code: lambda.Code.fromAsset(assetPath, {
        exclude: ['requirements.txt'],
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
