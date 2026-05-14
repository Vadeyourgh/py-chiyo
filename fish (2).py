import requests
import time
import json
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
AUTO_REBIRTH_ENABLED = True       # Set False untuk disable auto rebirth
AUTO_REBIRTH_MAX     = 0          # 0 = unlimited, atau angka batas rebirth per session

# Formula upgrade: cost = baseCost * costMul ^ currentLevel
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

# Urutan zone berdasarkan lineReq (index = lineReq)
ZONE_ORDER = [
    "pond",               # 0
    "lake",               # 1
    "river",              # 2
    "marsh",              # 3
    "pier",               # 4
    "reef",               # 5
    "open",               # 6
    "kelp",               # 7
    "storm",              # 8
    "frozen",             # 9
    "twilight",           # 10
    "abyss",              # 11
    "garden",             # 12
    "glass_current",      # 13
    "ember_vent",         # 14
    "starfall_rift",      # 15
    "moon_bloom",         # 16
    "clockwork_tide",     # 17
    "dreamwhale_expanse", # 18
    "astral_tide",        # 19
    "echoing_orbit",      # 20
]

# Charter fee per line level (index = current line, value = fee untuk unlock zone berikutnya)
CHARTER_FEES = [
    125,               # 0→1  pond→lake
    450,               # 1→2  lake→river
    1_700,             # 2→3  river→marsh
    5_500,             # 3→4  marsh→pier
    19_000,            # 4→5  pier→reef
    62_000,            # 5→6  reef→open
    200_000,           # 6→7  open→kelp
    620_000,           # 7→8  kelp→storm
    1_900_000,         # 8→9  storm→frozen
    5_800_000,         # 9→10 frozen→twilight
    17_700_000,        # 10→11 twilight→abyss
    52_800_000,        # 11→12 abyss→garden
    157_700_000,       # 12→13 garden→glass_current
    467_400_000,       # 13→14 glass_current→ember_vent
    1_364_100_000,     # 14→15 ember_vent→starfall_rift
    3_990_100_000,     # 15→16 starfall_rift→moon_bloom
    11_685_100_000,    # 16→17 moon_bloom→clockwork_tide
    33_880_000_000,    # 17→18 clockwork_tide→dreamwhale_expanse
    98_800_000_000,    # 18→19 dreamwhale_expanse→astral_tide
    287_000_100_000,   # 19→20 astral_tide→echoing_orbit
]

