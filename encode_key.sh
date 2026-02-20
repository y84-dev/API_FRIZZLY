#!/bin/bash
# Encode serviceAccountKey.json to base64
base64 -w 0 serviceAccountKey.json > serviceAccountKey.base64.txt
echo ""
echo "Copy the content above and set as environment variable:"
echo "export FIREBASE_SERVICE_ACCOUNT_BASE64='<paste_here>'"
