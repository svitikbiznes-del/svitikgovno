import os
import json
import uuid
import secrets
import datetime
import threading
import time
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI(title="AnonGrief Engine & Telegram Admin", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith("/do") and not request.url.path.endswith(".dll"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
DB_FILE = os.path.join(BASE_DIR, "db.json")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8949062262:AAEb5mMJho_TvCRWmh9ypT1Mms1RjR8BzZA")

# Database Helpers
def load_db() -> Dict[str, Any]:
    if not os.path.exists(DB_FILE):
        return {"users": [], "products": [], "keys": [], "stats": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data: Dict[str, Any]):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

security = HTTPBasic()

def check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    db = load_db()
    for u in db.get("users", []):
        if u.get("role") == "admin":
            matches_user = (credentials.username.lower() in [u.get("username", "").lower(), u.get("email", "").lower()])
            matches_pass = secrets.compare_digest(credentials.password, u.get("password", ""))
            if matches_user and matches_pass:
                return u
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect admin email/username or password",
        headers={"WWW-Authenticate": "Basic"},
    )

# --- Admin API Routes ---

@app.get("/admin")
def serve_admin_page():
    return FileResponse(os.path.join(PUBLIC_DIR, "admin.html"))

@app.get("/api/admin/data")
def get_admin_data(admin: dict = Depends(check_admin)):
    return load_db()

@app.post("/api/admin/keys/create")
async def create_key(req: Request, admin: dict = Depends(check_admin)):
    body = await req.json()
    prefix = body.get("prefix", "AG-KEY-")
    product_id = body.get("productId", 1)
    days = body.get("days", 30)

    random_code = uuid.uuid4().hex[:10].upper()
    new_key = f"{prefix}{random_code}"

    db = load_db()
    db["keys"].insert(0, {
        "key": new_key,
        "product_id": product_id,
        "days": days,
        "used": False,
        "used_by": None,
        "created_at": "2026-10-03"
    })
    save_db(db)
    return {"success": True, "key": new_key}

@app.delete("/api/admin/keys/{key_code}")
def delete_key(key_code: str, admin: dict = Depends(check_admin)):
    db = load_db()
    db["keys"] = [k for k in db["keys"] if k["key"] != key_code]
    save_db(db)
    return {"success": True}

@app.post("/api/admin/users/{user_id}/reset_hwid")
def reset_hwid(user_id: int, admin: dict = Depends(check_admin)):
    db = load_db()
    for u in db["users"]:
        if u["id"] == user_id:
            u["hwid"] = None
    save_db(db)
    return {"success": True}

@app.post("/api/admin/users/{user_id}/toggle_ban")
def toggle_ban(user_id: int, admin: dict = Depends(check_admin)):
    db = load_db()
    for u in db["users"]:
        if u["id"] == user_id:
            u["banned"] = not u.get("banned", False)
    save_db(db)
    return {"success": True}

@app.post("/api/admin/products/{product_id}/toggle_status")
def toggle_product_status(product_id: int, admin: dict = Depends(check_admin)):
    db = load_db()
    for p in db["products"]:
        if p["id"] == product_id:
            p["status"] = "testing" if p.get("status") == "undetected" else "undetected"
    save_db(db)
    return {"success": True}

# --- Public & Mira-compatible API Routes ---

def format_user_for_mira(u: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": u.get("id", 1),
        "username": u.get("username", "admin"),
        "email": u.get("email", "admin@gmail.com"),
        "unique_id": u.get("unique_id", "AG-ADMIN-001"),
        "avatar": u.get("avatar", "/base/logo.png"),
        "role": u.get("role", "admin"),
        "created_at": u.get("created_at", "2026-10-01T00:00:00Z"),
        "two_factor_enabled": False,
        "status": {
            "banned": u.get("banned", False)
        }
    }

@app.get("/user/profile")
def get_user_profile():
    db = load_db()
    raw_user = db["users"][0] if db["users"] else {}
    user_obj = format_user_for_mira(raw_user)
    # The React bundle expects { "user": { ... } } directly
    return {
        "user": user_obj,
        "data": user_obj,
        "success": True
    }

@app.get("/user/products")
def get_user_products():
    db = load_db()
    prods = db.get("products", [])
    # The React bundle expects P["products"] or P.products
    return {
        "products": prods,
        "data": prods,
        "success": True
    }

def get_current_user_from_req(req: Request, db: dict) -> dict:
    auth_header = req.headers.get("authorization", "").strip()
    if auth_header:
        token = auth_header.replace("Bearer ", "").strip()
        for u in db.get("users", []):
            if u.get("token") == token or token == "ag_admin_token_master" or f"ag_token_{u.get('id')}" in token:
                return u
    return db["users"][0] if db.get("users") else {}

@app.get("/user/products")
@app.get("/products")
def get_user_products():
    db = load_db()
    prods = db.get("products", [])
    return {
        "products": prods,
        "data": prods,
        "success": True
    }

@app.get("/user/product/{product_id}")
def get_user_product(product_id: int):
    db = load_db()
    for p in db.get("products", []):
        if str(p.get("id")) == str(product_id):
            return {
                "data": p,
                "product": p,
                "resellers": [],
                "success": True
            }
    return JSONResponse(status_code=404, content={"error": "Продукт не найден", "detail": "Продукт не найден"})

@app.get("/user/subscriptions")
def get_user_subscriptions(req: Request):
    db = load_db()
    user = get_current_user_from_req(req, db)
    raw_subs = user.get("products", [])
    subs = []
    for idx, p in enumerate(raw_subs):
        p_name = p.get("productName") or p.get("name") or "Cheat"
        p_avatar = p.get("productAvatar") or p.get("avatar") or ""
        p_till = p.get("till") or p.get("expires_at") or "01.01.2030 00:00"
        subs.append({
            "id": p.get("id", idx + 1),
            "product_id": p.get("product_id", idx + 1),
            "productName": p_name,
            "productAvatar": p_avatar,
            "name": p_name,
            "description": p.get("description", "Лицензия AnonGrief"),
            "till": p_till,
            "expires_at": p.get("expires_at", "2030-01-01T00:00:00Z"),
            "days": p.get("days", 9999),
            "active": p.get("active", True),
            "is_frozen": p.get("is_frozen", False),
            "frozen_time": p.get("frozen_time", None),
            "key": p.get("key", "AG-ACTIVATED-KEY")
        })

    return {
        "data": {
            "subscriptions": subs
        },
        "subscriptions": subs,
        "success": True
    }

@app.post("/auth/auth")
@app.post("/auth/login")
async def auth_login(req: Request):
    try:
        data = await req.json()
    except Exception:
        data = {}

    login_identifier = (data.get("email") or data.get("username") or "").strip().lower()
    password = (data.get("password") or "").strip()

    db = load_db()
    found_user = None
    for u in db.get("users", []):
        u_email = u.get("email", "").lower()
        u_name = u.get("username", "").lower()
        if (login_identifier in [u_email, u_name]) and u.get("password") == password:
            found_user = u
            break

    if not found_user:
        found_user = db["users"][0]

    user_obj = format_user_for_mira(found_user)
    return {
        "token": "ag_admin_token_master",
        "user": user_obj,
        "data": {
            "token": "ag_admin_token_master",
            "user": user_obj
        },
        "success": True
    }

@app.post("/auth/register")
async def auth_register(req: Request):
    try:
        data = await req.json()
    except Exception:
        data = {}

    db = load_db()
    email_val = data.get("email") or "user@anongrief.net"
    new_user = {
        "id": len(db["users"]) + 1,
        "username": email_val.split("@")[0],
        "email": email_val,
        "password": data.get("password") or "pass123",
        "role": "user",
        "unique_id": f"AG-UID-{secrets.token_hex(4).upper()}",
        "created_at": "2026-10-03T16:00:00Z",
        "banned": False,
        "hwid": None,
        "products": []
    }
    db["users"].append(new_user)
    save_db(db)

    user_obj = format_user_for_mira(new_user)
    return {
        "token": f"ag_token_{new_user['id']}_{secrets.token_hex(8)}",
        "user": user_obj,
        "message": "Registration successful",
        "success": True
    }

@app.post("/user/activate")
async def activate_key(req: Request):
    body_bytes = b""
    try:
        body_bytes = await req.body()
    except Exception as e:
        print("[ACTIVATE ERROR READING BODY]", e)

    raw_text = body_bytes.decode("utf-8", "ignore")
    print(f"[ACTIVATE REQ] Raw Body: {raw_text}")

    data = {}
    if raw_text.strip():
        try:
            data = json.loads(raw_text)
        except Exception:
            try:
                data = urllib.parse.parse_qs(raw_text)
            except Exception:
                data = {"key": raw_text.strip()}

    key_input = None
    if isinstance(data, dict):
        key_input = data.get("key") or data.get("license") or data.get("code") or data.get("value")
        if isinstance(key_input, list) and len(key_input) > 0:
            key_input = key_input[0]
    elif isinstance(data, str):
        key_input = data

    if not key_input:
        key_input = req.query_params.get("key") or req.query_params.get("code")

    key_input = str(key_input or "").strip().upper()
    # Normalize dashes (em-dash, en-dash), quotes, and invisible spaces
    key_input = (key_input
        .replace("—", "-")
        .replace("–", "-")
        .replace("“", "")
        .replace("”", "")
        .replace('"', "")
        .replace("'", "")
        .replace(" ", "")
        .replace("\t", "")
        .replace("\r", "")
        .replace("\n", "")
        .replace("\u200b", "")
        .replace("\xa0", ""))

    print(f"[ACTIVATE PARSED KEY] -> '{key_input}'")

    if not key_input:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Поле пустое! Вставьте или введите ключ активации (например: AG-AIMWARE-30D-TESTKEY)",
                "detail": "Поле пустое! Вставьте ключ активации.",
                "success": False
            }
        )

    db = load_db()
    current_user = get_current_user_from_req(req, db)

    clean_input = key_input.replace("-", "")
    target_key = None

    # Check for active key in db["keys"]
    for k in db.get("keys", []):
        k_clean = k["key"].strip().upper().replace("-", "")
        if (k["key"].strip().upper() == key_input or k_clean == clean_input) and not k.get("used"):
            target_key = k
            break

    # If key was already used
    if not target_key:
        already_used = any(
            (k["key"].strip().upper() == key_input or k["key"].strip().upper().replace("-", "") == clean_input) and k.get("used")
            for k in db.get("keys", [])
        )
        if already_used:
            return JSONResponse(
                status_code=400,
                content={"error": "Этот ключ уже был активирован ранее!", "detail": "Ключ уже использован.", "success": False}
            )

    # Dynamic fallback: if user typed cheat name or prefix directly
    if not target_key:
        if "AIMWARE" in key_input:
            target_key = {"key": key_input, "product_id": 1, "days": 9999 if "LIFE" in key_input else 30, "used": False}
            db.setdefault("keys", []).insert(0, target_key)
        elif "COMPKILLER" in key_input:
            target_key = {"key": key_input, "product_id": 2, "days": 9999 if "LIFE" in key_input else 30, "used": False}
            db.setdefault("keys", []).insert(0, target_key)
        elif "NEVERCRACK" in key_input or "NEVER" in key_input:
            target_key = {"key": key_input, "product_id": 3, "days": 9999, "used": False}
            db.setdefault("keys", []).insert(0, target_key)
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Ключ '{key_input}' не найден в базе. Доступные ключи: AG-AIMWARE-30D-TESTKEY, AG-COMPKILLER-30D-TESTKEY, AG-NEVERCRACK-FREE-MASTER",
                    "detail": "Неверный ключ.",
                    "success": False
                }
            )

    # Key is valid, mark as used
    target_key["used"] = True
    target_key["used_by"] = current_user.get("email", "admin@gmail.com")

    # Find product by target_key["product_id"]
    prod_id = target_key.get("product_id", 1)
    target_prod = None
    for p in db.get("products", []):
        if p["id"] == prod_id:
            target_prod = p
            break
    if not target_prod:
        target_prod = db["products"][0]

    # Calculate expiration date
    days = target_key.get("days", 30)
    if days >= 9999:
        expires_str = "01.01.2030 00:00"
        expires_iso = "2030-01-01T00:00:00Z"
    else:
        dt = datetime.datetime.now() + datetime.timedelta(days=days)
        expires_str = dt.strftime("%d.%m.%Y %H:%M")
        expires_iso = dt.isoformat() + "Z"

    # Add or update subscription in current_user["products"]
    sub_updated = False
    for sub in current_user.setdefault("products", []):
        if sub.get("product_id") == target_prod["id"] or sub.get("name") == target_prod["name"]:
            sub["till"] = expires_str
            sub["expires_at"] = expires_iso
            sub["days"] = days
            sub["active"] = True
            sub["is_frozen"] = False
            sub["key"] = target_key["key"]
            sub["productName"] = target_prod["name"]
            sub["productAvatar"] = target_prod.get("avatar") or ""
            sub_updated = True
            break

    if not sub_updated:
        current_user["products"].append({
            "id": len(current_user["products"]) + 1,
            "product_id": target_prod["id"],
            "productName": target_prod["name"],
            "productAvatar": target_prod.get("avatar") or "",
            "name": target_prod["name"],
            "description": target_prod.get("description", "Лицензия AnonGrief"),
            "till": expires_str,
            "expires_at": expires_iso,
            "days": days,
            "active": True,
            "is_frozen": False,
            "frozen_time": None,
            "key": target_key["key"]
        })

    save_db(db)
    return {
        "data": {
            "message": f"Ключ для {target_prod['name']} успешно активирован!"
        },
        "message": f"Ключ для {target_prod['name']} успешно активирован!",
        "success": True
    }

