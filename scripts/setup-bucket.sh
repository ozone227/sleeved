#!/bin/bash
# Sleeved — S3 Bucket Setup
# Usage: bash scripts/setup-bucket.sh

set -e

BUCKET="sleeved-collection"
REGION="us-east-1"

echo "🪣  Creating bucket: $BUCKET in $REGION..."
aws s3api create-bucket \
  --bucket "$BUCKET" \
  --region "$REGION"

echo "🔄  Enabling versioning..."
aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

echo "🔓  Disabling block public access..."
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

echo "📜  Applying public read policy..."
aws s3api put-bucket-policy \
  --bucket "$BUCKET" \
  --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Sid\": \"PublicReadGetObject\",
      \"Effect\": \"Allow\",
      \"Principal\": \"*\",
      \"Action\": \"s3:GetObject\",
      \"Resource\": \"arn:aws:s3:::$BUCKET/*\"
    }]
  }"

echo "🌐  Setting CORS (for gallery app)..."
aws s3api put-bucket-cors \
  --bucket "$BUCKET" \
  --cors-configuration '{
    "CORSRules": [{
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": []
    }]
  }'

echo "📁  Uploading initial inventory scaffold..."

cat > /tmp/cyberpunk-inventory.json << 'ENDJSON'
{
  "game": "cyberpunk-tcg",
  "displayName": "Cyberpunk TCG",
  "lastUpdated": "",
  "structure": {
    "types": ["Legend", "Unit", "Program", "Gear"],
    "colors": ["Red", "Green", "Blue", "Yellow"],
    "coloredTypes": ["Unit", "Program", "Gear"]
  },
  "cards": []
}
ENDJSON

aws s3 cp /tmp/cyberpunk-inventory.json \
  "s3://$BUCKET/cyberpunk-tcg/inventory.json" \
  --content-type "application/json"

cat > /tmp/games.json << 'ENDJSON'
{
  "games": [
    {
      "id": "cyberpunk-tcg",
      "displayName": "Cyberpunk TCG",
      "inventoryPath": "cyberpunk-tcg/inventory.json"
    }
  ]
}
ENDJSON

aws s3 cp /tmp/games.json \
  "s3://$BUCKET/games.json" \
  --content-type "application/json"

rm /tmp/cyberpunk-inventory.json /tmp/games.json

echo ""
echo "✅  Done!"
echo "   URL:        https://$BUCKET.s3.amazonaws.com"
echo "   Versioning: Enabled"
echo "   Access:     Public read"
echo "   CORS:       Enabled"
echo ""
aws s3 ls "s3://$BUCKET" --recursive
