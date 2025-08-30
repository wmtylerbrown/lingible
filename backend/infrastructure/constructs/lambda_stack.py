"""Lambda stack for GenZ Translation App."""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    Duration,
    RemovalPolicy,
)
from constructs import Construct


class LambdaStack(Stack):
    """Lambda infrastructure stack."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        database_stack,
        cognito_stack,
        environment: str = "dev",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.database_stack = database_stack
        self.cognito_stack = cognito_stack
        self.environment = environment

        # Common Lambda configuration
        lambda_config = {
            "runtime": lambda_.Runtime.PYTHON_3_11,
            "timeout": Duration.seconds(30),
            "memory_size": 512,
            "log_retention": logs.RetentionDays.ONE_WEEK,
            "removal_policy": RemovalPolicy.DESTROY,  # For development
        }

        # Common environment variables
        common_env = {
            "POWERTOOLS_SERVICE_NAME": "genz-translation-app",
            "LOG_LEVEL": "INFO",
            "USERS_TABLE": self.database_stack.users_table.table_name,
            "TRANSLATIONS_TABLE": self.database_stack.translations_table.table_name,
            "USER_POOL_ID": self.cognito_stack.user_pool.user_pool_id,
            "USER_POOL_CLIENT_ID": self.cognito_stack.user_pool_client.user_pool_client_id,
            "IDENTITY_POOL_ID": self.cognito_stack.identity_pool.ref,
        }

        # Common IAM policy for Lambda functions
        lambda_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                    ],
                    resources=[
                        self.database_stack.users_table.table_arn,
                        self.database_stack.translations_table.table_arn,
                        f"{self.database_stack.users_table.table_arn}/index/*",
                        f"{self.database_stack.translations_table.table_arn}/index/*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                    ],
                    resources=["*"],
                ),
            ]
        )

        # Authorizer Lambda
        self.authorizer_lambda = lambda_.Function(
            self,
            "AuthorizerLambda",
            function_name=f"lingible-authorizer-{environment}",
            handler="src.handlers.authorizer.authorizer.lambda_handler",
            code=lambda_.Code.from_asset("../src"),
            environment={
                **common_env,
                "USER_POOL_ID": self.cognito_stack.user_pool.user_pool_id,
                "USER_POOL_REGION": self.region,
            },
            **lambda_config,
        )

        # Add authorizer-specific policies
        self.authorizer_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:GetUser",
                    "cognito-idp:ListUsers",
                ],
                resources=[self.cognito_stack.user_pool.user_pool_arn],
            )
        )

        # API Handlers
        self.translate_lambda = lambda_.Function(
            self,
            "TranslateLambda",
            function_name=f"lingible-translate-{environment}",
            handler="src.handlers.translate_api.translate_api_handler.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.user_profile_lambda = lambda_.Function(
            self,
            "UserProfileLambda",
            function_name=f"lingible-user-profile-{environment}",
            handler="src.handlers.user_profile_api.user_profile_api_handler.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.user_usage_lambda = lambda_.Function(
            self,
            "UserUsageLambda",
            function_name=f"lingible-user-usage-{environment}",
            handler="src.handlers.user_usage_api.user_usage_api_handler.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.user_upgrade_lambda = lambda_.Function(
            self,
            "UserUpgradeLambda",
            function_name=f"lingible-user-upgrade-{environment}",
            handler="src.handlers.user_upgrade_api.user_upgrade_api_handler.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.translation_history_lambda = lambda_.Function(
            self,
            "TranslationHistoryLambda",
            function_name=f"lingible-translation-history-{environment}",
            handler="src.handlers.translation_history_api.get_translation_history.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.delete_translation_lambda = lambda_.Function(
            self,
            "DeleteTranslationLambda",
            function_name=f"lingible-delete-translation-{environment}",
            handler="src.handlers.translation_history_api.delete_translation.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.delete_all_translations_lambda = lambda_.Function(
            self,
            "DeleteAllTranslationsLambda",
            function_name=f"lingible-delete-all-translations-{environment}",
            handler="src.handlers.translation_history_api.delete_all_translations.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.health_lambda = lambda_.Function(
            self,
            "HealthLambda",
            function_name=f"lingible-health-{environment}",
            handler="src.handlers.health_api.health_api_handler.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        # Webhook Handlers
        self.apple_webhook_lambda = lambda_.Function(
            self,
            "AppleWebhookLambda",
            function_name=f"lingible-apple-webhook-{environment}",
            handler="src.handlers.apple_webhook.apple_webhook_handler.handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        # Cognito Triggers
        self.post_confirmation_lambda = lambda_.Function(
            self,
            "PostConfirmationLambda",
            function_name=f"lingible-post-confirmation-{environment}",
            handler="src.handlers.cognito_post_confirmation.cognito_post_confirmation.post_confirmation_handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.pre_authentication_lambda = lambda_.Function(
            self,
            "PreAuthenticationLambda",
            function_name=f"lingible-pre-authentication-{environment}",
            handler="src.handlers.cognito_pre_authentication.cognito_pre_authentication.pre_authentication_handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        self.pre_user_deletion_lambda = lambda_.Function(
            self,
            "PreUserDeletionLambda",
            function_name=f"lingible-pre-user-deletion-{environment}",
            handler="src.handlers.cognito_pre_user_deletion.cognito_pre_user_deletion.pre_user_deletion_handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        # Background Processing
        self.user_data_cleanup_lambda = lambda_.Function(
            self,
            "UserDataCleanupLambda",
            function_name=f"lingible-user-data-cleanup-{environment}",
            handler="src.handlers.user_data_cleanup.user_data_cleanup.cleanup_user_data_handler",
            code=lambda_.Code.from_asset("../src"),
            environment=common_env,
            **lambda_config,
        )

        # Add Cognito trigger permissions
        self.cognito_stack.user_pool.add_trigger(
            cognito.UserPoolOperation.POST_CONFIRMATION,
            self.post_confirmation_lambda,
        )

        self.cognito_stack.user_pool.add_trigger(
            cognito.UserPoolOperation.PRE_AUTHENTICATION,
            self.pre_authentication_lambda,
        )

        self.cognito_stack.user_pool.add_trigger(
            cognito.UserPoolOperation.PRE_USER_DELETION,
            self.pre_user_deletion_lambda,
        )

        # Grant Cognito permission to invoke Lambda functions
        self.post_confirmation_lambda.grant_invoke(self.cognito_stack.user_pool)
        self.pre_authentication_lambda.grant_invoke(self.cognito_stack.user_pool)
        self.pre_user_deletion_lambda.grant_invoke(self.cognito_stack.user_pool)

        # Add policies to all Lambda functions
        for lambda_func in [
            self.translate_lambda,
            self.user_profile_lambda,
            self.user_usage_lambda,
            self.user_upgrade_lambda,
            self.translation_history_lambda,
            self.delete_translation_lambda,
            self.delete_all_translations_lambda,
            self.health_lambda,
            self.apple_webhook_lambda,
            self.post_confirmation_lambda,
            self.pre_authentication_lambda,
            self.pre_user_deletion_lambda,
            self.user_data_cleanup_lambda,
        ]:
            lambda_func.role.attach_inline_policy(
                iam.Policy(self, f"{lambda_func.node.id}Policy", document=lambda_policy)
            )
