#!/usr/bin/env python3
"""
Script to generate Firebase test token
"""

import os
from firebase_admin import auth, credentials, initialize_app
import json

def generate_test_token():
    """Generate Firebase custom token"""
    try:
        # Directly use firebase-credentials.json file
        cred_path = "firebase-credentials.json"
        if not os.path.exists(cred_path):
            print(f"❌ Firebase credentials file not found: {cred_path}")
            return None
            
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
        
        # User UID
        uid = "kakwSReJOyaPb3ArKGHFhjuG1Wr1"
        
        print(f"🔑 Generating custom token for user {uid}...")
        
        # Generate custom token
        custom_token = auth.create_custom_token(uid)
        
        print(f"✅ Generated Firebase custom token:")
        print(custom_token.decode('utf-8'))
        print(f"\n📋 Token length: {len(custom_token.decode('utf-8'))} characters")
        
        return custom_token.decode('utf-8')
        
    except Exception as e:
        print(f"❌ Failed to generate token: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    generate_test_token() 