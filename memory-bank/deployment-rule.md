# CDK Deployment Rule

## CRITICAL: Always Use npm Scripts for CDK Deployment

**NEVER use raw `cdk deploy` commands in this project.**

### ✅ CORRECT Commands:
```bash
npm run deploy:backend:dev    # For development
npm run deploy:backend:prod   # For production
```

### ❌ WRONG Commands:
```bash
cdk deploy --app app.js Lingible-Dev  # Missing build step!
cdk deploy Lingible-Dev               # Wrong context!
```

### Why This Matters:
- The npm scripts include `npm run build` which compiles TypeScript and builds lambda packages
- Raw CDK commands skip the build step and will fail
- This project has a specific build process that must be followed

### What the Scripts Do:
1. `npm run build` - Compiles TypeScript + builds lambda packages
2. `cdk deploy` - Deploys with proper context and app file

### If You Forget:
- Check `package.json` scripts section first
- Look for `deploy:backend:dev` or `deploy:backend:prod`
- Never assume raw CDK commands will work

**This rule exists because we wasted 2+ hours debugging a "circular dependency" that was actually just a missing build step.**
