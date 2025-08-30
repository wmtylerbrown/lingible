"""Monitoring stack for Lingible."""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_logs as logs,
    aws_iam as iam,
    Duration,
    RemovalPolicy,
)
from constructs import Construct


class MonitoringStack(Stack):
    """Monitoring infrastructure stack."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_stack,
        api_gateway_stack,
        environment: str = "dev",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.lambda_stack = lambda_stack
        self.api_gateway_stack = api_gateway_stack
        self.environment = environment

        # SNS Topic for alerts
        self.alerts_topic = sns.Topic(
            self,
            "LingibleAlertsTopic",
            topic_name=f"lingible-alerts-{environment}",
            display_name="Lingible Alerts",
        )

        # Add email subscription (update for production)
        # self.alerts_topic.add_subscription(
        #     sns_subscriptions.EmailSubscription("alerts@genzapp.com")
        # )

        # CloudWatch Dashboard
        self.dashboard = cloudwatch.Dashboard(
            self,
            "LingibleDashboard",
            dashboard_name=f"Lingible-Dashboard-{environment}",
        )

        # Lambda Monitoring
        self._add_lambda_monitoring()

        # API Gateway Monitoring
        self._add_api_gateway_monitoring()

        # Database Monitoring
        self._add_database_monitoring()

    def _add_lambda_monitoring(self):
        """Add Lambda function monitoring."""

        # Common Lambda metrics
        lambda_metrics = [
            ("Duration", "Average Duration", "Average"),
            ("Duration", "Maximum Duration", "Maximum"),
            ("Errors", "Error Count", "Sum"),
            ("Invocations", "Invocation Count", "Sum"),
            ("Throttles", "Throttle Count", "Sum"),
        ]

        for metric_name, display_name, stat in lambda_metrics:
            # Create metric for all Lambda functions
            metric = cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name=metric_name,
                statistic=stat,
                period=Duration.minutes(5),
            )

            # Add to dashboard
            self.dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title=f"{display_name} - All Lambda Functions",
                    left=[metric],
                    width=12,
                    height=6,
                )
            )

        # Lambda-specific monitoring for critical functions
        critical_functions = [
            ("translate", "Translation Service"),
            ("authorizer", "API Authorizer"),
            ("user-data-cleanup", "User Data Cleanup"),
        ]

        for func_name, display_name in critical_functions:
            # Error rate alarm
            error_alarm = cloudwatch.Alarm(
                self,
                f"{func_name}ErrorAlarm",
                alarm_name=f"{func_name}-error-rate-{environment}",
                metric=cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    statistic="Sum",
                    period=Duration.minutes(5),
                    dimensions_map={"FunctionName": f"lingible-{func_name}-{environment}"},
                ),
                threshold=5,
                evaluation_periods=2,
                alarm_description=f"High error rate for {display_name}",
            )

            # Duration alarm
            duration_alarm = cloudwatch.Alarm(
                self,
                f"{func_name}DurationAlarm",
                alarm_name=f"{func_name}-duration-{environment}",
                metric=cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    statistic="Average",
                    period=Duration.minutes(5),
                    dimensions_map={"FunctionName": f"lingible-{func_name}-{environment}"},
                ),
                threshold=25000,  # 25 seconds
                evaluation_periods=2,
                alarm_description=f"High duration for {display_name}",
            )

            # Add alarms to SNS topic
            error_alarm.add_alarm_action(
                cw_actions.SnsAction(self.alerts_topic)
            )
            duration_alarm.add_alarm_action(
                cw_actions.SnsAction(self.alerts_topic)
            )

    def _add_api_gateway_monitoring(self):
        """Add API Gateway monitoring."""

        # API Gateway metrics
        api_metrics = [
            ("Count", "Request Count", "Sum"),
            ("4XXError", "4XX Error Count", "Sum"),
            ("5XXError", "5XX Error Count", "Sum"),
            ("Latency", "API Latency", "Average"),
        ]

        for metric_name, display_name, stat in api_metrics:
            metric = cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name=metric_name,
                statistic=stat,
                period=Duration.minutes(5),
                dimensions_map={
                    "ApiName": f"lingible-api-{environment}",
                    "Stage": environment,
                },
            )

            self.dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title=f"{display_name} - API Gateway",
                    left=[metric],
                    width=12,
                    height=6,
                )
            )

        # API Gateway error rate alarm
        error_alarm = cloudwatch.Alarm(
            self,
            "ApiGatewayErrorAlarm",
            alarm_name=f"api-gateway-error-rate-{environment}",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                statistic="Sum",
                period=Duration.minutes(5),
                dimensions_map={
                    "ApiName": f"lingible-api-{environment}",
                    "Stage": environment,
                },
            ),
            threshold=10,
            evaluation_periods=2,
            alarm_description="High 5XX error rate for API Gateway",
        )

        error_alarm.add_alarm_action(
            cw_actions.SnsAction(self.alerts_topic)
        )

        # API Gateway latency alarm
        latency_alarm = cloudwatch.Alarm(
            self,
            "ApiGatewayLatencyAlarm",
            alarm_name=f"api-gateway-latency-{environment}",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Latency",
                statistic="Average",
                period=Duration.minutes(5),
                dimensions_map={
                    "ApiName": f"lingible-api-{environment}",
                    "Stage": environment,
                },
            ),
            threshold=5000,  # 5 seconds
            evaluation_periods=2,
            alarm_description="High latency for API Gateway",
        )

        latency_alarm.add_alarm_action(
            cw_actions.SnsAction(self.alerts_topic)
        )

    def _add_database_monitoring(self):
        """Add DynamoDB monitoring."""

        # DynamoDB metrics
        db_metrics = [
            ("ConsumedReadCapacityUnits", "Read Capacity Units", "Sum"),
            ("ConsumedWriteCapacityUnits", "Write Capacity Units", "Sum"),
            ("ThrottledRequests", "Throttled Requests", "Sum"),
            ("SystemErrors", "System Errors", "Sum"),
        ]

        # Monitor both tables
        for table_name in [f"lingible-users-{environment}", f"lingible-translations-{environment}"]:
            for metric_name, display_name, stat in db_metrics:
                metric = cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name=metric_name,
                    statistic=stat,
                    period=Duration.minutes(5),
                    dimensions_map={"TableName": table_name},
                )

                self.dashboard.add_widgets(
                    cloudwatch.GraphWidget(
                        title=f"{display_name} - {table_name}",
                        left=[metric],
                        width=12,
                        height=6,
                    )
                )

        # DynamoDB throttling alarm
        throttling_alarm = cloudwatch.Alarm(
            self,
            "DynamoDBThrottlingAlarm",
            alarm_name=f"dynamodb-throttling-{environment}",
            metric=cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="ThrottledRequests",
                statistic="Sum",
                period=Duration.minutes(5),
                dimensions_map={"TableName": f"lingible-users-{environment}"},
            ),
            threshold=10,
            evaluation_periods=2,
            alarm_description="High throttling for DynamoDB",
        )

        throttling_alarm.add_alarm_action(
            cw_actions.SnsAction(self.alerts_topic)
        )

        # DynamoDB system errors alarm
        system_errors_alarm = cloudwatch.Alarm(
            self,
            "DynamoDBSystemErrorsAlarm",
            alarm_name=f"dynamodb-system-errors-{environment}",
            metric=cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="SystemErrors",
                statistic="Sum",
                period=Duration.minutes(5),
                dimensions_map={"TableName": f"lingible-users-{environment}"},
            ),
            threshold=5,
            evaluation_periods=2,
            alarm_description="System errors for DynamoDB",
        )

        system_errors_alarm.add_alarm_action(
            cw_actions.SnsAction(self.alerts_topic)
        )

        # Add business metrics dashboard
        self._add_business_metrics()

    def _add_business_metrics(self):
        """Add business-specific metrics dashboard."""

        # Custom business metrics widget
        business_widget = cloudwatch.TextWidget(
            markdown="""
# Business Metrics

## User Activity
- **Daily Active Users**: [Custom metric needed]
- **Translation Volume**: [Custom metric needed]
- **Premium Conversion Rate**: [Custom metric needed]

## Performance
- **Translation Success Rate**: [Custom metric needed]
- **Average Response Time**: [Custom metric needed]
- **Error Rate by Endpoint**: [Custom metric needed]

## Cost
- **Lambda Invocations**: [CloudWatch metric]
- **DynamoDB Read/Write Units**: [CloudWatch metric]
- **API Gateway Requests**: [CloudWatch metric]
            """,
            width=24,
            height=8,
        )

        self.dashboard.add_widgets(business_widget)
