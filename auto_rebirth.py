import requests
import time
import math

# ===========================
# KONSTANTA
# ===========================
SUPABASE_URL    = "https://qsoptshiorjhoiwwrumb.supabase.co/auth/v1/token"
SUPABASE_APIKEY = "sb_publishable_OtJtVXVlBl7_JPubRQg6rA_5uyAGLqP"
GAME_URL        = "https://fishin-chiyo.vercel.app/api/game/action"

# ===========================
# KONFIGURASI AUTO REBIRTH
# ===========================
CONFIG = {
    "auto_rebirth": True,          # aktifkan auto rebirth
    "auto_cast": True,             # auto cast setelah rebirth
    "auto_sell": True,             # auto sell
    "auto_upgrade": True,          # auto upgrade setelah rebirth
    "cast_per_cycle": 10,          # jumlah cast per siklus
    "delay_between_cast": 0.3,     # delay antar cast (detik)
    "delay_after_sell": 0.5,       # delay setelah sell
    "delay_after_rebirth": 3,      # delay setelah rebirth (server perlu waktu)
    "max_rebirth_count": 50,       # batas rebirth (0 = unlimited)
}

# ===========================
# UPGRADE DATA (dari game source)
# ===========================
UPGRADE_DATA = {
    "rod":             {"baseCost": 20,   "costMul": 1.32},
    "reel":            {"baseCost": 90,   "costMul": 1.34},
    "market_bell":     {"baseCost": 140,  "costMul": 1.33},
    "bait":            {"baseCost": 120,  "costMul": 1.30},
    "bobber":          {"baseCost": 160,  "costMul": 1.31},
    "hook":            {"baseCost": 180,  "costMul": 1.30},
    "reinforced_hook": {"baseCost": 260,  "costMul": 1.28},
    "junk_filter":     {"baseCost": 420,  "costMul": 1.27},
    "tackle_brush":    {"baseCost": 640,  "costMul": 1.28},
    "repair_kit":      {"baseCost": 800,  "costMul": 1.29},
    "auto_repair_hook":{"baseCost": 950,  "costMul": 1.28},
    "tackle_net":      {"baseCost": 1100, "costMul": 1.24},
    "weather_vane":    {"baseCost": 2200, "costMul": 1.27},
    "dock":            {"baseCost": 180,  "costMul": 1.36},
    "tacklebox":       {"baseCost": 50,   "costMul": 1.20},
    "crew":            {"baseCost": 600,  "costMul": 1.35},
}


# ===========================
# REBIRTH FORMULA (dari index.js)
# thresholdForRebirth = sa(1e6 * 1.14^min(max(0,count),20) * 1.06^max(0,count-20), "ceil")
# tokensFromRun = lifetimeCoins >= threshold ? 1 : 0
# multiplierFromTokens = 1 + 0.08*log1p(tokens*1.8) + 0.02*sqrt(tokens)
# ===========================
def threshold_for_rebirth(prestige_count):
    """Hitung minimum lifetime coins yang dibutuhkan untuk rebirth berikutnya."""
    count = max(0, int(prestige_count or 0))
    base = 1_000_000  # 1e6
    # Scaling: 1.14^min(count,20) * 1.06^max(0,count-20)
    threshold = base * (1.14 ** min(count, 20)) * (1.06 ** max(0, count - 20))
    return math.ceil(threshold)


def can_rebirth(state):
    """Cek apakah bisa rebirth berdasarkan lifetimeCoins dan prestigeCount."""
    lifetime_coins = state.get("lifetimeCoins", 0)
    prestige_count = state.get("prestigeCount", 0)
    threshold = threshold_for_rebirth(prestige_count)
    return lifetime_coins >= threshold


def multiplier_from_tokens(tokens):
    """Hitung multiplier permanent dari total prestige tokens."""
    t = max(0, int(tokens or 0))
    return 1 + 0.08 * math.log1p(t * 1.8) + 0.02 * math.sqrt(t)


def get_total_tokens(state):
    """Total tokens yang sudah dimiliki (lifetime)."""
    return max(
        int(state.get("prestigeLifetimeTokens", 0)),
        int(state.get("prestigeTokens", 0))
    )


