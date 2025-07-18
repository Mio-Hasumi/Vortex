#!/bin/bash
# Setup Firebase credentials for VoiceApp Backend

echo "🔥 Firebase Setup Script"
echo "=========================="

# Check if firebase-credentials.json exists
if [ -f "firebase-credentials.json" ]; then
    echo "✅ firebase-credentials.json found"
else
    echo "❌ firebase-credentials.json not found"
    echo ""
    echo "Please follow these steps:"
    echo "1. Go to https://console.firebase.google.com/"
    echo "2. Select project 'voiceapp-8f09a'"
    echo "3. Go to Project Settings > Service accounts"
    echo "4. Click 'Generate new private key'"
    echo "5. Download the JSON file"
    echo "6. Rename it to 'firebase-credentials.json'"
    echo "7. Place it in the project root directory"
    echo ""
    exit 1
fi

# Test the Firebase setup
echo "🧪 Testing Firebase configuration..."
python3 -c "
import sys
sys.path.append('.')
from infrastructure.config import get_settings
settings = get_settings()
print(f'✅ Firebase project ID: {settings.FIREBASE_PROJECT_ID}')
print(f'✅ Firebase credentials path: {settings.FIREBASE_CREDENTIALS_PATH}')
print('✅ Firebase setup complete!')
"

echo ""
echo "🎉 Firebase is ready to use!"
echo "You can now start the backend with: python main.py" 