"""Cognito stack for Lingible."""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    aws_lambda as lambda_,
    aws_iam as iam,
    Duration,
    RemovalPolicy,
)
from constructs import Construct


class CognitoStack(Stack):
    """Cognito infrastructure stack."""

    def __init__(self, scope: Construct, construct_id: str, environment: str = "dev", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment

        # User Pool
        self.user_pool = cognito.UserPool(
            self,
            "LingibleUserPool",
            user_pool_name=f"lingible-users-{environment}",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=True,
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True,
                ),
                given_name=cognito.StandardAttribute(
                    required=False,
                    mutable=True,
                ),
                family_name=cognito.StandardAttribute(
                    required=False,
                    mutable=True,
                ),
            ),
            custom_attributes={
                "user_tier": cognito.StringAttribute(
                    mutable=True,
                    min_len=1,
                    max_len=20,
                ),
                "subscription_id": cognito.StringAttribute(
                    mutable=True,
                    min_len=1,
                    max_len=100,
                ),
            },
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            user_verification=cognito.UserVerificationConfig(
                email_subject="Verify your email for GenZ Translation App",
                email_body="Thanks for signing up! Your verification code is {####}",
                email_style=cognito.VerificationEmailStyle.CODE,
            ),
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=True,
                otp=True,
            ),
            device_tracking=cognito.DeviceTracking(
                challenge_required_on_new_device=True,
                device_only_remembered_on_user_prompt=True,
            ),
            removal_policy=RemovalPolicy.DESTROY,  # For development - change to RETAIN for production
        )

        # Apple Identity Provider (Sign in with Apple)
        self.apple_provider = cognito.UserPoolIdentityProviderApple(
            self,
            "AppleIdentityProvider",
            user_pool=self.user_pool,
                               client_id="com.lingible.lingible",  # Your App ID from Apple Developer Console
            team_id="YOUR_APPLE_TEAM_ID",        # Replace with your Team ID
            key_id="YOUR_APPLE_KEY_ID",          # Replace with your Key ID
            private_key="YOUR_APPLE_PRIVATE_KEY", # Replace with your private key
            scopes=["email", "name"],
            attribute_request_method=cognito.AttributeRequestMethod.GET,
            attribute_mapping={
                "email": "email",
                "name": "name",
                "given_name": "given_name",
                "family_name": "family_name",
            }
        )

        # User Pool Client
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "LingibleUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name=f"lingible-client-{environment}",
            generate_secret=False,  # For public clients (mobile apps)
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                custom=True,
                admin_user_password=True,  # For admin-initiated auth
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=True,
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=["https://localhost:3000/callback"],  # Update for production
                logout_urls=["https://localhost:3000/logout"],      # Update for production
            ),
            # Add identity providers
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO,
                cognito.UserPoolClientIdentityProvider.APPLE,
            ],
            prevent_user_existence_errors=True,
            enable_token_revocation=True,
            refresh_token_validity=Duration.days(30),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
        )

        # Identity Pool (for AWS service access)
        self.identity_pool = cognito.CfnIdentityPool(
            self,
            "LingibleIdentityPool",
            identity_pool_name=f"lingible-identity-pool-{environment}",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=self.user_pool_client.user_pool_client_id,
                    provider_name=self.user_pool.user_pool_provider_name,
                )
            ],
        )

        # IAM roles for authenticated users
        self.authenticated_role = iam.Role(
            self,
            "CognitoAuthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
        )

        # IAM roles for unauthenticated users (if needed)
        self.unauthenticated_role = iam.Role(
            self,
            "CognitoUnauthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "unauthenticated"
                    }
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
        )

        # Attach roles to identity pool
        cognito.CfnIdentityPoolRoleAttachment(
            self,
            "IdentityPoolRoleAttachment",
            identity_pool_id=self.identity_pool.ref,
            roles={
                "authenticated": self.authenticated_role.role_arn,
                "unauthenticated": self.unauthenticated_role.role_arn,
            },
        )

        # Add policies to authenticated role
        self.authenticated_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )

        # Custom domain (optional - for production)
        # self.user_pool.add_domain(
        #     "GenZCustomDomain",
        #     custom_domain=cognito.CustomDomainConfig(
        #         domain_name="auth.genzapp.com",  # Update for production
        #         certificate=certificate,  # ACM certificate
        #     ),
        # )