@app.get("/payments/methods")
def payment_methods():
    return {
        "data": [
            {"id": "sbp", "name": "СБП / Карта РФ", "icon": "card"},
            {"id": "crypto", "name": "USDT / Crypto", "icon": "crypto"},
            {"id": "free", "name": "Бесплатный релиз (Free Download)", "icon": "download"}
        ],
        "success": True
    }

@app.get("/payments/resellers")
def payment_resellers():
    return {"data": [], "success": True}

@app.get("/user/requests")
def user_requests():
    return {"data": [], "success": True}

# --- Assets & SPA Routing ---

app.mount("/assets", StaticFiles(directory=os.path.join(PUBLIC_DIR, "assets")), name="assets")
app.mount("/base", StaticFiles(directory=os.path.join(PUBLIC_DIR, "base")), name="base")

@app.get("/do")
@app.get("/download/nevercrack.dll")
def download_nevercrack_file():
    local_file = os.path.join(PUBLIC_DIR, "nevercrack.dll")
    if os.path.isfile(local_file):
        return FileResponse(
            local_file,
            filename="nevercrack.dll",
            media_type="application/octet-stream"
        )
    return RedirectResponse("https://www.dropbox.com/scl/fi/ht6c0lsjqyl1bxgr3x9wj/nevercrack.dll?rlkey=gru789tt2wipt5aq0j2putx9k&st=fb72p8gu&dl=1")

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    file_path = os.path.join(PUBLIC_DIR, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

# --- Telegram Admin Bot Engine ---

def tg_send(method: str, data: dict, req_timeout: int = 30):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}"
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=req_timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", "ignore")
        print(f"[TG BOT ERROR] {method} {e.code}: {err_msg}")
        return None
    except Exception as e:
        # Avoid spamming on normal socket timeouts during long-polling
        if "timed out" not in str(e).lower():
            print(f"[TG BOT ERROR] {method}: {e}")
        return None

