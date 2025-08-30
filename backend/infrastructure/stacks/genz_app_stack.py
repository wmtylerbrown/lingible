"""Main CDK stack for Lingible."""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_logs as logs,
    aws_sqs as sqs,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct

from .constructs.database_stack import DatabaseStack
from .constructs.cognito_stack import CognitoStack
from .constructs.api_gateway_stack import ApiGatewayStack
from .constructs.lambda_stack import LambdaStack
from .constructs.monitoring_stack import MonitoringStack


class LingibleStack(Stack):
    """Main stack for Lingible infrastructure."""

    def __init__(self, scope: Construct, construct_id: str, environment: str = "dev", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment

        # Database Stack
        self.database_stack = DatabaseStack(self, "Database", environment=environment)

        # Cognito Stack
        self.cognito_stack = CognitoStack(self, "Cognito", environment=environment)

        # Lambda Stack
        self.lambda_stack = LambdaStack(
            self,
            "Lambda",
            database_stack=self.database_stack,
            cognito_stack=self.cognito_stack,
            environment=environment,
        )

        # API Gateway Stack
        self.api_gateway_stack = ApiGatewayStack(
            self,
            "ApiGateway",
            lambda_stack=self.lambda_stack,
            cognito_stack=self.cognito_stack,
            environment=environment,
        )

        # Monitoring Stack
        self.monitoring_stack = MonitoringStack(
            self,
            "Monitoring",
            lambda_stack=self.lambda_stack,
            api_gateway_stack=self.api_gateway_stack,
            environment=environment,
        )

        # Outputs
        CfnOutput(
            self,
            "UserPoolId",
            value=self.cognito_stack.user_pool.user_pool_id,
            description="Cognito User Pool ID",
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.cognito_stack.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
        )

        CfnOutput(
            self,
            "ApiGatewayUrl",
            value=self.api_gateway_stack.api.url,
            description="API Gateway URL",
        )

        CfnOutput(
            self,
            "UsersTableName",
            value=self.database_stack.users_table.table_name,
            description="DynamoDB Users Table Name",
        )

        CfnOutput(
            self,
            "TranslationsTableName",
            value=self.database_stack.translations_table.table_name,
            description="DynamoDB Translations Table Name",
        )
