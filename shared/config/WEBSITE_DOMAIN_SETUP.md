# Website Domain Setup Guide

## 🎯 **Complete DNS Configuration for Lingible Website**

This document explains the DNS setup required for both dev and production environments.

## 📋 **Environment Overview**

### **Dev Environment:**
- **Website Domain**: `dev.lingible.com`
- **API Domain**: `api.dev.lingible.com` (already configured)
- **Hosted Zone**: `dev.lingible.com` (managed by AWS Route53)

### **Production Environment:**
- **Website Domain**: `lingible.com`
- **API Domain**: `api.lingible.com` (to be configured)
- **Hosted Zone**: `lingible.com` (managed by Squarespace)

## 🔧 **Technical Implementation**

### **What the CDK Does Automatically:**

#### **Dev Environment (`dev.lingible.com`):**
1. ✅ **Creates hosted zone** `dev.lingible.com` in Route53
2. ✅ **Creates SSL certificate** for `dev.lingible.com`
3. ✅ **Creates CloudFront distribution** with custom domain
4. ✅ **Creates A record** in `dev.lingible.com` zone pointing to CloudFront
5. ✅ **Deploys website** to S3 with CloudFront

#### **Production Environment (`lingible.com`):**
1. ✅ **Creates SSL certificate** for `lingible.com` (validated via DNS)
2. ✅ **Creates CloudFront distribution** with custom domain
3. ✅ **Deploys website** to S3 with CloudFront
4. ❌ **Manual step**: A record in Squarespace pointing to CloudFront

## 📝 **Manual DNS Configuration Required**

### **For Production (`lingible.com`):**

You'll need to add an **A record** in Squarespace DNS:

```
Type: A
Name: @ (or leave blank for root domain)
Value: [CloudFront Distribution Domain]
TTL: 300 (or default)
```

**To get the CloudFront domain:**
1. Deploy the website stack: `cdk deploy Lingible-Prod-Website`
2. Check outputs: `aws cloudformation describe-stacks --stack-name Lingible-Prod-Website`
3. Use the `CloudFrontURL` output value

### **For Dev (`dev.lingible.com`):**

**No manual configuration needed!** The CDK automatically:
- Creates the hosted zone
- Sets up the A record
- Configures SSL certificate

## 🚀 **Deployment Steps**

### **1. Deploy Hosted Zones (if not already done):**
```bash
cd backend/infrastructure
cdk deploy Lingible-Dev-HostedZones
```

### **2. Deploy Website Stack:**
```bash
# For dev environment
cdk deploy Lingible-Dev-Website

# For production environment
cdk deploy Lingible-Prod-Website
```

### **3. Configure Squarespace DNS (Production Only):**
1. Get CloudFront domain from CDK outputs
2. Add A record in Squarespace DNS pointing to CloudFront
3. Wait for DNS propagation (5-15 minutes)

## 🔍 **Verification**

### **Check Website is Live:**
```bash
# Dev environment
curl -I https://dev.lingible.com

# Production environment
curl -I https://lingible.com
```

### **Check SSL Certificate:**
```bash
# Dev environment
openssl s_client -connect dev.lingible.com:443 -servername dev.lingible.com

# Production environment
openssl s_client -connect lingible.com:443 -servername lingible.com
```

## 📊 **DNS Record Summary**

### **Dev Environment (`dev.lingible.com`):**
```
@ A [CloudFront Domain] (auto-created by CDK)
```

### **Production Environment (`lingible.com`):**
```
@ A [CloudFront Domain] (manual in Squarespace)
```

## 🎯 **Expected Results**

After deployment:

- ✅ **Dev**: `https://dev.lingible.com` → Lingible website
- ✅ **Production**: `https://lingible.com` → Lingible website
- ✅ **SSL**: Both domains have valid SSL certificates
- ✅ **Performance**: CloudFront CDN for fast global delivery
- ✅ **Security**: HTTPS redirect and secure headers

## 🔧 **Troubleshooting**

### **Common Issues:**

1. **SSL Certificate Pending**: Wait 5-15 minutes for DNS validation
2. **DNS Not Propagated**: Wait up to 48 hours for full propagation
3. **CloudFront Not Updated**: Clear CloudFront cache or wait for TTL
4. **Squarespace DNS**: Ensure A record points to CloudFront domain (not IP)

### **Useful Commands:**
```bash
# Check DNS resolution
nslookup dev.lingible.com
nslookup lingible.com

# Check CloudFront status
aws cloudfront get-distribution --id [DISTRIBUTION_ID]

# Check certificate status
aws acm list-certificates --region us-east-1
```

The website will be fully functional with proper domains and SSL certificates! 🚀
