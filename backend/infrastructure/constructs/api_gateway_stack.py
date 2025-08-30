"""API Gateway stack for GenZ Translation App."""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_iam as iam,
    Duration,
    RemovalPolicy,
)
from constructs import Construct


class ApiGatewayStack(Stack):
    """API Gateway infrastructure stack."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_stack,
        cognito_stack,
        environment: str = "dev",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.lambda_stack = lambda_stack
        self.cognito_stack = cognito_stack
        self.environment = environment

        # Lambda Authorizer
        self.authorizer = apigateway.TokenAuthorizer(
            self,
            "GenZAuthorizer",
            handler=self.lambda_stack.authorizer_lambda,
            identity_source="method.request.header.Authorization",
            results_cache_ttl=Duration.minutes(5),
        )

        # API Gateway
        self.api = apigateway.RestApi(
            self,
            "LingibleAPI",
            rest_api_name=f"lingible-api-{environment}",
            description="Lingible API",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],  # Update for production
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
                allow_credentials=True,
                max_age=Duration.days(1),
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=environment,
                throttling_rate_limit=1000,
                throttling_burst_limit=500,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
            ),
            removal_policy=RemovalPolicy.DESTROY,  # For development
        )

        # Health Check Endpoint (Public)
        health_resource = self.api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.lambda_stack.health_lambda),
            authorization_type=apigateway.AuthorizationType.NONE,
        )

        # Translation Endpoint (Authenticated)
        translate_resource = self.api.root.add_resource("translate")
        translate_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.lambda_stack.translate_lambda),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.authorizer,
        )

        # Translation History Endpoints (Authenticated)
        translations_resource = self.api.root.add_resource("translations")

        # GET /translations
        translations_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.lambda_stack.translation_history_lambda),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.authorizer,
        )

        # DELETE /translations
        translations_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.lambda_stack.delete_all_translations_lambda),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.authorizer,
        )

        # DELETE /translations/{id}
        translation_resource = translations_resource.add_resource("{translation_id}")
        translation_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.lambda_stack.delete_translation_lambda),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.authorizer,
        )

        # User Endpoints (Authenticated)
        user_resource = self.api.root.add_resource("user")

        # GET /user/profile
        profile_resource = user_resource.add_resource("profile")
        profile_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.lambda_stack.user_profile_lambda),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.authorizer,
        )

        # GET /user/usage
        usage_resource = user_resource.add_resource("usage")
        usage_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.lambda_stack.user_usage_lambda),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.authorizer,
        )

        # POST /user/upgrade
        upgrade_resource = user_resource.add_resource("upgrade")
        upgrade_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.lambda_stack.user_upgrade_lambda),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.authorizer,
        )

        # Webhook Endpoints (Public - for Apple/Google)
        webhook_resource = self.api.root.add_resource("webhook")

        # POST /webhook/apple
        apple_webhook_resource = webhook_resource.add_resource("apple")
        apple_webhook_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.lambda_stack.apple_webhook_lambda),
            authorization_type=apigateway.AuthorizationType.NONE,
        )

        # Add request/response models for better API documentation
        self._add_api_models()

        # Add usage plan and API key (optional)
        self._add_usage_plan()

    def _add_api_models(self):
        """Add request/response models for API documentation."""

        # Translation Request Model
        translation_request_model = self.api.add_model(
            "TranslationRequest",
            model_name="TranslationRequest",
            content_type="application/json",
            schema=apigateway.JsonSchema(
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "text": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Text to translate",
                        min_length=1,
                        max_length=1000,
                    ),
                    "direction": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Translation direction",
                        enum=["genz_to_english", "english_to_genz"],
                    ),
                },
                required=["text", "direction"],
            ),
        )

        # Translation Response Model
        translation_response_model = self.api.add_model(
            "TranslationResponse",
            model_name="TranslationResponse",
            content_type="application/json",
            schema=apigateway.JsonSchema(
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "translation_id": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Unique translation ID",
                    ),
                    "original_text": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Original text",
                    ),
                    "translated_text": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Translated text",
                    ),
                    "direction": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Translation direction",
                    ),
                    "confidence_score": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.NUMBER,
                        description="Translation confidence score",
                    ),
                    "created_at": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Translation timestamp",
                    ),
                },
            ),
        )

        # Error Response Model
        error_response_model = self.api.add_model(
            "ErrorResponse",
            model_name="ErrorResponse",
            content_type="application/json",
            schema=apigateway.JsonSchema(
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "success": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.BOOLEAN,
                        description="Always false for error responses",
                    ),
                    "message": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Human-readable error message",
                    ),
                    "error_code": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Application-specific error code",
                    ),
                    "status_code": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.INTEGER,
                        description="HTTP status code",
                    ),
                    "timestamp": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        description="Error timestamp",
                    ),
                },
            ),
        )

    def _add_usage_plan(self):
        """Add usage plan for API rate limiting."""

        # Create usage plan
        usage_plan = self.api.add_usage_plan(
            "LingibleUsagePlan",
            name=f"Lingible API Usage Plan - {environment}",
            description="Usage plan for Lingible API",
            throttle=apigateway.ThrottleSettings(
                rate_limit=1000,
                burst_limit=500,
            ),
            quota=apigateway.QuotaSettings(
                limit=1000000,  # 1M requests per month
                period=apigateway.Period.MONTH,
            ),
        )

        # Associate usage plan with API stage
        usage_plan.add_api_stage(
            stage=self.api.deployment_stage,
        )

        # Create API key (optional - for client identification)
        api_key = self.api.add_api_key(
            "LingibleAPIKey",
            api_key_name=f"lingible-api-key-{environment}",
            description="API key for Lingible API",
        )

        # Associate API key with usage plan
        usage_plan.add_api_key(api_key)
