
import os
import time
import hmac
import hashlib
import json
import requests
from flask import Flask, jsonify

CLIENT_ID   = os.environ.get("TUYA_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("TUYA_CLIENT_SECRET", "").strip()
DEVICE_ID   = os.environ.get("TUYA_DEVICE_ID", "").strip()
REGION      = os.environ.get("TUYA_REGION", "eu").strip()
DP_CODE     = os.environ.get("TUYA_DP_CODE", "switch").strip()

REGION_MAP = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}
BASE = REGION_MAP.get(REGION.lower(), REGION_MAP["eu"])

_access_token = None
_token_expire = 0

def _hmac_sign(message: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest().upper()

def _sha256hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _headers(method: str, path: str, query: str, body: str, need_token: bool):
    global _access_token
    t = str(int(time.time()*1000))
    body_hash = _sha256hex(body or "")
    string_to_sign = f"{method}\n{body_hash}\n\n{path}{query}"
    if need_token and _access_token:
        sign_str = CLIENT_ID + _access_token + t + string_to_sign
    else:
        sign_str = CLIENT_ID + t + string_to_sign
    sign = _hmac_sign(sign_str, CLIENT_SECRET)
    headers = {
        "client_id": CLIENT_ID,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "Content-Type": "application/json; charset=utf-8",
    }
    if need_token and _access_token:
        headers["access_token"] = _access_token
    return headers

def _request(method: str, path: str, params=None, body=None, need_token=True):
    global _access_token, _token_expire
    if params is None: params = {}
    query = ""
    if params:
        from urllib.parse import urlencode
        query = "?" + urlencode(params)
    url = BASE + path + query
    data = "" if body is None else json.dumps(body, separators=(",", ":"))
    headers = _headers(method, path, query, data, need_token)
    r = requests.request(method, url, headers=headers, data=data, timeout=15)
    if r.status_code == 401 and need_token:
        _access_token = None
        _token_expire = 0
        _get_token(force=True)
        headers = _headers(method, path, query, data, need_token=True)
        r = requests.request(method, url, headers=headers, data=data, timeout=15)
    r.raise_for_status()
    return r.json()

def _get_token(force=False):
    global _access_token, _token_expire
    if not force and _access_token and time.time() < _token_expire - 60:
        return _access_token
    path = "/v1.0/token?grant_type=1"
    res = _request("GET", path, need_token=False)
    if not res.get("success"):
        raise RuntimeError(f"Token failed: {res}")
    _access_token = res["result"]["access_token"]
    _token_expire = time.time() + int(res["result"].get("expire_time", 7000))
    return _access_token

def _ensure_config():
    missing = []
    if not CLIENT_ID: missing.append("TUYA_CLIENT_ID")
    if not CLIENT_SECRET: missing.append("TUYA_CLIENT_SECRET")
    if not DEVICE_ID: missing.append("TUYA_DEVICE_ID")
    if BASE is None: missing.append("TUYA_REGION")
    if missing:
        raise RuntimeError("Missing env: " + ", ".join(missing))

def tuya_switch(value: bool):
    _ensure_config()
    _get_token()
    body = {"commands":[{"code": DP_CODE, "value": bool(value)}]}
    path = f"/v1.0/devices/{DEVICE_ID}/commands"
    res = _request("POST", path, body=body, need_token=True)
    return res

def tuya_status():
    _ensure_config()
    _get_token()
    path = f"/v1.0/devices/{DEVICE_ID}/status"
    return _request("GET", path, need_token=True)

from flask import Flask
app = Flask(__name__)

@app.route("/")
def root():
    return jsonify(ok=True, device=DEVICE_ID, region=REGION, dp_code=DP_CODE)

@app.route("/ac/on")
def ac_on():
    try:
        r = tuya_switch(True)
        return jsonify(ok=True, action="on", tuya=r)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route("/ac/off")
def ac_off():
    try:
        r = tuya_switch(False)
        return jsonify(ok=True, action="off", tuya=r)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route("/ac/status")
def ac_status():
    try:
        r = tuya_status()
        return jsonify(ok=True, status=r)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