# Charter species per zone (non-boss, non-legendary/mythic)
CHARTER_SPECIES = {
    "pond":               ["pond_0","pond_1","pond_2","pond_3","pond_4","pond_5","pond_6","pond_7","pond_8"],  # 9
    "lake":               ["lake_0","lake_1","lake_2","lake_3","lake_4","lake_5","lake_6","lake_8"],  # 8
    "river":              ["river_0","river_1","river_2","river_3","river_4","river_5","river_6","river_8"],  # 8
    "marsh":              ["marsh_0","marsh_1","marsh_2","marsh_3","marsh_4","marsh_5","marsh_6","marsh_8"],  # 8
    "pier":               ["pier_0","pier_1","pier_2","pier_3","pier_4","pier_5","pier_6","pier_7","pier_8"],  # 9
    "reef":               ["reef_0","reef_1","reef_2","reef_3","reef_4","reef_5","reef_6","reef_8"],  # 8
    "open":               ["open_0","open_1","open_2","open_3","open_4","open_5","open_9"],  # 7
    "kelp":               ["kelp_0","kelp_1","kelp_2","kelp_3","kelp_4","kelp_5","kelp_6"],  # 7
    "storm":              ["storm_0","storm_1","storm_2","storm_3","storm_4","storm_5"],  # 6
    "frozen":             ["frozen_0","frozen_1","frozen_2","frozen_3","frozen_4","frozen_5","frozen_6","frozen_9"],  # 8
    "twilight":           ["twilight_0","twilight_1","twilight_2","twilight_3","twilight_4","twilight_5"],  # 6
    "abyss":              ["abyss_0","abyss_1","abyss_2","abyss_3","abyss_4","abyss_5"],  # 6
    "garden":             ["garden_0","garden_1","garden_2","garden_3","garden_4","garden_5","garden_6","garden_9"],  # 8
    "glass_current":      ["glass_current_0","glass_current_1","glass_current_2","glass_current_3","glass_current_4","glass_current_5","glass_current_6","glass_current_9","glass_current_10"],  # 9
    "ember_vent":         ["ember_vent_0","ember_vent_1","ember_vent_2","ember_vent_3","ember_vent_4","ember_vent_5","ember_vent_6","ember_vent_9","ember_vent_11"],  # 9
    "starfall_rift":      ["starfall_rift_0","starfall_rift_1","starfall_rift_2","starfall_rift_3","starfall_rift_4","starfall_rift_5","starfall_rift_6","starfall_rift_9"],  # 8
    "moon_bloom":         ["moon_bloom_0","moon_bloom_1","moon_bloom_2","moon_bloom_3","moon_bloom_4","moon_bloom_5","moon_bloom_6","moon_bloom_9"],  # 8
    "clockwork_tide":     ["clockwork_tide_0","clockwork_tide_1","clockwork_tide_2","clockwork_tide_3","clockwork_tide_4","clockwork_tide_5","clockwork_tide_6","clockwork_tide_9"],  # 8
    "dreamwhale_expanse": ["dreamwhale_expanse_0","dreamwhale_expanse_1","dreamwhale_expanse_2","dreamwhale_expanse_3","dreamwhale_expanse_4","dreamwhale_expanse_5","dreamwhale_expanse_6","dreamwhale_expanse_9"],  # 8
    "astral_tide":        ["astral_tide_0","astral_tide_1","astral_tide_2","astral_tide_3","astral_tide_4","astral_tide_5","astral_tide_6","astral_tide_7","astral_tide_8"],  # 9
    "echoing_orbit":      ["echoing_orbit_0","echoing_orbit_1","echoing_orbit_2","echoing_orbit_3","echoing_orbit_4","echoing_orbit_5","echoing_orbit_6","echoing_orbit_7","echoing_orbit_8","echoing_orbit_41","echoing_orbit_42","echoing_orbit_43"],  # 12
}


# ===========================
# REBIRTH / PRESTIGE FORMULAS (dari index-DeWwtqLH.js)
# ===========================
def threshold_for_rebirth(prestige_count):
    """
    Hitung minimum lifetime coins untuk rebirth berikutnya.
    Formula: 1_000_000 * 1.14^min(count,20) * 1.06^max(0, count-20)
    """
    count = max(0, int(prestige_count or 0))
    threshold = 1_000_000 * (1.14 ** min(count, 20)) * (1.06 ** max(0, count - 20))
    return math.ceil(threshold)


def can_rebirth(state):
    """Cek apakah syarat rebirth terpenuhi."""
    lifetime_coins = state.get("lifetimeCoins", 0)
    prestige_count = state.get("prestigeCount", 0)
    return lifetime_coins >= threshold_for_rebirth(prestige_count)


def multiplier_from_tokens(tokens):
    """Hitung permanent multiplier dari total prestige tokens."""
    t = max(0, int(tokens or 0))
    return 1 + 0.08 * math.log1p(t * 1.8) + 0.02 * math.sqrt(t)


def get_total_tokens(state):
    """Total lifetime tokens."""
    return max(
        int(state.get("prestigeLifetimeTokens", 0)),
        int(state.get("prestigeTokens", 0))
    )


