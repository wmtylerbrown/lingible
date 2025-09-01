#!/bin/bash
#
# Regenerate Lingible Client SDK while preserving custom code
# Custom files are protected by .openapi-generator-ignore
#

set -e  # Exit on any error

echo "🔄 Regenerating Lingible Client SDK..."

# Step 1: Verify custom files exist
echo "🔒 Checking for custom files..."
if [ ! -f "python/lingible_client/auth.py" ] || [ ! -f "python/lingible_client/authenticated_client.py" ] || [ ! -f "python/test_lingible_client.py" ]; then
    echo "⚠️  Custom files not found. This might be the first generation."
fi

# Step 2: Regenerate from updated OpenAPI spec
echo "🏗️  Generating client from OpenAPI spec..."
echo "   Custom files protected by .openapi-generator-ignore"
openapi-generator generate \
  -i ../shared/api/openapi/lingible-api.yaml \
  -g python \
  -o python \
  --package-name lingible_client \
  --additional-properties=projectName=lingible-client,packageVersion=1.0.0

echo "✅ Client SDK regenerated successfully!"
echo ""
echo "🔍 Next steps:"
echo "1. Check for any import errors in custom files"
echo "2. Update any API endpoint references if needed (removed /v1 prefix)"
echo "3. Test the client: cd python && python test_lingible_client.py"
echo ""
echo "🛡️  Custom files protected by .openapi-generator-ignore:"
echo "   - lingible_client/auth.py"
echo "   - lingible_client/authenticated_client.py"
echo "   - test_lingible_client.py"
echo "   - requirements.txt"
echo "   - test-requirements.txt"
