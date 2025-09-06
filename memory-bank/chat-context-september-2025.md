# Chat Context - September 2025

## App Store Submission Progress

### Current Status
- **Production Archive**: Built with correct bundle ID `com.lingible.lingible` and production Amplify configuration
- **App Store Connect**: Setup complete with screenshots, description, keywords, and 1024x1024 icon
- **Legal Documents**: Updated Privacy Policy and Terms of Service to match Apple privacy questionnaire answers
- **Apple Privacy Questionnaire**: Currently in progress - completed Email Address and User ID sections

### Key Decisions Made
1. **Bundle ID Strategy**:
   - Dev: `com.lingible.lingible.dev`
   - Prod: `com.lingible.lingible`

2. **Amplify Configuration**:
   - Dev: `amplify_outputs-dev.json` (us-east-1_65YoJgNVi user pool)
   - Prod: `amplify_outputs-prod.json` (us-east-1_ENGYDDFRb user pool)
   - Manual copy approach for production builds

3. **Legal Document Updates**:
   - Updated dates to September 5, 2025
   - Added explicit no-tracking statements
   - Aligned with Apple privacy questionnaire answers

### Current Apple Privacy Questionnaire Answers
- **Email Addresses**:
  - Usage: App Functionality, Analytics
  - Tracking: No
  - Linked to Identity: Yes

- **User IDs**:
  - Usage: App Functionality, Analytics
  - Tracking: No
  - Linked to Identity: Yes

### Major Decision: Google AdMob Integration
- **Target**: Free tier users only (premium users get ad-free experience)
- **Approach**: Simple banner ads with basic demographic targeting (no fancy targeting)
- **Timeline**: Implement before App Store submission to avoid resubmission

### Next Steps Required
1. Update legal documents for AdMob integration
2. Add AdMob to iOS app (simple banner ads)
3. Update Apple privacy questionnaire answers for AdMob
4. Complete App Store submission

### Technical Context
- **iOS Project**: `/Users/tyler/mobile-app-aws-backend/ios/Lingible/`
- **Legal Documents**: `shared/legal/PRIVACY_POLICY.md` and `shared/legal/TERMS_OF_SERVICE.md`
- **Amplify Configs**: `amplify_outputs-dev.json` and `amplify_outputs-prod.json`
- **Production Archive**: `Lingible-Production-Release.xcarchive`

### User Preferences
- Prefers manual configuration over automated scripts for now
- Wants to implement AdMob before App Store submission
- Focuses on simple, compliant implementation over complex targeting
- Values clear legal documentation and privacy compliance
