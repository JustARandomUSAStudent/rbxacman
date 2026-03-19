from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import threading
import requests
import os
from classes.roblox_api import RobloxAPI

app = FastAPI(title="Roblox Account Manager API (evanovar + ic3w0lf22)")

# Shared manager from the GUI (no password issues)
manager = None

def start_api(mgr):
    """Called from main.py — shares the exact same loaded accounts"""
    global manager
    manager = mgr
    print("✅ API Server started on http://127.0.0.1:6969")
    print("   → Open http://127.0.0.1:6969/docs for interactive Swagger UI")
    uvicorn.run("api_server:app", host="127.0.0.1", port=6969, log_level="warning")

# ====================== PASSWORD PROTECTION (optional) ======================
def check_password(password: str | None):
    # You can add your own APIPassword in AccountManagerData/settings.json later if you want
    pass  # disabled for now so it works immediately

# ====================== ENDPOINTS (full ic3w0lf22 style) ======================
@app.get("/LaunchAccount")
async def launch_account(
    Account: str = Query(..., description="Your exact account username"),
    PlaceId: int = Query(..., description="Place ID to join"),
    JobId: str = Query(None, description="Optional server JobId"),
    Password: str = Query(None)
):
    check_password(Password)
    if manager is None:
        raise HTTPException(500, "Manager not ready")
    cookie = manager.get_account_cookie(Account)
    if not cookie:
        raise HTTPException(404, f"Account '{Account}' not found or no cookie")
    
    # Uses the EXACT same launch code as your GUI
    success = RobloxAPI.launch_roblox(
        username=Account,
        cookie=cookie,
        game_id=PlaceId,
        private_server_id="",
        launcher_preference="default",
        job_id=JobId or ""
    )
    return {"status": "success" if success else "failed", "account": Account, "placeId": PlaceId}

@app.get("/FollowUser")
async def follow_user(
    Account: str = Query(...),
    Username: str = Query(...),
    Password: str = Query(None)
):
    check_password(Password)
    if manager is None:
        raise HTTPException(500, "Manager not ready")
    cookie = manager.get_account_cookie(Account)
    if not cookie:
        raise HTTPException(404, "Account not found")
    
    user_id = RobloxAPI.get_user_id_from_username(Username)
    if not user_id:
        raise HTTPException(404, "Target user not found")
    
    csrf = RobloxAPI.get_csrf_token(cookie)
    r = requests.post(
        f"https://friends.roblox.com/v1/users/{user_id}/follow",
        headers={"x-csrf-token": csrf, "Cookie": f".ROBLOSECURITY={cookie}"}
    )
    return {"success": r.ok, "status_code": r.status_code}

@app.get("/BlockUser")
async def block_user(
    Account: str = Query(...),
    UserId: int = Query(...),
    Password: str = Query(None)
):
    check_password(Password)
    cookie = manager.get_account_cookie(Account) if manager else None
    if not cookie:
        raise HTTPException(404, "Account not found")
    csrf = RobloxAPI.get_csrf_token(cookie)
    r = requests.post(
        f"https://users.roblox.com/v1/users/{UserId}/block",
        headers={"x-csrf-token": csrf, "Cookie": f".ROBLOSECURITY={cookie}"}
    )
    return {"success": r.ok}

@app.get("/UnblockUser")
async def unblock_user(
    Account: str = Query(...),
    UserId: int = Query(...),
    Password: str = Query(None)
):
    check_password(Password)
    cookie = manager.get_account_cookie(Account) if manager else None
    if not cookie:
        raise HTTPException(404, "Account not found")
    csrf = RobloxAPI.get_csrf_token(cookie)
    r = requests.post(
        f"https://users.roblox.com/v1/users/{UserId}/unblock",
        headers={"x-csrf-token": csrf, "Cookie": f".ROBLOSECURITY={cookie}"}
    )
    return {"success": r.ok}

@app.get("/GetAccounts")
async def get_accounts():
    return {"accounts": list(manager.accounts.keys()) if manager else []}

@app.get("/GetCookie")
async def get_cookie(Account: str = Query(...)):
    cookie = manager.get_account_cookie(Account) if manager else None
    return {"cookie": cookie}

@app.get("/GetAccountsJson")
async def get_accounts_json():
    if not manager:
        return {"accounts": {}}
    safe = {u: {k: v for k, v in d.items() if k != "cookie"} for u, d in manager.accounts.items()}
    return JSONResponse(content=safe)

@app.get("/status")
async def status():
    return {"running": True, "accounts": len(manager.accounts) if manager else 0}