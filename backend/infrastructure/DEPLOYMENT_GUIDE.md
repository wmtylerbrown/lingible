# 🚀 Lingible Deployment Guide

## 📋 **Quick Reference**

### **🎯 Main Deployment Commands**
```bash
# Deploy everything (backend + website) to dev (default)
npm run deploy

# Deploy everything to dev
npm run deploy:dev

# Deploy everything to prod
npm run deploy:prod
```

### **🔧 Component-Specific Deployments**
```bash
# Backend only
npm run deploy:backend:dev
npm run deploy:backend:prod

# Website only
npm run deploy:website:dev
npm run deploy:website:prod

# Hosted zones only (DNS setup)
npm run deploy:hosted-zones:dev
npm run deploy:hosted-zones:prod
```

## 🏗️ **What Gets Deployed**

### **Full Deployment (`deploy:dev` / `deploy:prod`)**
- ✅ **Backend Stack**: All Lambda functions, API Gateway, DynamoDB, Cognito
- ✅ **Website Stack**: S3 bucket, CloudFront distribution, legal pages

### **Backend Only (`deploy:backend:dev` / `deploy:backend:prod`)**
- ✅ **API Infrastructure**: Lambda functions, API Gateway, DynamoDB
- ✅ **Authentication**: Cognito User Pool
- ✅ **Monitoring**: CloudWatch logs, SNS alerts

### **Website Only (`deploy:website:dev` / `deploy:website:prod`)**
- ✅ **Static Website**: S3 bucket with website files
- ✅ **CDN**: CloudFront distribution
- ✅ **Legal Pages**: Privacy Policy, Terms of Service

## 🌐 **Environment URLs**

### **Development**
- **API**: `https://04rie9qo0b.execute-api.us-east-1.amazonaws.com/prod/`
- **Website**: `https://dev.lingible.com`
- **Health Check**: `https://04rie9qo0b.execute-api.us-east-1.amazonaws.com/prod/health`

### **Production**
- **API**: `https://7buj7qpef5.execute-api.us-east-1.amazonaws.com/prod/`
- **Website**: `https://lingible.com`
- **Health Check**: `https://7buj7qpef5.execute-api.us-east-1.amazonaws.com/prod/health`

## 🛠️ **Other Useful Commands**

### **Development**
```bash
npm run build          # Build TypeScript and Lambda packages
npm run watch          # Watch TypeScript files for changes
npm run lint           # Lint TypeScript code
npm run lint:fix       # Fix linting issues
```

### **Testing**
```bash
npm run python:test           # Run Python tests
npm run python:test:coverage  # Run tests with coverage
npm run python:lint           # Lint Python code
npm run python:type-check     # Type check Python code
```

### **Cleanup**
```bash
npm run clean          # Clean build artifacts
npm run clean:all      # Clean everything including node_modules
npm run clean:workspace # Clean entire workspace
```

### **CDK Operations**
```bash
npm run cdk:synth      # Synthesize CloudFormation templates
npm run cdk:diff       # Show differences
npm run cdk:bootstrap  # Bootstrap CDK environment
```

## 🔄 **Deployment Workflow**

### **First Time Setup**
1. **Bootstrap CDK**: `npm run cdk:bootstrap`
2. **Deploy Hosted Zones**: `npm run deploy:hosted-zones:dev`
3. **Deploy Everything**: `npm run deploy:dev`

### **Regular Development**
1. **Make changes** to code
2. **Deploy to dev**: `npm run deploy:dev`
3. **Test** on dev environment
4. **Deploy to prod**: `npm run deploy:prod`

### **Component Updates**
- **Backend changes only**: `npm run deploy:backend:dev`
- **Website changes only**: `npm run deploy:website:dev`
- **Legal document updates**: `npm run deploy:website:dev`

## ⚠️ **Important Notes**

- **Dev deployments**: Use `--require-approval never` (automatic)
- **Prod deployments**: Use `--require-approval any-change` (manual confirmation)
- **Website builds**: Automatically regenerates legal pages from Markdown
- **Lambda packages**: Smart change detection prevents unnecessary rebuilds
- **Environment separation**: Dev and prod are completely isolated

## 🆘 **Troubleshooting**

### **Deployment Fails**
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify CDK bootstrap: `npm run cdk:bootstrap`
3. Check CloudFormation console for detailed errors

### **Website Not Updating**
1. Check CloudFront cache (may take 15-20 minutes)
2. Verify S3 bucket contents
3. Check DNS propagation

### **API Not Working**
1. Check Lambda function logs in CloudWatch
2. Verify API Gateway configuration
3. Test health endpoint: `curl https://api.dev.lingible.com/health`
