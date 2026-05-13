import requests
import time

# ===========================
# KONSTANTA
# ===========================
SUPABASE_URL = "https://qsoptshiorjhoiwwrumb.supabase.co/auth/v1/token"
SUPABASE_APIKEY = "sb_publishable_OtJtVXVlBl7_JPubRQg6rA_5uyAGLqP"
GAME_URL = "https://fishin-chiyo.vercel.app/api/game/action"


# ===========================
# LOAD / SAVE TOKEN
# ===========================
def load_bearer():
    with open("bearer.txt", "r", encoding="utf-8") as f:
        return f.read().strip()

def load_refresh_token():
    with open("refresh_token.txt", "r", encoding="utf-8") as f:
        return f.read().strip()

def save_bearer(token):
    with open("bearer.txt", "w", encoding="utf-8") as f:
        f.write(token)

def save_refresh_token(token):
    with open("refresh_token.txt", "w", encoding="utf-8") as f:
        f.write(token)


# ===========================
# REFRESH TOKEN
# ===========================
def refresh_access_token():
    print("\n[REFRESH TOKEN] Bearer kadaluarsa, mencoba refresh...")

    refresh_token = load_refresh_token()
    print(f"[REFRESH TOKEN] Menggunakan refresh_token: {refresh_token}")

    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_APIKEY
    }
    payload = {"refresh_token": refresh_token}
    params = {"grant_type": "refresh_token"}

    try:
        response = requests.post(SUPABASE_URL, params=params, headers=headers, json=payload)

        print(f"[REFRESH TOKEN] Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            new_access_token  = data.get("access_token")
            new_refresh_token = data.get("refresh_token")

            if new_access_token:
                save_bearer(new_access_token)
                print("[REFRESH TOKEN] access_token baru disimpan ke bearer.txt")

            if new_refresh_token:
                save_refresh_token(new_refresh_token)
                print("[REFRESH TOKEN] refresh_token baru disimpan ke refresh_token.txt")

            return new_access_token

        else:
            print("[REFRESH TOKEN] Gagal refresh token!")
            print(response.text)
            return None

    except Exception as e:
        print("[REFRESH TOKEN] Error:", e)
        return None


# ===========================
# HEADERS
# ===========================
def make_headers():
    return {
        "Authorization": f"Bearer {load_bearer()}",
        "Content-Type": "application/json",
        "Referer": "https://fishin-chiyo.vercel.app/",
        "User-Agent": "Mozilla/5.0"
    }


# ===========================
# SEND ACTION
# ===========================
def send_action(action_type, payload_data, revision_value):
    payload = {
        "type": action_type,
        "payload": payload_data,
        "revision": revision_value
    }

    response = requests.post(GAME_URL, headers=make_headers(), json=payload)

    print(f"\n[{action_type.upper()}] Status Code: {response.status_code}")

    # Bearer kadaluarsa → refresh dulu lalu retry
    if response.status_code == 401:
        print("Bearer kadaluarsa → refresh token...")
        new_token = refresh_access_token()

        if new_token:
            print("Token berhasil diperbarui, retry action...")
            response = requests.post(GAME_URL, headers=make_headers(), json=payload)
            print(f"[{action_type.upper()} RETRY] Status Code: {response.status_code}")
        else:
            print("Gagal refresh token, berhenti...")
            return {
                "retry": False,
                "repair": False,
                "revision": revision_value,
                "success": False
            }

    try:
        data = response.json()

        state = data.get("state", {})
        user  = state.get("user", {})

        name  = user.get("name", "Unknown")
        coins = state.get("coins", 0)
        gems  = state.get("gems", 0)

        latest_revision = data.get(
            "revision",
            state.get("revision", revision_value)
        )

        print(f"Nama      : {name}")
        print(f"Coins     : {coins}")
        print(f"Gems      : {gems}")
        print(f"Revision  : {latest_revision}")

        # Conflict revision
        if response.status_code == 409:
            print("Cloud save berubah, retry...")
            return {
                "retry": True,
                "repair": False,
                "revision": latest_revision,
                "success": False
            }

        # Hook rusak
        if response.status_code == 400:
            print("Hook rusak → repairHook")
            return {
                "retry": False,
                "repair": True,
                "revision": latest_revision,
                "success": False
            }

        return {
            "retry": False,
            "repair": False,
            "revision": latest_revision,
            "success": response.status_code == 200
        }

    except Exception as e:
        print("Gagal membaca response JSON")
        print("Detail Error:", e)
        print(response.text)

        return {
            "retry": False,
            "repair": False,
            "revision": revision_value,
            "success": False
        }


# ===========================
# REPAIR HOOK
# ===========================
def repair_hook_with_fallback(revision_value):
    print("Mencoba repairHook...")

    repair_result = send_action("repairHook", {}, revision_value)
    revision_value = repair_result["revision"]

    # Jika repairHook masih 400 → cleanHook
    if repair_result.get("repair"):
        print("repairHook masih 400 → cleanHook...")
        clean_result = send_action("cleanHook", {"score": 1}, revision_value)
        revision_value = clean_result["revision"]
        print("cleanHook selesai")

    return revision_value


# ==================================
# LOOP SELAMANYA
# ==================================
revision = 271

while True:

    # =========================
    # STEP 1 - SELL
    # =========================
    while True:
        result = send_action("sell", {}, revision)
        revision = result["revision"]

        if result.get("retry"):
            time.sleep(1)
            continue

        if result.get("repair"):
            revision = repair_hook_with_fallback(revision)
            print("Menunggu 5 detik setelah repair hook...")
            time.sleep(5)
            continue

        if result.get("success"):
            print("\nSELL berhasil")
            break

        print("SELL gagal")
        time.sleep(3)

    # =========================
    # STEP 2 - CAST 10x
    # =========================
    for i in range(10):

        while True:
            result = send_action(
                "cast",
                {"fightGrade": "perfect", "auto": False},
                revision
            )
            revision = result["revision"]

            if result.get("retry"):
                time.sleep(1)
                continue

            if result.get("repair"):
                revision = repair_hook_with_fallback(revision)
                print("Hook berhasil diperbaiki")
                print("Menunggu 5 detik sebelum lanjut...")
                time.sleep(5)
                continue

            if result.get("success"):
                print(f"Cast ke-{i+1} berhasil")
                break

            print(f"Cast ke-{i+1} gagal")
            break

    print("\n=== Mengulang ke SELL ===\n")