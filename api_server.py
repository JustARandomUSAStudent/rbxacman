from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import requests
from classes.roblox_api import RobloxAPI

app = FastAPI(title="RBX Account Manager API")
manager = None

def start_api(mgr):
    global manager
    manager = mgr
    port = int(manager.get_secure_setting("api_port", 6969))
    print(f"API Server started on http://127.0.0.1:{port}")
    print(f"   → Open http://127.0.0.1:{port}/docs for interactive Swagger UI")
    uvicorn.run("api_server:app", host="127.0.0.1", port=port, log_level="warning")

def check_password(password: str | None):
    if manager and manager.get_secure_setting("api_require_password", False):
        if password != manager.get_secure_setting("api_password", ""):
            raise HTTPException(401, "Invalid API password")

@app.get("/LaunchAccount")
async def launch_account(Account: str = Query(...), PlaceId: int = Query(...), JobId: str = Query(None), Password: str = Query(None)):
    check_password(Password)
    if not manager or Account not in manager.accounts:
        raise HTTPException(404, f"Account '{Account}' not found")
    success = manager.launch_roblox(username=Account, game_id=PlaceId, job_id=JobId or "")
    return {"status": "success" if success else "failed", "account": Account}

@app.get("/FollowUser")
async def follow_user(Account: str = Query(...), Username: str = Query(...), Password: str = Query(None)):
    check_password(Password)
    cookie = manager.get_account_cookie(Account)
    if not cookie: raise HTTPException(404, "Account not found")
    user_id = RobloxAPI.get_user_id_from_username(Username)
    if not user_id: raise HTTPException(404, "User not found")
    csrf = RobloxAPI.get_csrf_token(cookie)
    r = requests.post(f"https://friends.roblox.com/v1/users/{user_id}/follow", headers={"x-csrf-token": csrf, "Cookie": f".ROBLOSECURITY={cookie}"})
    return {"success": r.ok}

@app.get("/BlockUser")
async def block_user(Account: str = Query(...), UserId: int = Query(...), Password: str = Query(None)):
    check_password(Password)
    cookie = manager.get_account_cookie(Account)
    if not cookie: raise HTTPException(404, "Account not found")
    csrf = RobloxAPI.get_csrf_token(cookie)
    r = requests.post(f"https://users.roblox.com/v1/users/{UserId}/block", headers={"x-csrf-token": csrf, "Cookie": f".ROBLOSECURITY={cookie}"})
    return {"success": r.ok}

@app.get("/UnblockUser")
async def unblock_user(Account: str = Query(...), UserId: int = Query(...), Password: str = Query(None)):
    check_password(Password)
    cookie = manager.get_account_cookie(Account)
    if not cookie: raise HTTPException(404, "Account not found")
    csrf = RobloxAPI.get_csrf_token(cookie)
    r = requests.post(f"https://users.roblox.com/v1/users/{UserId}/unblock", headers={"x-csrf-token": csrf, "Cookie": f".ROBLOSECURITY={cookie}"})
    return {"success": r.ok}

@app.get("/GetAccounts")
async def get_accounts():
    return {"accounts": list(manager.accounts.keys()) if manager else []}

@app.get("/GetAccountsJson")
async def get_accounts_json():
    if not manager: return {"accounts": {}}
    safe = {u: {k:v for k,v in d.items() if k != "cookie"} for u,d in manager.accounts.items()}
    return JSONResponse(content=safe)

@app.get("/GetPublicServers")
async def get_public_servers(PlaceId: int = Query(...), Limit: int = Query(10), Password: str = Query(None)):
    check_password(Password)
    servers = RobloxAPI.get_public_servers(PlaceId, Limit)
    return {"placeId": PlaceId, "servers": servers}

@app.get("/JoinSmallestServer")
async def join_smallest_server(Account: str = Query(...), PlaceId: int = Query(...), Password: str = Query(None)):
    check_password(Password)
    if not manager or Account not in manager.accounts: raise HTTPException(404, f"Account '{Account}' not found")
    server_id = RobloxAPI.get_smallest_server(PlaceId)
    if not server_id: raise HTTPException(404, "No servers found")
    success = manager.launch_roblox(username=Account, game_id=PlaceId, job_id=server_id)
    return {"status": "success" if success else "failed", "jobId": server_id}

@app.get("/status")
async def status():
    return {"running": True, "port": int(manager.get_secure_setting("api_port", 6969)) if manager else 6969}