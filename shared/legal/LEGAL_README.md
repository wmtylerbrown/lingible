# Legal Documentation

This directory contains the legal documents for the Lingible mobile application.

## Documents

### [Terms of Service](./TERMS_OF_SERVICE.md)
- User agreement and service terms
- Usage limits and subscription details
- User conduct and content policies
- Liability limitations and disclaimers

### [Privacy Policy](./PRIVACY_POLICY.md)
- Data collection and usage practices
- Information sharing and security measures
- User rights and data control options
- Compliance with privacy regulations (CCPA, GDPR)

## Implementation Notes

### Single Source of Truth
- **Markdown files** (`.md`) are the authoritative source
- **HTML files** (`.html`) are auto-generated from Markdown
- **Never edit HTML files directly** - they will be overwritten

### Generating HTML Files
To update HTML files after editing Markdown:
```bash
cd docs/
python generate_html.py
```

### App Integration
These documents should be accessible from within the Lingible app:

1. **Settings Screen**: Add links to both documents
2. **Onboarding**: Show privacy policy during account creation
3. **Subscription Flow**: Display terms during premium upgrade
4. **About Screen**: Include legal document links

### Web Hosting
Consider hosting these documents on:
- `https://lingible.com/terms`
- `https://lingible.com/privacy`

### Updates
- **Edit only the Markdown files** (`.md`)
- Run `python generate_html.py` to update HTML
- Review and update documents quarterly
- Notify users of material changes
- Maintain version history
- Update "Last Updated" dates

### Compliance
- Ensure compliance with app store requirements
- Review for GDPR, CCPA, and other privacy regulations
- Consider legal review for production use
- Document any customizations for your specific use case

## Contact Information

For legal questions or document updates:
- **Legal Email**: legal@lingible.com
- **Privacy Email**: privacy@lingible.com
- **General Contact**: support@lingible.com
- **Data Protection Officer**: dpo@lingible.com

## Recent Updates (September 6, 2025)

### AdMob Integration Updates
- **Privacy Policy**: Updated to reflect Google AdMob integration and data collection practices
- **Terms of Service**: Added comprehensive advertising terms and conditions
- **Key Changes**:
  - Free users: Ad-supported experience with banner and interstitial ads
  - Premium users: Completely ad-free experience with no advertising data collection
  - Clear disclosure of data sharing with Google AdMob for free users only
  - Prohibition of ad blocking and manipulation
  - Updated contact information and legal disclaimers