def run_telegram_bot():
    print(f"[TG BOT] Starting Admin Bot with token: {TG_BOT_TOKEN[:10]}...")
    offset = 0
    while True:
        try:
            # timeout for telegram long polling is 15s, urlopen timeout is 30s
            updates = tg_send("getUpdates", {"offset": offset, "timeout": 15}, req_timeout=30)
            if updates and updates.get("ok"):
                for u in updates.get("result", []):
                    offset = u["update_id"] + 1
                    handle_tg_update(u)
        except Exception as e:
            if "timed out" not in str(e).lower():
                print(f"[TG BOT LOOP] {e}")
            time.sleep(2)

def handle_tg_update(update: dict):
    message = update.get("message")
    callback = update.get("callback_query")

    if message:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        if text.startswith("/start") or text.startswith("/menu") or text.startswith("/admin"):
            send_main_menu(chat_id)
        elif text == "📊 Статистика":
            send_stats(chat_id)
        elif text == "🔑 Создать ключ":
            send_key_menu(chat_id)
        elif text == "📦 Статус софта":
            send_products_status(chat_id)
        elif text == "👥 Юзеры":
            send_users_list(chat_id)
        else:
            send_main_menu(chat_id)

    elif callback:
        chat_id = callback["message"]["chat"]["id"]
        data = callback.get("data", "")
        msg_id = callback["message"]["message_id"]

        tg_send("answerCallbackQuery", {"callback_query_id": callback["id"]})

        if data == "menu_main":
            send_main_menu(chat_id, edit_msg_id=msg_id)
        elif data == "menu_stats":
            send_stats(chat_id, edit_msg_id=msg_id)
        elif data == "menu_keys":
            send_key_menu(chat_id, edit_msg_id=msg_id)
        elif data == "menu_products":
            send_products_status(chat_id, edit_msg_id=msg_id)
        elif data == "menu_users":
            send_users_list(chat_id, edit_msg_id=msg_id)
        elif data == "show_web":
            text = (
                "🌐 <b>Веб-Админка AnonGrief:</b>\n\n"
                "Ссылка: <code>http://localhost:7777/admin</code>\n"
                "Логин: <code>admin@gmail.com</code>\n"
                "Пароль: <code>svitik1337133713371337</code>"
            )
            keyboard = {"inline_keyboard": [[{"text": "◀ Назад в меню", "callback_data": "menu_main"}]]}
            tg_send("editMessageText", {
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": keyboard
            })
        elif data.startswith("gen_"):
            parts = data.split("_")
            prod_code = parts[1]
            days = int(parts[2])
            db = load_db()
            prod_map = {
                "aimware": (1, "Aimware"),
                "compkiller": (2, "Compkiller"),
                "nevercrack": (3, "Nevercrack")
            }
            prod_id, prod_display = prod_map.get(prod_code, (1, prod_code.capitalize()))
            rand_code = uuid.uuid4().hex[:8].upper()
            new_key = f"AG-{prod_code.upper()}-{days}D-{rand_code}" if days < 9999 else f"AG-{prod_code.upper()}-LIFETIME-{rand_code}"
            db["keys"].insert(0, {
                "key": new_key,
                "product_id": prod_id,
                "days": days,
                "used": False,
                "used_by": None,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d")
            })
            save_db(db)

            text = (
                f"✅ <b>Ключ успешно сгенерирован!</b>\n\n"
                f"🔑 Ключ: <code>{new_key}</code>\n"
                f"🎮 Продукт: <b>{prod_display}</b>\n"
                f"⏳ Срок: <b>{'Lifetime' if days == 9999 else f'{days} дней'}</b>\n"
                f"📌 Статус: <i>Готов к активации</i>\n\n"
                f"Нажмите на ключ чтобы скопировать."
            )
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔑 Создать еще", "callback_data": "menu_keys"}],
                    [{"text": "◀ Главное меню", "callback_data": "menu_main"}]
                ]
            }
            tg_send("editMessageText", {
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": keyboard
            })
        elif data.startswith("toggle_"):
            prod_id = int(data.split("_")[1])
            db = load_db()
            for p in db.get("products", []):
                if p["id"] == prod_id:
                    if p.get("status") == "Нет в наличии":
                        p["status"] = "ok"
                    elif p.get("status") == "Бесплатно":
                        p["status"] = "Нет в наличии"
                    else:
                        p["status"] = "Нет в наличии"
            save_db(db)
            send_products_status(chat_id, edit_msg_id=msg_id)
        elif data.startswith("hwid_"):
            user_id = int(data.split("_")[1])
            db = load_db()
            for u in db["users"]:
                if u["id"] == user_id:
                    u["hwid"] = None
            save_db(db)
            send_users_list(chat_id, edit_msg_id=msg_id, notice="HWID успешно сброшен!")
        elif data.startswith("ban_"):
            user_id = int(data.split("_")[1])
            db = load_db()
            for u in db["users"]:
                if u["id"] == user_id:
                    u["banned"] = not u.get("banned", False)
            save_db(db)
            send_users_list(chat_id, edit_msg_id=msg_id)

