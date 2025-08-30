"""Database stack for Lingible."""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Duration,
)
from constructs import Construct


class DatabaseStack(Stack):
    """Database infrastructure stack."""

    def __init__(self, scope: Construct, construct_id: str, environment: str = "dev", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment

        # Users Table (Single-table design for users, subscriptions, and usage)
        self.users_table = dynamodb.Table(
            self,
            "UsersTable",
            table_name=f"lingible-users-{environment}",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For development - change to RETAIN for production
            point_in_time_recovery=True,
            time_to_live_attribute="ttl",
        )

        # Add GSI for email lookups
        self.users_table.add_global_secondary_index(
            index_name="EmailIndex",
            partition_key=dynamodb.Attribute(
                name="email", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for username lookups
        self.users_table.add_global_secondary_index(
            index_name="UsernameIndex",
            partition_key=dynamodb.Attribute(
                name="username", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for subscription status lookups
        self.users_table.add_global_secondary_index(
            index_name="SubscriptionStatusIndex",
            partition_key=dynamodb.Attribute(
                name="subscription_status", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for transaction ID lookups
        self.users_table.add_global_secondary_index(
            index_name="TransactionIndex",
            partition_key=dynamodb.Attribute(
                name="transaction_id", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for usage analytics
        self.users_table.add_global_secondary_index(
            index_name="UsageTierIndex",
            partition_key=dynamodb.Attribute(
                name="usage_tier", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="updated_at", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Translations Table
        self.translations_table = dynamodb.Table(
            self,
            "TranslationsTable",
            table_name=f"lingible-translations-{environment}",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            time_to_live_attribute="ttl",
        )

        # Add GSI for translation direction lookups
        self.translations_table.add_global_secondary_index(
            index_name="DirectionIndex",
            partition_key=dynamodb.Attribute(
                name="direction", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for model usage analytics
        self.translations_table.add_global_secondary_index(
            index_name="ModelIndex",
            partition_key=dynamodb.Attribute(
                name="model_used", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )
