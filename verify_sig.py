#!/usr/bin/env python3
import sys, json, base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

if len(sys.argv) != 3:
    print("Usage: python3 verify_sig.py <json_file> <pubkey_pem>")
    sys.exit(1)

json_file, pubkey_path = sys.argv[1], sys.argv[2]

# load JSON file
with open(json_file,"r") as f:
    data = json.load(f)

if "signature" not in data:
    print("❌ No signature field in JSON")
    sys.exit(1)

# extract signature
sig_b64 = data.pop("signature")
sig = base64.b64decode(sig_b64)

# load pubkey
with open(pubkey_path,"rb") as f:
    pub = serialization.load_pem_public_key(f.read())

try:
    pub.verify(sig, json.dumps(data, sort_keys=True).encode())
    print("✅ signature valid")
except Exception as e:
    print("❌ signature verification failed:", e)