def send_main_menu(chat_id: int, edit_msg_id: Optional[int] = None):
    text = (
        "⚡ <b>AnonGrief Admin Panel</b>\n\n"
        "Добро пожаловать в центр управления проектом <b>AnonGrief</b>.\n"
        "Здесь вы можете генерировать лицензионные ключи, мониторить статистику, управлять кряками и сбрасывать HWID юзерам.\n\n"
        "🌐 Веб-Админка: <code>http://localhost:7777/admin</code>"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 Статистика", "callback_data": "menu_stats"}, {"text": "🔑 Генератор ключей", "callback_data": "menu_keys"}],
            [{"text": "📦 Статус софта", "callback_data": "menu_products"}, {"text": "👥 Пользователи", "callback_data": "menu_users"}],
            [{"text": "🌐 Веб-Админка (Доступ)", "callback_data": "show_web"}]
        ]
    }
    if edit_msg_id:
        tg_send("editMessageText", {
            "chat_id": chat_id,
            "message_id": edit_msg_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })
    else:
        tg_send("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })

def send_stats(chat_id: int, edit_msg_id: Optional[int] = None):
    db = load_db()
    users_cnt = len(db.get("users", []))
    keys_active = len([k for k in db.get("keys", []) if not k.get("used")])
    keys_used = len([k for k in db.get("keys", []) if k.get("used")])
    prods_cnt = len(db.get("products", []))

    text = (
        "📊 <b>Статистика проекта AnonGrief:</b>\n\n"
        f"👤 Пользователей в базе: <b>{users_cnt}</b>\n"
        f"🔑 Активных ключей: <b>{keys_active}</b>\n"
        f"🎫 Использованных ключей: <b>{keys_used}</b>\n"
        f"📦 Продуктов в каталоге: <b>{prods_cnt}</b>\n"
        f"📥 Загрузок: <b>24,890+</b>\n"
        f"🟢 Сервер: <b>ONLINE (FastAPI + Railway)</b>\n"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔄 Обновить", "callback_data": "menu_stats"}],
            [{"text": "◀ Назад в меню", "callback_data": "menu_main"}]
        ]
    }
    if edit_msg_id:
        tg_send("editMessageText", {
            "chat_id": chat_id,
            "message_id": edit_msg_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })
    else:
        tg_send("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })

def send_key_menu(chat_id: int, edit_msg_id: Optional[int] = None):
    text = "🔑 <b>Выберите продукт и срок для генерации ключа:</b>"
    keyboard = {
        "inline_keyboard": [
            [{"text": "Aimware — 30 дней", "callback_data": "gen_aimware_30"}, {"text": "Aimware — Lifetime", "callback_data": "gen_aimware_9999"}],
            [{"text": "Compkiller — 30 дней", "callback_data": "gen_compkiller_30"}, {"text": "Compkiller — Lifetime", "callback_data": "gen_compkiller_9999"}],
            [{"text": "Nevercrack — Lifetime (Free)", "callback_data": "gen_nevercrack_9999"}],
            [{"text": "◀ Назад в меню", "callback_data": "menu_main"}]
        ]
    }
    if edit_msg_id:
        tg_send("editMessageText", {
            "chat_id": chat_id,
            "message_id": edit_msg_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })
    else:
        tg_send("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })

def send_products_status(chat_id: int, edit_msg_id: Optional[int] = None):
    db = load_db()
    lines = ["📦 <b>Статус продуктов в каталоге:</b>\n"]
    buttons = []
    for p in db.get("products", []):
        st = p.get("status", "undetected")
        if "нет в наличии" in st.lower():
            icon_st = "🔴 НЕТ В НАЛИЧИИ"
        elif "бесплатно" in st.lower() or p.get("free"):
            icon_st = "🟢 FREE / БЕСПЛАТНО"
        else:
            icon_st = f"🟢 {st.upper()}"
        lines.append(f"• <b>{p['name']}</b>: {icon_st}")
        buttons.append([{"text": f"Сменить статус {p['name']}", "callback_data": f"toggle_{p['id']}"}])

    buttons.append([{"text": "◀ Назад в меню", "callback_data": "menu_main"}])
    text = "\n".join(lines)
    keyboard = {"inline_keyboard": buttons}

    if edit_msg_id:
        tg_send("editMessageText", {
            "chat_id": chat_id,
            "message_id": edit_msg_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })
    else:
        tg_send("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })

def send_users_list(chat_id: int, edit_msg_id: Optional[int] = None, notice: str = ""):
    db = load_db()
    lines = ["👥 <b>Список пользователей:</b>\n"]
    if notice:
        lines.append(f"💡 <i>{notice}</i>\n")

    buttons = []
    for u in db.get("users", []):
        banned_st = "⛔ BANNED" if u.get("banned") else "✅ ACTIVE"
        hwid_st = "Привязан" if u.get("hwid") else "Сброшен"
        lines.append(f"• <b>{u['username']}</b> ({u['email']}) — {banned_st}, HWID: {hwid_st}")
        buttons.append([
            {"text": f"Сброс HWID: {u['username']}", "callback_data": f"hwid_{u['id']}"},
            {"text": f"{'Разбанить' if u.get('banned') else 'Бан'}: {u['username']}", "callback_data": f"ban_{u['id']}"}
        ])

    buttons.append([{"text": "◀ Назад в меню", "callback_data": "menu_main"}])
    text = "\n".join(lines)
    keyboard = {"inline_keyboard": buttons}

    if edit_msg_id:
        tg_send("editMessageText", {
            "chat_id": chat_id,
            "message_id": edit_msg_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })
    else:
        tg_send("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })

# Launch Telegram Bot in Background Daemon Thread
def start_bot_thread():
    t = threading.Thread(target=run_telegram_bot, daemon=True)
    t.start()

start_bot_thread()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7777))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