def print_rebirth_status(state):
    """Print status rebirth lengkap."""
    prestige_count = state.get("prestigeCount", 0)
    lifetime_coins = state.get("lifetimeCoins", 0)
    coins          = state.get("coins", 0)
    threshold      = threshold_for_rebirth(prestige_count)
    current_tokens = get_total_tokens(state)
    current_mult   = multiplier_from_tokens(current_tokens)
    next_mult      = multiplier_from_tokens(current_tokens + 1)
    progress       = min(100, (lifetime_coins / threshold) * 100) if threshold > 0 else 0
    ready          = "YES ✓" if lifetime_coins >= threshold else "NO"

    bar_len = 30
    filled  = int(bar_len * progress / 100)
    bar     = "█" * filled + "░" * (bar_len - filled)

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
# LOAD UPGRADE CONFIG
# ===========================
def load_upgrade_config():
    config = {}
    try:
        with open("upgrades.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                if len(parts) != 3:
                    continue
                uid, max_level, enabled = parts
                config[uid.strip()] = {
                    "max_level": int(max_level.strip()),
                    "enabled":   enabled.strip().lower() == "true"
                }
    except FileNotFoundError:
        pass
    return config


# ===========================
# HITUNG HARGA UPGRADE
# ===========================
def calc_upgrade_cost(upgrade_id, current_level):
    data = UPGRADE_DATA.get(upgrade_id)
    if not data:
        return None
    return data["baseCost"] * (data["costMul"] ** current_level)


# ===========================
# CEK STATUS CHARTER
# ===========================
def get_charter_status(state):
    current_line  = state.get("upgrades", {}).get("line", 0)
    charter_dex   = state.get("charterDex", {})
    coins         = state.get("coins", 0)
    current_zone  = state.get("zoneId", "pond")

    current_idx = current_line
    next_idx    = current_idx + 1

    if next_idx >= len(ZONE_ORDER):
        return {"maxed": True, "can_charter": False}

    source_zone = ZONE_ORDER[current_idx]
    target_zone = ZONE_ORDER[next_idx]

    required    = CHARTER_SPECIES.get(source_zone, [])
    caught      = sum(1 for s in required if s in charter_dex)
    target      = len(required)
    survey_done = caught >= target

    charter_fee = CHARTER_FEES[current_idx] if current_idx < len(CHARTER_FEES) else float("inf")
    has_coins   = coins >= charter_fee
    can_charter = survey_done and has_coins

    return {
        "maxed":        False,
        "current_zone": current_zone,
        "current_line": current_line,
        "source_zone":  source_zone,
        "target_zone":  target_zone,
        "caught":       caught,
        "target":       target,
        "survey_done":  survey_done,
        "charter_fee":  charter_fee,
        "has_coins":    has_coins,
        "coins":        coins,
        "can_charter":  can_charter,
    }


# ===========================
# PRINT STATUS CHARTER
# ===========================
def print_charter_status(state):
    cs = get_charter_status(state)
    print("\n========== STATUS CHARTER ==========")
    if cs.get("maxed"):
        print("Semua zone sudah di-unlock!")
        print("=" * 38)
        return cs

    sv = "✓" if cs["survey_done"] else "✗"
    co = "✓" if cs["has_coins"]   else "✗"
    print(f"Zone aktif    : {cs['current_zone']}")
    print(f"Target charter: {cs['target_zone']}")
    print(f"Survey        : {cs['caught']}/{cs['target']} species [{sv}]")
    print(f"Charter fee   : {cs['charter_fee']:,.0f}")
    print(f"Coins         : {cs['coins']:,.0f} [{co}]")

    if cs["can_charter"]:
        print(f"\n[INFO] Siap charter ke {cs['target_zone']}!")
    elif not cs["survey_done"]:
        print(f"\n[INFO] Perlu {cs['target'] - cs['caught']} species lagi di {cs['source_zone']}")
    else:
        kurang = cs["charter_fee"] - cs["coins"]
        print(f"\n[INFO] Coin kurang {kurang:,.0f} untuk charter")
    print("=" * 38)
    return cs


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
        print(f"[REFRESH TOKEN] Status Code: {response.status_code}")

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
            print("[REFRESH TOKEN] Gagal!")
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

    if response.status_code == 401:
        print("Bearer kadaluarsa → refresh token...")
        new_token = refresh_access_token()
        if new_token:
            print("Token berhasil diperbarui, retry...")
            response = requests.post(GAME_URL, headers=make_headers(), json=payload)
            print(f"[{action_type.upper()} RETRY] Status Code: {response.status_code}")
        else:
            print("Gagal refresh token, berhenti...")
            return {"retry": False, "repair": False, "revision": revision_value,
                    "success": False, "coins": 0, "upgrades": {}, "state": {}}

    try:
        data     = response.json()
        state    = data.get("state", {})
        user     = state.get("user", {})
        coins    = state.get("coins", 0)
        gems     = state.get("gems", 0)
        upgrades = state.get("upgrades", {})

        latest_revision = data.get("revision", state.get("revision", revision_value))

        print(f"Nama      : {user.get('name', 'Unknown')}")
        print(f"Coins     : {coins:,.0f}")
        print(f"Gems      : {gems}")
        print(f"Revision  : {latest_revision}")

        if response.status_code == 409:
            print("Cloud save berubah, retry...")
            return {"retry": True, "repair": False, "revision": latest_revision,
                    "success": False, "coins": coins, "upgrades": upgrades, "state": state}

        if response.status_code == 400:
            print("Hook rusak → repairHook")
            return {"retry": False, "repair": True, "revision": latest_revision,
                    "success": False, "coins": coins, "upgrades": upgrades, "state": state}

        return {"retry": False, "repair": False, "revision": latest_revision,
                "success": response.status_code == 200,
                "coins": coins, "upgrades": upgrades, "state": state}

    except Exception as e:
        print("Gagal membaca response JSON:", e)
        print(response.text)
        return {"retry": False, "repair": False, "revision": revision_value,
                "success": False, "coins": 0, "upgrades": {}, "state": {}}


# ===========================
# REPAIR HOOK
# ===========================
def repair_hook_with_fallback(revision_value):
    print("Mencoba cleanHook...")
    clean_result   = send_action("cleanHook", {"score": 1}, revision_value)
    revision_value = clean_result["revision"]
    print("cleanHook selesai")

    print("Mencoba repairHook...")
    repair_result  = send_action("repairHook", {}, revision_value)
    revision_value = repair_result["revision"]

    if repair_result.get("repair"):
        print("repairHook masih 400, lanjut...")

    return revision_value


# ===========================
# AUTO UPGRADE
# ===========================
def run_auto_upgrade(coins, current_upgrades, revision, state=None):
    config = load_upgrade_config()
    if not config:
        return revision, coins, current_upgrades

    # Kalau survey selesai tapi coin belum cukup charter → skip upgrade
    if state is not None:
        cs = get_charter_status(state)
        if not cs.get("maxed") and cs["survey_done"] and not cs["has_coins"]:
            kurang = cs["charter_fee"] - coins
            print(f"\n[UPGRADE] Survey {cs['source_zone']} selesai, fokus kumpul coin untuk charter.")
            print(f"[UPGRADE] Butuh {kurang:,.0f} lagi → skip semua upgrade.")
            return revision, coins, current_upgrades

    # Build list dan sort dari termurah
    queue = []
    for uid, cfg in config.items():
        if not cfg["enabled"]:
            continue
        current_level = current_upgrades.get(uid, 0)
        max_level     = cfg["max_level"]
        if current_level >= max_level:
            continue
        cost = calc_upgrade_cost(uid, current_level)
        if cost is None:
            continue
        queue.append((uid, cfg, cost))

    queue.sort(key=lambda x: x[2])

    if not queue:
        return revision, coins, current_upgrades

    print("\n--- AUTO UPGRADE ---")
    for uid, cfg, _ in queue:
        current_level = current_upgrades.get(uid, 0)
        max_level     = cfg["max_level"]
        if current_level >= max_level:
            continue

        cost = calc_upgrade_cost(uid, current_level)
        if cost is None:
            continue

        if coins < cost:
            print(f"[UPGRADE] {uid} lv{current_level}→{current_level+1} butuh {cost:,.0f}, skip")
            continue

        print(f"[UPGRADE] {uid} lv{current_level}→{current_level+1} | cost: {cost:,.0f} | coins: {coins:,.0f}")

        while True:
            result   = send_action("buyUpgrade", {"id": uid, "count": 1}, revision)
            revision = result["revision"]

            if result.get("retry"):
                time.sleep(1)
                continue
            if result.get("repair"):
                revision = repair_hook_with_fallback(revision)
                time.sleep(5)
                continue
            if result.get("success"):
                coins           = result["coins"]
                current_upgrades = result["upgrades"]
                print(f"[UPGRADE] {uid} berhasil! Coins sisa: {coins:,.0f}")
            else:
                print(f"[UPGRADE] {uid} gagal, skip")
            break

    print("--- UPGRADE SELESAI ---")
    return revision, coins, current_upgrades


# ===========================
# AUTO CHARTER
# ===========================
def run_auto_charter(state, revision):
    cs = get_charter_status(state)
    if cs.get("maxed") or not cs["can_charter"]:
        return revision, state

    print(f"\n[CHARTER] Unlock zone: {cs['target_zone']}...")

    payload = {
        "type": "unlockZone",
        "payload": {"targetZoneId": cs["target_zone"]},
        "revision": revision
    }
    response = requests.post(GAME_URL, headers=make_headers(), json=payload)
    print(f"[UNLOCKZONE] Status Code: {response.status_code}")

    if response.status_code == 401:
        new_token = refresh_access_token()
        if new_token:
            response = requests.post(GAME_URL, headers=make_headers(), json=payload)

    try:
        data = response.json()
        revision = data.get("revision", state.get("revision", revision))

        if response.status_code != 200:
            err = data.get("error", "Unknown error")
            print(f"[CHARTER] Gagal unlock: {err}")
            return revision, state

        print(f"[CHARTER] unlockZone berhasil!")
    except Exception as e:
        print(f"[CHARTER] Error parse response: {e}")
        return revision, state

    print(f"[CHARTER] Travel ke: {cs['target_zone']}...")

    payload2 = {
        "type": "travel",
        "payload": {"zoneId": cs["target_zone"]},
        "revision": revision
    }
    response2 = requests.post(GAME_URL, headers=make_headers(), json=payload2)
    print(f"[TRAVEL] Status Code: {response2.status_code}")

    if response2.status_code == 401:
        new_token = refresh_access_token()
        if new_token:
            response2 = requests.post(GAME_URL, headers=make_headers(), json=payload2)

    try:
        data2    = response2.json()
        revision = data2.get("revision", revision)

        if response2.status_code == 200:
            state = data2.get("state", state)
            print(f"[CHARTER] Berhasil pindah ke: {state.get('zoneId', cs['target_zone'])}")
        else:
            err = data2.get("error", "Unknown error")
            print(f"[CHARTER] Gagal travel: {err}")
    except Exception as e:
        print(f"[CHARTER] Error parse travel response: {e}")

    return revision, state


# ===========================
# AUTO REBIRTH (PRESTIGE)
# ===========================
def run_auto_rebirth(state, revision, rebirth_session_count=0):
    """
    Cek dan lakukan rebirth jika syarat terpenuhi.
    Returns: (revision, state, rebirth_session_count, did_rebirth)
    """
    if not AUTO_REBIRTH_ENABLED:
        return revision, state, rebirth_session_count, False

    if AUTO_REBIRTH_MAX > 0 and rebirth_session_count >= AUTO_REBIRTH_MAX:
        return revision, state, rebirth_session_count, False

    if not can_rebirth(state):
        return revision, state, rebirth_session_count, False

    prestige_count = state.get("prestigeCount", 0)
    lifetime_coins = state.get("lifetimeCoins", 0)
    threshold      = threshold_for_rebirth(prestige_count)
    current_tokens = get_total_tokens(state)
    new_mult       = multiplier_from_tokens(current_tokens + 1)

    print("\n" + "★" * 55)
    print("  ★★★ REBIRTH READY! ★★★")
    print("★" * 55)
    print(f"  Prestige Count  : {prestige_count}")
    print(f"  Lifetime Coins  : {lifetime_coins:,.0f}")
    print(f"  Threshold       : {threshold:,.0f}")
    print(f"  Current Tokens  : {current_tokens}")
    print(f"  New Multiplier  : x{new_mult:.4f}")
    print("★" * 55)

    # Kirim action "prestige"
    print("\n[REBIRTH] Mengirim action prestige...")
    while True:
        result   = send_action("prestige", {}, revision)
        revision = result["revision"]

        if result.get("retry"):
            time.sleep(1)
            continue
        if result.get("repair"):
            revision = repair_hook_with_fallback(revision)
            time.sleep(3)
            continue

        if result.get("success"):
            state = result.get("state", state)
            new_count  = state.get("prestigeCount", prestige_count + 1)
            new_tokens = get_total_tokens(state)
            rebirth_session_count += 1

            print(f"\n[REBIRTH] ✓ BERHASIL! Prestige #{new_count}")
            print(f"[REBIRTH] Total Tokens: {new_tokens}")
            print(f"[REBIRTH] Multiplier: x{multiplier_from_tokens(new_tokens):.4f}")
            print(f"[REBIRTH] Session rebirth count: {rebirth_session_count}")

            # Setelah rebirth, auto upgrade lagi dari awal
            time.sleep(3)
            coins            = state.get("coins", 0)
            current_upgrades = state.get("upgrades", {})
            revision, coins, current_upgrades = run_auto_upgrade(
                coins, current_upgrades, revision, state
            )
            # Update state
            state["coins"]    = coins
            state["upgrades"] = current_upgrades

            return revision, state, rebirth_session_count, True
        else:
            print("[REBIRTH] ✗ Gagal! Mungkin syarat belum terpenuhi di server.")
            return revision, state, rebirth_session_count, False


# ==================================
# FUNGSI PRINT STATUS
# ==================================
def print_upgrade_status(coins, current_upgrades):
    config = load_upgrade_config()
    if not config:
        return
    print("\n========== STATUS UPGRADE ==========")
    print(f"{'ID':<20} {'LV':>4} {'MAX':>4} {'HARGA UPGRADE':>18} {'STATUS':>6}")
    print("-" * 58)
    status_list = []
    for uid, cfg in config.items():
        if not cfg["enabled"]:
            continue
        lv   = current_upgrades.get(uid, 0)
        ml   = cfg["max_level"]
        cost = calc_upgrade_cost(uid, lv)
        if cost is None:
            continue
        status_list.append((uid, lv, ml, cost))
    status_list.sort(key=lambda x: x[3])
    for uid, lv, ml, cost in status_list:
        if lv >= ml:
            status = "MAX"
        elif coins >= cost:
            status = "OK"
        else:
            status = "-"
        print(f"{uid:<20} {lv:>4} {ml:>4} {cost:>18,.0f} {status:>6}")
    print(f"\nCoins : {coins:,.0f}")
    print("=" * 58)


# ==================================
# LOOP SELAMANYA
# ==================================
revision = 271

# =========================
# INISIALISASI AWAL
# =========================
print("\n=== INISIALISASI ===")
while True:
    result   = send_action("sell", {}, revision)
    revision = result["revision"]

    if result.get("retry"):
        time.sleep(1)
        continue
    if result.get("repair"):
        revision = repair_hook_with_fallback(revision)
        time.sleep(5)
        continue
    if result.get("success"):
        print("\nSELL berhasil")
        coins            = result["coins"]
        current_upgrades = result["upgrades"]
        state            = result["state"]
        break

    print("SELL gagal")
    time.sleep(3)

print_upgrade_status(coins, current_upgrades)
print_charter_status(state)
print_rebirth_status(state)
revision, state = run_auto_charter(state, revision)
revision, coins, current_upgrades = run_auto_upgrade(coins, current_upgrades, revision, state)
rebirth_session_count = 0
print("\n=== MULAI LOOP ===\n")

while True:

    # =========================
    # STEP 1 - CAST 10x
    # =========================
    for i in range(10):
        while True:
            result   = send_action("cast", {"fightGrade": "perfect", "auto": False}, revision)
            revision = result["revision"]

            if result.get("retry"):
                time.sleep(1)
                continue
            if result.get("repair"):
                revision = repair_hook_with_fallback(revision)
                print("Menunggu 5 detik sebelum lanjut...")
                time.sleep(5)
                continue
            if result.get("success"):
                print(f"Cast ke-{i+1} berhasil")
                break

            print(f"Cast ke-{i+1} gagal")
            break

    # =========================
    # STEP 2 - SELL
    # =========================
    while True:
        result   = send_action("sell", {}, revision)
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
            coins            = result["coins"]
            current_upgrades = result["upgrades"]
            state            = result["state"]
            break

        print("SELL gagal")
        time.sleep(3)

    print_upgrade_status(coins, current_upgrades)

    # =========================
    # PRINT STATUS CHARTER
    # =========================
    print_charter_status(state)

    # =========================
    # STEP 3 - AUTO CHARTER
    # =========================
    revision, state = run_auto_charter(state, revision)

    # =========================
    # STEP 4 - AUTO UPGRADE
    # =========================
    revision, coins, current_upgrades = run_auto_upgrade(coins, current_upgrades, revision, state)

    # =========================
    # STEP 5 - AUTO REBIRTH
    # =========================
    print_rebirth_status(state)
    revision, state, rebirth_session_count, did_rebirth = run_auto_rebirth(
        state, revision, rebirth_session_count
    )
    if did_rebirth:
        # Setelah rebirth, state sudah reset, langsung ulang dari cast
        coins            = state.get("coins", 0)
        current_upgrades = state.get("upgrades", {})
        print("\n=== POST-REBIRTH: Mulai ulang dari CAST ===\n")
        continue

    print("\n=== Mengulang ke CAST ===\n")