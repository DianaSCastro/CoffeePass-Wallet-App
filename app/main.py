from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from app.google_wallet import create_google_wallet_jwt
from app.apple_wallet import create_apple_pass
import os

app = FastAPI(title="LoyaltyChain Wallet API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MemberData(BaseModel):
    member_id: str
    name: str
    points: int
    level: str          # Bronze / Silver / Gold / Platinum
    wallet_address: str

# ── Google Wallet ──────────────────────────────────────────────────────────────
@app.post("/wallet/google/add-url")
def google_wallet_url(member: MemberData):
    """Returns the Save-to-Google-Wallet URL. Redirect the browser to it."""
    try:
        token = create_google_wallet_jwt(member)
        url = f"https://pay.google.com/gp/v/save/{token}"
        return {"url": url, "token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/wallet/google/redirect")
def google_wallet_redirect(member: MemberData):
    """Directly redirects user to Google Wallet save page."""
    token = create_google_wallet_jwt(member)
    return RedirectResponse(
        url=f"https://pay.google.com/gp/v/save/{token}",
        status_code=302
    )


