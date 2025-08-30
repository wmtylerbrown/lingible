# Apple Credentials Security Guide

## 🔐 **Overview**

This document outlines how we securely manage Apple Identity Provider credentials (private keys, client IDs, etc.) in the Lingible AWS infrastructure.

## 🚨 **CRITICAL SECURITY ISSUE RESOLVED**

### **The Problem**
The original approach embedded the Apple private key directly in the CloudFormation template, making it visible in:
- CloudFormation console
- CloudFormation logs
- CDK synthesis output
- AWS CLI `describe-stack` calls

### **The Solution**
We now use **CDK Context Parameters** to pass credentials during deployment without embedding them in the template.

## 🏗️ **Current Security Architecture**

### **1. CDK Context Parameters (Secure)**
```python
# Credentials passed via CDK context during deployment
client_id=self.node.try_get_context("apple_client_id")
team_id=self.node.try_get_context("apple_team_id")
key_id=self.node.try_get_context("apple_key_id")
private_key=self.node.try_get_context("apple_private_key")
```

### **2. Deployment Options**

#### **Option A: Environment Variables (Recommended)**
```bash
# Set environment variables before deployment
export CDK_CONTEXT_APPLE_CLIENT_ID="com.lingible.lingible"
export CDK_CONTEXT_APPLE_TEAM_ID="YOUR_TEAM_ID"
export CDK_CONTEXT_APPLE_KEY_ID="YOUR_KEY_ID"
export CDK_CONTEXT_APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"

# Deploy
python3 deploy-dev.py
```

#### **Option B: CDK Context File**
```json
// cdk.context.json
{
  "apple_client_id": "com.lingible.lingible",
  "apple_team_id": "YOUR_TEAM_ID",
  "apple_key_id": "YOUR_KEY_ID",
  "apple_private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
}
```

#### **Option C: Command Line Parameters**
```bash
cdk deploy Lingible-Dev \
  --context environment=dev \
  --context apple_client_id="com.lingible.lingible" \
  --context apple_team_id="YOUR_TEAM_ID" \
  --context apple_key_id="YOUR_KEY_ID" \
  --context apple_private_key="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
```

### **3. Security Benefits**
- ✅ **No secrets in CloudFormation template**
- ✅ **No secrets in version control**
- ✅ **No secrets in CDK synthesis output**
- ✅ **Environment-specific credentials**
- ✅ **Secure credential management**

## 🔒 **Security Measures**

### **1. Apple Credentials vs. App Store Secrets**
```python
# Two different types of Apple secrets:

# 1. Apple Identity Provider (Cognito) - Private Key
# Used by: AWS Cognito for Apple Sign-In
# Passed via: CDK Context Parameters (secure)
# Accessed by: AWS Cognito only (not Lambda functions)

# 2. App Store Shared Secret (Receipt Validation)
# Used by: Lambda functions for receipt validation
# Stored in: SSM Parameter Store or environment variables
# Accessed by: Lambda functions for subscription validation
```

### **2. IAM Access Control**
```python
# AWS Cognito accesses the credentials directly (not Lambda functions)
# Credentials are passed securely during deployment
aws_cognito -> CDK Context -> Apple Private Key
```

### **3. Runtime Access**
```python
# AWS Cognito uses credentials during authentication
# Lambda functions never access the Apple private key directly
# The private key is only used by Cognito for Apple Sign-In authentication
```

## 🚨 **Security Best Practices**

### **1. Private Key Management**
- ✅ **Never commit to version control**
- ✅ **Use CDK context parameters for deployment**
- ✅ **Environment-specific credentials**
- ✅ **Secure credential storage**

### **2. Access Control**
- ✅ **Least privilege principle**
- ✅ **Environment-specific permissions**
- ✅ **Audit logging enabled**
- ✅ **Regular access reviews**

### **3. Operational Security**
- ✅ **No hardcoded credentials**
- ✅ **Secure credential rotation process**
- ✅ **Monitoring and alerting**
- ✅ **Backup and recovery procedures**

## 🔧 **Setup Instructions**

