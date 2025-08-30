#!/usr/bin/env python3
"""CDK app for Lingible infrastructure."""

import aws_cdk as cdk
from stacks.lingible_stack import LingibleStack

app = cdk.App()

# Get environment from context or default to 'dev'
environment = app.node.try_get_context("environment") or "dev"

# Main application stack
LingibleStack(
    app,
    f"Lingible-{environment.title()}",
    description=f"Lingible - {environment.title()} Environment",
    environment=environment,
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

# Add tags to all resources
cdk.Tags.of(app).add("Application", "Lingible")
cdk.Tags.of(app).add("Environment", environment)
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