def tokens_from_run(state):
    """Berapa token yang didapat dari run ini jika rebirth sekarang."""
    lifetime_coins = state.get("lifetimeCoins", 0)
    prestige_count = state.get("prestigeCount", 0)
    threshold = threshold_for_rebirth(prestige_count)
    if lifetime_coins >= threshold:
        return 1
    return 0


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
    headers = {"Content-Type": "application/json", "apikey": SUPABASE_APIKEY}
    payload = {"refresh_token": refresh_token}
    params  = {"grant_type": "refresh_token"}

    try:
        response = requests.post(SUPABASE_URL, params=params, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            new_access  = data.get("access_token")
            new_refresh = data.get("refresh_token")
            if new_access:
                save_bearer(new_access)
                print("[REFRESH TOKEN] access_token baru disimpan")
            if new_refresh:
                save_refresh_token(new_refresh)
                print("[REFRESH TOKEN] refresh_token baru disimpan")
            return new_access
        else:
            print(f"[REFRESH TOKEN] Gagal! Status: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"[REFRESH TOKEN] Error: {e}")
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

    try:
        response = requests.post(GAME_URL, headers=make_headers(), json=payload, timeout=30)
    except requests.exceptions.Timeout:
        print(f"[{action_type.upper()}] Timeout! Server tidak merespon dalam 30 detik.")
        return {"retry": True, "repair": False, "revision": revision_value,
                "success": False, "state": {}}
    except requests.exceptions.ConnectionError as e:
        print(f"[{action_type.upper()}] Connection error: {e}")
        return {"retry": True, "repair": False, "revision": revision_value,
                "success": False, "state": {}}

    if response.status_code == 401:
        new_token = refresh_access_token()
        if new_token:
            try:
                response = requests.post(GAME_URL, headers=make_headers(), json=payload, timeout=30)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                return {"retry": True, "repair": False, "revision": revision_value,
                        "success": False, "state": {}}
        else:
            return {"retry": False, "repair": False, "revision": revision_value,
                    "success": False, "state": {}}

    try:
        data     = response.json()
        state    = data.get("state", {})
        latest_revision = data.get("revision", state.get("revision", revision_value))

        if response.status_code == 409:
            return {"retry": True, "repair": False, "revision": latest_revision,
                    "success": False, "state": state}

        if response.status_code == 400:
            return {"retry": False, "repair": True, "revision": latest_revision,
                    "success": False, "state": state}

        return {"retry": False, "repair": False, "revision": latest_revision,
                "success": response.status_code == 200, "state": state}

    except Exception as e:
        print(f"[{action_type.upper()}] Error: {e}")
        return {"retry": False, "repair": False, "revision": revision_value,
                "success": False, "state": {}}


# ===========================
# REPAIR HOOK
# ===========================
def repair_hook(revision):
    print("[REPAIR] Membersihkan & memperbaiki hook...")
    result = send_action("cleanHook", {"score": 1}, revision)
    revision = result["revision"]
    result = send_action("repairHook", {}, revision)
    revision = result["revision"]
    return revision


# ===========================
# EXECUTE ACTION WITH RETRY
# ===========================
def execute_action(action_type, payload_data, revision, max_retries=5):
    """Execute an action with automatic retry/repair handling."""
    for attempt in range(max_retries):
        result = send_action(action_type, payload_data, revision)
        revision = result["revision"]

        if result.get("retry"):
            print(f"  [RETRY] Attempt {attempt+1}/{max_retries}...")
            time.sleep(2)
            continue

        if result.get("repair"):
            revision = repair_hook(revision)
            time.sleep(3)
            continue

        return result

    print(f"  [{action_type.upper()}] Gagal setelah {max_retries} percobaan.")
    return result


# ===========================
# AUTO REBIRTH (PRESTIGE)
# ===========================
def do_rebirth(revision, state):
    """Lakukan rebirth/prestige jika memenuhi syarat."""
    if not can_rebirth(state):
        return revision, state, False

    prestige_count = state.get("prestigeCount", 0)
    lifetime_coins = state.get("lifetimeCoins", 0)
    threshold = threshold_for_rebirth(prestige_count)
    current_tokens = get_total_tokens(state)
    new_multiplier = multiplier_from_tokens(current_tokens + 1)

    print("\n" + "=" * 55)
    print("  *** REBIRTH READY! ***")
    print("=" * 55)
    print(f"  Prestige Count  : {prestige_count}")
    print(f"  Lifetime Coins  : {lifetime_coins:,.0f}")
    print(f"  Threshold       : {threshold:,.0f}")
    print(f"  Current Tokens  : {current_tokens}")
    print(f"  New Multiplier  : x{new_multiplier:.4f}")
    print("=" * 55)

    print("\n[REBIRTH] Mengirim prestige action...")
    result = execute_action("prestige", {}, revision)
    revision = result["revision"]

    if result.get("success"):
        state = result.get("state", {})
        new_prestige_count = state.get("prestigeCount", prestige_count + 1)
        new_tokens = get_total_tokens(state)
        print(f"\n[REBIRTH] BERHASIL! Prestige #{new_prestige_count}")
        print(f"[REBIRTH] Total Tokens: {new_tokens}")
        print(f"[REBIRTH] Multiplier: x{multiplier_from_tokens(new_tokens):.4f}")
        time.sleep(CONFIG["delay_after_rebirth"])
        return revision, state, True
    else:
        print("[REBIRTH] GAGAL! Mungkin syarat belum terpenuhi di server.")
        return revision, state, False


# ===========================
# PRINT REBIRTH STATUS
# ===========================
def print_rebirth_status(state):
    prestige_count = state.get("prestigeCount", 0)
    lifetime_coins = state.get("lifetimeCoins", 0)
    coins          = state.get("coins", 0)
    threshold      = threshold_for_rebirth(prestige_count)
    current_tokens = get_total_tokens(state)
    current_mult   = multiplier_from_tokens(current_tokens)
    next_mult      = multiplier_from_tokens(current_tokens + 1)
    progress       = min(100, (lifetime_coins / threshold) * 100) if threshold > 0 else 0

    ready = "YES" if lifetime_coins >= threshold else "NO"
    bar_len = 30
    filled = int(bar_len * progress / 100)
    bar = "#" * filled + "-" * (bar_len - filled)

    print("\n" + "=" * 55)
    print("  REBIRTH STATUS")
    print("=" * 55)
    print(f"  Prestige Count   : {prestige_count}")
    print(f"  Coins (current)  : {coins:,.0f}")
    print(f"  Lifetime Coins   : {lifetime_coins:,.0f}")
    print(f"  Threshold        : {threshold:,.0f}")
    print(f"  Progress         : [{bar}] {progress:.1f}%")
    print(f"  Ready to Rebirth : {ready}")
    print(f"  Current Tokens   : {current_tokens} (x{current_mult:.4f})")
    print(f"  Next Multiplier  : x{next_mult:.4f} (+{(next_mult - current_mult):.4f})")
    print("=" * 55)


# ===========================
# AUTO UPGRADE (simple: buy cheapest available)
# ===========================
def auto_upgrade_after_rebirth(revision, state):
    """Upgrade setelah rebirth - prioritas: rod, bait, reel, market_bell."""
    if not CONFIG["auto_upgrade"]:
        return revision, state

    coins = state.get("coins", 0)
    upgrades = state.get("upgrades", {})

    priority = ["rod", "bait", "reel", "market_bell", "bobber", "hook",
                "tacklebox", "dock", "reinforced_hook", "junk_filter"]

    bought_something = True
    while bought_something:
        bought_something = False
        for uid in priority:
            data = UPGRADE_DATA.get(uid)
            if not data:
                continue
            current_level = upgrades.get(uid, 0)
            cost = data["baseCost"] * (data["costMul"] ** current_level)

            if coins >= cost:
                result = execute_action("buyUpgrade", {"id": uid, "count": 1}, revision)
                revision = result["revision"]
                if result.get("success"):
                    state = result.get("state", state)
                    coins = state.get("coins", 0)
                    upgrades = state.get("upgrades", upgrades)
                    bought_something = True
                time.sleep(0.1)

    return revision, state


# ===========================
# MAIN LOOP
# ===========================
def main():
    print("=" * 55)
    print("  FISHIN' CHIYO - AUTO REBIRTH BOT")
    print("  Features: Auto Cast, Sell, Rebirth, Upgrade")
    print("=" * 55)

    revision = 0
    rebirth_count = 0

    # --- INISIALISASI: ambil state awal via sell ---
    print("\n[INIT] Mengambil state awal...")
    result = execute_action("sell", {}, revision)
    revision = result["revision"]
    state = result.get("state", {})

    if not state:
        print("[ERROR] Tidak bisa mendapatkan state. Cek bearer/refresh token!")
        return

    print(f"[INIT] Player: {state.get('user', {}).get('name', 'Unknown')}")
    print(f"[INIT] Zone: {state.get('zoneId', '?')}")
    print_rebirth_status(state)

    # --- MAIN LOOP ---
    while True:
        # Cek limit rebirth
        if CONFIG["max_rebirth_count"] > 0 and rebirth_count >= CONFIG["max_rebirth_count"]:
            print(f"\n[DONE] Sudah rebirth {rebirth_count}x. Berhenti.")
            break

        # === CEK REBIRTH ===
        if CONFIG["auto_rebirth"] and can_rebirth(state):
            revision, state, success = do_rebirth(revision, state)
            if success:
                rebirth_count += 1
                print(f"\n[INFO] Total rebirth session ini: {rebirth_count}")

                # Auto upgrade setelah rebirth
                revision, state = auto_upgrade_after_rebirth(revision, state)
                continue  # Langsung loop lagi

        # === CAST ===
        for i in range(CONFIG["cast_per_cycle"]):
            result = execute_action("cast", {"fightGrade": "perfect", "auto": False}, revision)
            revision = result["revision"]
            if result.get("success"):
                state = result.get("state", state)
            time.sleep(CONFIG["delay_between_cast"])

        # === SELL ===
        result = execute_action("sell", {}, revision)
        revision = result["revision"]
        if result.get("success"):
            state = result.get("state", state)
        time.sleep(CONFIG["delay_after_sell"])

        # === AUTO UPGRADE ===
        revision, state = auto_upgrade_after_rebirth(revision, state)

        # === PRINT STATUS ===
        print_rebirth_status(state)

        # Cek rebirth lagi setelah earn coins
        if CONFIG["auto_rebirth"] and can_rebirth(state):
            revision, state, success = do_rebirth(revision, state)
            if success:
                rebirth_count += 1
                print(f"\n[INFO] Total rebirth session ini: {rebirth_count}")
                revision, state = auto_upgrade_after_rebirth(revision, state)


# ==================================
# ENTRY POINT
# ==================================
if __name__ == "__main__":
    main()
