import json
import os
import time
import uuid


import google.auth.transport.requests
from google.oauth2 import service_account
import requests as req

from dotenv import load_dotenv
load_dotenv()

ISSUER_ID    = os.environ["GOOGLE_WALLET_ISSUER_ID"]
CLASS_SUFFIX = os.environ.get("GOOGLE_WALLET_CLASS_SUFFIX", "LoyaltyChain_v1")
SA_FILE      = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
SCOPES       = ["https://www.googleapis.com/auth/wallet_object.issuer"]

LEVEL_COLORS = {
    "Bronze": "#CD7F32", "Silver": "#C0C0C0",
    "Gold": "#FAC775",   "Platinum": "#E5E4E2",
}

def _get_credentials():
    creds = service_account.Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    return creds

def ensure_loyalty_class():
    class_id = f"{ISSUER_ID}.{CLASS_SUFFIX}"
    creds = _get_credentials()
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json"
    }
    url = f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass/{class_id}"
    resp = req.get(url, headers=headers)
    if resp.status_code == 200:
        return class_id

    loyalty_class = {
        "id": class_id,
        "issuerName": "LoyaltyChain",
        "programName": "LoyaltyChain Rewards",
        "programLogo": {
            "sourceUri": {"uri": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Star_Polygon_6-2.svg/240px-Star_Polygon_6-2.svg.png"},
            "contentDescription": {"defaultValue": {"language": "es", "value": "Logo"}}
        },
        "hexBackgroundColor": "#26215C",
        "reviewStatus": "UNDER_REVIEW",
        "countryCode": "MX",
    }
    resp2 = req.post(
        "https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass",
        headers=headers, json=loyalty_class
    )
    if resp2.status_code not in (200, 201):
        raise Exception(f"Error creando clase: {resp2.status_code} {resp2.text}")
    return class_id

def create_google_wallet_jwt(member) -> str:
    import jwt as pyjwt

    class_id  = ensure_loyalty_class()
    
    object_id = f"{ISSUER_ID}.{member.member_id.replace('-', '_')}_{uuid.uuid4().hex[:8]}"
    value_mxn = member.points / 100

    loyalty_object = {
        "id": object_id,
        "classId": class_id,
        "state": "ACTIVE",
        "accountId": member.wallet_address[:20],
        "accountName": member.name,
        "loyaltyPoints": {
            "balance": {"string": f"{member.points:,} LYL"},
            "label": "Puntos LYL",
        },
        "textModulesData": [
            {"header": "Nivel",   "body": member.level,        "id": "level"},
            {"header": "Valor",   "body": f"${value_mxn:.2f} MXN", "id": "value"},
            {"header": "Red",     "body": "Ethereum Mainnet",  "id": "network"},
        ],
        "barcode": {
            "type": "QR_CODE",
            "value": f"LC-{member.member_id}|{member.wallet_address}|{member.points}",
            "alternateText": f"ID: {member.member_id}",
        },
        "hexBackgroundColor": "#26215C",
    }

    with open(SA_FILE) as f:
        sa = json.load(f)

    payload = {
        "iss": sa["client_email"],
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(time.time()),
        "origins": ["http://localhost:8000", "http://127.0.0.1:8000"],
        "payload": {
            "loyaltyObjects": [loyalty_object]
        },
    }

    signer = service_account.Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
    token = pyjwt.encode(payload, signer.signer._key, algorithm="RS256")
    return token