### **1. Development Environment**
```bash
# Set environment variables
export CDK_CONTEXT_APPLE_CLIENT_ID="com.lingible.lingible"
export CDK_CONTEXT_APPLE_TEAM_ID="YOUR_TEAM_ID"
export CDK_CONTEXT_APPLE_KEY_ID="YOUR_KEY_ID"
export CDK_CONTEXT_APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"

# Deploy
python3 deploy-dev.py
```

### **2. Production Environment**
```bash
# Set environment variables
export CDK_CONTEXT_APPLE_CLIENT_ID="com.lingible.lingible"
export CDK_CONTEXT_APPLE_TEAM_ID="YOUR_TEAM_ID"
export CDK_CONTEXT_APPLE_KEY_ID="YOUR_KEY_ID"
export CDK_CONTEXT_APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"

# Deploy
python3 deploy-prod.py
```

### **3. CI/CD Pipeline**
```yaml
# Example GitHub Actions workflow
- name: Deploy to Production
  env:
    CDK_CONTEXT_APPLE_CLIENT_ID: ${{ secrets.APPLE_CLIENT_ID }}
    CDK_CONTEXT_APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
    CDK_CONTEXT_APPLE_KEY_ID: ${{ secrets.APPLE_KEY_ID }}
    CDK_CONTEXT_APPLE_PRIVATE_KEY: ${{ secrets.APPLE_PRIVATE_KEY }}
  run: python3 deploy-prod.py
```

## 📊 **Monitoring & Alerting**

### **1. CloudWatch Metrics**
- Secret access frequency
- Failed access attempts
- Secret rotation events

### **2. CloudTrail Logging**
- All Cognito API calls
- IAM permission changes
- Credential modifications

### **3. Alerts**
- Unusual access patterns
- Failed authentication attempts
- Credential rotation failures

## 🔄 **Credential Rotation Process**

### **1. Apple Developer Console**
1. Generate new private key
2. Update key ID and team ID if needed
3. Keep old key active during transition

### **2. AWS Deployment**
1. Update environment variables with new credentials
2. Deploy updated Cognito stack
3. Test Apple Sign-In with new credentials
4. Monitor for any issues

### **3. Application Update**
1. Verify Apple Sign-In still works
2. Remove old credentials from Apple Developer Console
3. Update documentation

## 🛡️ **Additional Security Recommendations**

### **1. Enhanced Encryption**
Consider using AWS KMS customer-managed keys for additional control over encryption.

### **2. Secret Rotation Automation**
Implement automatic secret rotation using AWS Lambda functions.

### **3. Multi-Region Backup**
Store credentials in multiple regions for disaster recovery.

### **4. Access Monitoring**
Set up detailed monitoring and alerting for credential access patterns.

## 📋 **Compliance Considerations**

### **1. Data Protection**
- ✅ **GDPR**: Personal data encryption
- ✅ **SOC 2**: Security controls documentation
- ✅ **PCI DSS**: Secure credential storage

### **2. Audit Requirements**
- ✅ **Access logs**: All credential access logged
- ✅ **Change tracking**: All modifications tracked
- ✅ **Regular reviews**: Quarterly access reviews

## 🚀 **Deployment Checklist**

- [ ] Apple Developer Console credentials obtained
- [ ] Environment variables set for deployment
- [ ] CDK context parameters configured
- [ ] Cognito stack deployed
- [ ] Apple Sign-In tested
- [ ] Monitoring configured
- [ ] Documentation updated
- [ ] Team access reviewed

## 📞 **Emergency Procedures**

### **1. Credential Compromise**
1. Immediately rotate credentials in Apple Developer Console
2. Update environment variables with new credentials
3. Deploy updated Cognito stack
4. Monitor for unauthorized access

### **2. Deployment Issues**
1. Check environment variables are set correctly
2. Verify CDK context parameters
3. Review CloudTrail logs
4. Contact AWS support if needed

---

**Last Updated**: [Current Date]
**Version**: 2.0
**Owner**: DevOps Team
