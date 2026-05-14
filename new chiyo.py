import requests
import time
import json
import math
import threading
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

# ===========================
# KONSTANTA
# ===========================
SUPABASE_URL    = "https://qsoptshiorjhoiwwrumb.supabase.co/auth/v1/token"
SUPABASE_APIKEY = "sb_publishable_OtJtVXVlBl7_JPubRQg6rA_5uyAGLqP"
GAME_URL        = "https://fishin-chiyo.vercel.app/api/game/action"

# ===========================
# KONFIGURASI AUTO REBIRTH
# ===========================
AUTO_REBIRTH_ENABLED = True
AUTO_REBIRTH_MAX     = 0

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

ZONE_ORDER = [
    "pond","lake","river","marsh","pier","reef","open","kelp","storm","frozen",
    "twilight","abyss","garden","glass_current","ember_vent","starfall_rift",
    "moon_bloom","clockwork_tide","dreamwhale_expanse","astral_tide","echoing_orbit",
]

CHARTER_FEES = [
    125, 450, 1_700, 5_500, 19_000, 62_000, 200_000, 620_000, 1_900_000,
    5_800_000, 17_700_000, 52_800_000, 157_700_000, 467_400_000, 1_364_100_000,
    3_990_100_000, 11_685_100_000, 33_880_000_000, 98_800_000_000, 287_000_100_000,
]

CHARTER_SPECIES = {
    "pond":               ["pond_0","pond_1","pond_2","pond_3","pond_4","pond_5","pond_6","pond_7","pond_8"],
    "lake":               ["lake_0","lake_1","lake_2","lake_3","lake_4","lake_5","lake_6","lake_8"],
    "river":              ["river_0","river_1","river_2","river_3","river_4","river_5","river_6","river_8"],
    "marsh":              ["marsh_0","marsh_1","marsh_2","marsh_3","marsh_4","marsh_5","marsh_6","marsh_8"],
    "pier":               ["pier_0","pier_1","pier_2","pier_3","pier_4","pier_5","pier_6","pier_7","pier_8"],
    "reef":               ["reef_0","reef_1","reef_2","reef_3","reef_4","reef_5","reef_6","reef_8"],
    "open":               ["open_0","open_1","open_2","open_3","open_4","open_5","open_9"],
    "kelp":               ["kelp_0","kelp_1","kelp_2","kelp_3","kelp_4","kelp_5","kelp_6"],
    "storm":              ["storm_0","storm_1","storm_2","storm_3","storm_4","storm_5"],
    "frozen":             ["frozen_0","frozen_1","frozen_2","frozen_3","frozen_4","frozen_5","frozen_6","frozen_9"],
    "twilight":           ["twilight_0","twilight_1","twilight_2","twilight_3","twilight_4","twilight_5"],
    "abyss":              ["abyss_0","abyss_1","abyss_2","abyss_3","abyss_4","abyss_5"],
    "garden":             ["garden_0","garden_1","garden_2","garden_3","garden_4","garden_5","garden_6","garden_9"],
    "glass_current":      ["glass_current_0","glass_current_1","glass_current_2","glass_current_3","glass_current_4","glass_current_5","glass_current_6","glass_current_9","glass_current_10"],
    "ember_vent":         ["ember_vent_0","ember_vent_1","ember_vent_2","ember_vent_3","ember_vent_4","ember_vent_5","ember_vent_6","ember_vent_9","ember_vent_11"],
    "starfall_rift":      ["starfall_rift_0","starfall_rift_1","starfall_rift_2","starfall_rift_3","starfall_rift_4","starfall_rift_5","starfall_rift_6","starfall_rift_9"],
    "moon_bloom":         ["moon_bloom_0","moon_bloom_1","moon_bloom_2","moon_bloom_3","moon_bloom_4","moon_bloom_5","moon_bloom_6","moon_bloom_9"],
    "clockwork_tide":     ["clockwork_tide_0","clockwork_tide_1","clockwork_tide_2","clockwork_tide_3","clockwork_tide_4","clockwork_tide_5","clockwork_tide_6","clockwork_tide_9"],
    "dreamwhale_expanse": ["dreamwhale_expanse_0","dreamwhale_expanse_1","dreamwhale_expanse_2","dreamwhale_expanse_3","dreamwhale_expanse_4","dreamwhale_expanse_5","dreamwhale_expanse_6","dreamwhale_expanse_9"],
    "astral_tide":        ["astral_tide_0","astral_tide_1","astral_tide_2","astral_tide_3","astral_tide_4","astral_tide_5","astral_tide_6","astral_tide_7","astral_tide_8"],
    "echoing_orbit":      ["echoing_orbit_0","echoing_orbit_1","echoing_orbit_2","echoing_orbit_3","echoing_orbit_4","echoing_orbit_5","echoing_orbit_6","echoing_orbit_7","echoing_orbit_8","echoing_orbit_41","echoing_orbit_42","echoing_orbit_43"],
}

# ===========================
# GUI STATE
# ===========================
gui_state = {
    "running": False,
    "paused": False,
    "logs": [],
    "stats": {
        "coins": 0,
        "gems": 0,
        "loop_count": 0,
        "cast_count": 0,
        "sell_count": 0,
        "rebirth_count": 0,
        "charter_count": 0,
        "current_zone": "pond",
        "best_zone": "pond",
        "prestige_count": 0,
        "lifetime_coins": 0,
        "rebirth_progress": 0,
        "rebirth_threshold": 0,
        "current_tokens": 0,
        "current_multiplier": 1.0,
        "upgrades": {},
        "username": "",
        "start_time": None,
        "last_travel_loop": 0,
    },
    "config": {
        "auto_rebirth": True,
        "auto_charter": True,
        "auto_upgrade": True,
        "auto_travel": True,
        "travel_interval": 10,
        "cast_per_loop": 10,
        "revision": 271,
    },
    "upgrade_config": {},
}

bot_thread = None
stop_event = threading.Event()

def add_log(msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    gui_state["logs"].append({"time": ts, "msg": msg, "level": level})
    if len(gui_state["logs"]) > 300:
        gui_state["logs"] = gui_state["logs"][-300:]
    print(f"[{ts}] {msg}")

# ===========================
# REBIRTH FORMULAS
# ===========================
def threshold_for_rebirth(prestige_count):
    count = max(0, int(prestige_count or 0))
    threshold = 1_000_000 * (1.14 ** min(count, 20)) * (1.06 ** max(0, count - 20))
    return math.ceil(threshold)

def can_rebirth(state):
    return state.get("lifetimeCoins", 0) >= threshold_for_rebirth(state.get("prestigeCount", 0))

def multiplier_from_tokens(tokens):
    t = max(0, int(tokens or 0))
    return 1 + 0.08 * math.log1p(t * 1.8) + 0.02 * math.sqrt(t)

def get_total_tokens(state):
    return max(int(state.get("prestigeLifetimeTokens", 0)), int(state.get("prestigeTokens", 0)))

# ===========================
# TOKEN MANAGEMENT
# ===========================
def load_bearer():
    try:
        with open("bearer.txt", "r") as f:
            return f.read().strip()
    except:
        return ""

def load_refresh_token():
    try:
        with open("refresh_token.txt", "r") as f:
            return f.read().strip()
    except:
        return ""

def save_bearer(token):
    with open("bearer.txt", "w") as f:
        f.write(token)

def save_refresh_token(token):
    with open("refresh_token.txt", "w") as f:
        f.write(token)

def load_upgrade_config():
    config = {}
    try:
        with open("upgrades.txt", "r") as f:
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
                    "enabled": enabled.strip().lower() == "true"
                }
    except FileNotFoundError:
        pass
    return config

def calc_upgrade_cost(upgrade_id, current_level):
    data = UPGRADE_DATA.get(upgrade_id)
    if not data:
        return None
    return data["baseCost"] * (data["costMul"] ** current_level)

# ===========================
# CHARTER STATUS
# ===========================
def get_charter_status(state):
    current_line = state.get("upgrades", {}).get("line", 0)
    charter_dex  = state.get("charterDex", {})
    coins        = state.get("coins", 0)
    current_idx  = current_line
    next_idx     = current_idx + 1

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
        "maxed": False, "current_zone": state.get("zoneId","pond"),
        "current_line": current_line, "source_zone": source_zone,
        "target_zone": target_zone, "caught": caught, "target": target,
        "survey_done": survey_done, "charter_fee": charter_fee,
        "has_coins": has_coins, "coins": coins, "can_charter": can_charter,
    }

# ===========================
# REFRESH TOKEN
# ===========================
def refresh_access_token():
    add_log("Bearer expired, refreshing...", "warn")
    refresh_token = load_refresh_token()
    headers = {"Content-Type": "application/json", "apikey": SUPABASE_APIKEY}
    payload = {"refresh_token": refresh_token}
    try:
        response = requests.post(SUPABASE_URL, params={"grant_type": "refresh_token"},
                                  headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            new_access  = data.get("access_token")
            new_refresh = data.get("refresh_token")
            if new_access:
                save_bearer(new_access)
                add_log("Access token refreshed!", "success")
            if new_refresh:
                save_refresh_token(new_refresh)
            return new_access
        else:
            add_log(f"Token refresh failed: {response.status_code}", "error")
            return None
    except Exception as e:
        add_log(f"Token refresh error: {e}", "error")
        return None

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
    payload = {"type": action_type, "payload": payload_data, "revision": revision_value}
    try:
        response = requests.post(GAME_URL, headers=make_headers(), json=payload, timeout=15)
    except Exception as e:
        add_log(f"Network error: {e}", "error")
        return {"retry": False, "repair": False, "revision": revision_value,
                "success": False, "coins": 0, "upgrades": {}, "state": {}}

    if response.status_code == 401:
        add_log("401 - refreshing token...", "warn")
        new_token = refresh_access_token()
        if new_token:
            try:
                response = requests.post(GAME_URL, headers=make_headers(), json=payload, timeout=15)
            except:
                pass
        else:
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

        username = user.get("name", "")
        if username:
            gui_state["stats"]["username"] = username

        gui_state["stats"]["coins"] = coins
        gui_state["stats"]["gems"]  = gems
        gui_state["stats"]["upgrades"] = upgrades

        if state:
            current_line = upgrades.get("line", 0)
            best_idx = min(current_line, len(ZONE_ORDER) - 1)
            gui_state["stats"]["current_zone"] = state.get("zoneId", "pond")
            gui_state["stats"]["best_zone"]    = ZONE_ORDER[best_idx]
            gui_state["stats"]["prestige_count"]   = state.get("prestigeCount", 0)
            gui_state["stats"]["lifetime_coins"]   = state.get("lifetimeCoins", 0)
            tokens = get_total_tokens(state)
            gui_state["stats"]["current_tokens"]     = tokens
            gui_state["stats"]["current_multiplier"] = multiplier_from_tokens(tokens)
            threshold = threshold_for_rebirth(state.get("prestigeCount", 0))
            gui_state["stats"]["rebirth_threshold"] = threshold
            lc = state.get("lifetimeCoins", 0)
            gui_state["stats"]["rebirth_progress"] = min(100, (lc / threshold * 100)) if threshold > 0 else 0

        if response.status_code == 409:
            add_log(f"[{action_type}] 409 conflict - retrying...", "warn")
            return {"retry": True, "repair": False, "revision": latest_revision,
                    "success": False, "coins": coins, "upgrades": upgrades, "state": state}

        if response.status_code == 400:
            add_log(f"[{action_type}] 400 - hook broken, repairing...", "warn")
            return {"retry": False, "repair": True, "revision": latest_revision,
                    "success": False, "coins": coins, "upgrades": upgrades, "state": state}

        return {"retry": False, "repair": False, "revision": latest_revision,
                "success": response.status_code == 200,
                "coins": coins, "upgrades": upgrades, "state": state}
    except Exception as e:
        add_log(f"Parse error: {e}", "error")
        return {"retry": False, "repair": False, "revision": revision_value,
                "success": False, "coins": 0, "upgrades": {}, "state": {}}

# ===========================
# REPAIR HOOK
# ===========================
def repair_hook_with_fallback(revision_value):
    add_log("Cleaning hook...", "warn")
    r1 = send_action("cleanHook", {"score": 1}, revision_value)
    revision_value = r1["revision"]
    add_log("Repairing hook...", "warn")
    r2 = send_action("repairHook", {}, revision_value)
    return r2["revision"]

# ===========================
# AUTO UPGRADE
# ===========================
def run_auto_upgrade(coins, current_upgrades, revision, state=None):
    if not gui_state["config"]["auto_upgrade"]:
        return revision, coins, current_upgrades

    config = load_upgrade_config()
    if not config:
        return revision, coins, current_upgrades

    if state is not None:
        cs = get_charter_status(state)
        if not cs.get("maxed") and cs["survey_done"] and not cs["has_coins"]:
            add_log(f"Survey done, saving coins for charter ({cs['charter_fee']:,.0f})", "info")
            return revision, coins, current_upgrades

    queue = []
    for uid, cfg in config.items():
        if not cfg["enabled"]:
            continue
        current_level = current_upgrades.get(uid, 0)
        if current_level >= cfg["max_level"]:
            continue
        cost = calc_upgrade_cost(uid, current_level)
        if cost is None:
            continue
        queue.append((uid, cfg, cost))

    queue.sort(key=lambda x: x[2])

    for uid, cfg, _ in queue:
        if stop_event.is_set():
            break
        while gui_state["paused"] and not stop_event.is_set():
            time.sleep(0.5)

        current_level = current_upgrades.get(uid, 0)
        if current_level >= cfg["max_level"]:
            continue
        cost = calc_upgrade_cost(uid, current_level)
        if cost is None or coins < cost:
            continue

        add_log(f"Upgrading {uid} lv{current_level}→{current_level+1} (cost: {cost:,.0f})", "info")
        while True:
            result   = send_action("buyUpgrade", {"id": uid, "count": 1}, revision)
            revision = result["revision"]
            if result.get("retry"):
                time.sleep(1)
                continue
            if result.get("repair"):
                revision = repair_hook_with_fallback(revision)
                time.sleep(3)
                continue
            if result.get("success"):
                coins = result["coins"]
                current_upgrades = result["upgrades"]
                add_log(f"{uid} upgraded! Coins: {coins:,.0f}", "success")
            break

    return revision, coins, current_upgrades

# ===========================
# AUTO TRAVEL
# ===========================
def travel_to_best_zone(state, revision):
    if not gui_state["config"]["auto_travel"]:
        return revision, state

    current_line = state.get("upgrades", {}).get("line", 0)
    current_zone = state.get("zoneId", "pond")
    best_idx     = min(current_line, len(ZONE_ORDER) - 1)
    best_zone    = ZONE_ORDER[best_idx]

    if current_zone == best_zone:
        return revision, state

    try:
        current_idx = ZONE_ORDER.index(current_zone)
    except ValueError:
        current_idx = 0

    if current_idx >= best_idx:
        return revision, state

    add_log(f"Traveling: {current_zone} → {best_zone}", "info")
    result   = send_action("travel", {"zoneId": best_zone}, revision)
    revision = result["revision"]

    if result.get("success"):
        state = result.get("state", state)
        add_log(f"Arrived at: {state.get('zoneId', best_zone)}", "success")
    elif result.get("retry"):
        time.sleep(1)
        result   = send_action("travel", {"zoneId": best_zone}, revision)
        revision = result["revision"]
        if result.get("success"):
            state = result.get("state", state)
            add_log(f"Arrived at: {state.get('zoneId', best_zone)}", "success")
        else:
            add_log(f"Travel failed to {best_zone}", "error")
    else:
        add_log(f"Travel failed to {best_zone}", "error")

    return revision, state

# ===========================
# AUTO CHARTER
# ===========================
def run_auto_charter(state, revision):
    if not gui_state["config"]["auto_charter"]:
        return revision, state

    cs = get_charter_status(state)
    if cs.get("maxed") or not cs["can_charter"]:
        return revision, state

    add_log(f"Chartering to {cs['target_zone']}...", "info")
    payload  = {"type": "unlockZone", "payload": {"targetZoneId": cs["target_zone"]}, "revision": revision}
    response = requests.post(GAME_URL, headers=make_headers(), json=payload)

    if response.status_code == 401:
        refresh_access_token()
        response = requests.post(GAME_URL, headers=make_headers(), json=payload)

    try:
        data = response.json()
        revision = data.get("revision", revision)
        if response.status_code != 200:
            add_log(f"Charter failed: {data.get('error','?')}", "error")
            return revision, state
        add_log(f"Zone unlocked: {cs['target_zone']}!", "success")
        gui_state["stats"]["charter_count"] += 1
    except:
        return revision, state

    payload2  = {"type": "travel", "payload": {"zoneId": cs["target_zone"]}, "revision": revision}
    response2 = requests.post(GAME_URL, headers=make_headers(), json=payload2)

    if response2.status_code == 401:
        refresh_access_token()
        response2 = requests.post(GAME_URL, headers=make_headers(), json=payload2)

    try:
        data2    = response2.json()
        revision = data2.get("revision", revision)
        if response2.status_code == 200:
            state = data2.get("state", state)
            add_log(f"Traveled to {state.get('zoneId', cs['target_zone'])}", "success")
    except:
        pass

    return revision, state

# ===========================
# AUTO REBIRTH
# ===========================
def run_auto_rebirth(state, revision, rebirth_session_count=0):
    if not gui_state["config"]["auto_rebirth"]:
        return revision, state, rebirth_session_count, False
    if AUTO_REBIRTH_MAX > 0 and rebirth_session_count >= AUTO_REBIRTH_MAX:
        return revision, state, rebirth_session_count, False
    if not can_rebirth(state):
        return revision, state, rebirth_session_count, False

    add_log("REBIRTH READY! Performing prestige...", "success")

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
            rebirth_session_count += 1
            gui_state["stats"]["rebirth_count"] += 1
            new_tokens = get_total_tokens(state)
            add_log(f"Rebirth #{state.get('prestigeCount','?')} done! Tokens: {new_tokens}, Mult: x{multiplier_from_tokens(new_tokens):.4f}", "success")
            time.sleep(3)
            coins = state.get("coins", 0)
            current_upgrades = state.get("upgrades", {})
            revision, state = travel_to_best_zone(state, revision)
            revision, coins, current_upgrades = run_auto_upgrade(coins, current_upgrades, revision, state)
            state["coins"]    = coins
            state["upgrades"] = current_upgrades
            return revision, state, rebirth_session_count, True
        else:
            add_log("Rebirth failed at server", "error")
            return revision, state, rebirth_session_count, False

# ===========================
# MAIN BOT LOOP
# ===========================
def bot_loop():
    add_log("Bot starting...", "info")
    revision = gui_state["config"]["revision"]
    coins = 0
    current_upgrades = {}
    state = {}
    rebirth_session_count = 0
    loop_count = 0

    # Init
    add_log("Initializing with sell...", "info")
    while not stop_event.is_set():
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
            coins = result["coins"]
            current_upgrades = result["upgrades"]
            state = result["state"]
            add_log(f"Init OK - Coins: {coins:,.0f}", "success")
            break
        time.sleep(3)

    revision, state = run_auto_charter(state, revision)
    revision, state = travel_to_best_zone(state, revision)
    revision, coins, current_upgrades = run_auto_upgrade(coins, current_upgrades, revision, state)

    add_log("=== MAIN LOOP STARTED ===", "info")
    gui_state["stats"]["start_time"] = datetime.now().isoformat()

    while not stop_event.is_set():
        while gui_state["paused"] and not stop_event.is_set():
            time.sleep(0.5)
        if stop_event.is_set():
            break

        loop_count += 1
        gui_state["stats"]["loop_count"] = loop_count
        add_log(f"--- Loop #{loop_count} ---", "info")

        cast_count = gui_state["config"]["cast_per_loop"]
        for i in range(cast_count):
            if stop_event.is_set():
                break
            while gui_state["paused"] and not stop_event.is_set():
                time.sleep(0.5)

            while True:
                result   = send_action("cast", {"fightGrade": "perfect", "auto": False}, revision)
                revision = result["revision"]
                if result.get("retry"):
                    time.sleep(1)
                    continue
                if result.get("repair"):
                    revision = repair_hook_with_fallback(revision)
                    time.sleep(5)
                    continue
                if result.get("success"):
                    gui_state["stats"]["cast_count"] += 1
                    add_log(f"Cast {i+1}/{cast_count} ok", "info")
                    break
                add_log(f"Cast {i+1} failed", "warn")
                break

        if stop_event.is_set():
            break

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
                coins = result["coins"]
                current_upgrades = result["upgrades"]
                state = result["state"]
                gui_state["stats"]["sell_count"] += 1
                add_log(f"Sell ok - Coins: {coins:,.0f}", "success")
                break
            time.sleep(3)

        revision, state = run_auto_charter(state, revision)

        # Auto travel setiap 10 loop
        travel_interval = gui_state["config"]["travel_interval"]
        if loop_count % travel_interval == 0:
            add_log(f"[Loop {loop_count}] Auto travel check (every {travel_interval} loops)", "info")
            revision, state = travel_to_best_zone(state, revision)
            gui_state["stats"]["last_travel_loop"] = loop_count

        revision, coins, current_upgrades = run_auto_upgrade(coins, current_upgrades, revision, state)

        revision, state, rebirth_session_count, did_rebirth = run_auto_rebirth(
            state, revision, rebirth_session_count
        )
        if did_rebirth:
            coins = state.get("coins", 0)
            current_upgrades = state.get("upgrades", {})
            add_log("Post-rebirth: restarting loop", "success")
            continue

    add_log("Bot stopped.", "warn")
    gui_state["running"] = False

# ===========================
# HTTP SERVER (GUI)
# ===========================
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fishin' Chiyo Bot</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;800&display=swap');

  :root {
    --bg: #0a0e1a;
    --bg2: #111827;
    --bg3: #1c2539;
    --border: #2a3a5c;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --green: #10b981;
    --yellow: #f59e0b;
    --red: #ef4444;
    --text: #e2e8f0;
    --text2: #94a3b8;
    --mono: 'JetBrains Mono', monospace;
    --display: 'Syne', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--mono);
    font-size: 13px;
    min-height: 100vh;
  }

  .header {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .header h1 {
    font-family: var(--display);
    font-size: 20px;
    font-weight: 800;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
  }

  .status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    background: var(--red);
  }
  .status-dot.running { background: var(--green); animation: pulse 1.5s infinite; }
  .status-dot.paused  { background: var(--yellow); }

  @keyframes pulse {
    0%,100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .layout {
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 0;
    height: calc(100vh - 57px);
  }

  .sidebar {
    background: var(--bg2);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .main {
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .card {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
  }

  .card-title {
    font-family: var(--display);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--text2);
    margin-bottom: 12px;
  }

  .stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .stat-box {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
  }

  .stat-label {
    font-size: 10px;
    color: var(--text2);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 4px;
  }

  .stat-value {
    font-family: var(--display);
    font-size: 18px;
    font-weight: 800;
    color: var(--accent);
  }

  .stat-value.green { color: var(--green); }
  .stat-value.yellow { color: var(--yellow); }
  .stat-value.purple { color: #a78bfa; }

  .btn {
    width: 100%;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid var(--border);
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    background: var(--bg2);
    color: var(--text);
  }

  .btn:hover { border-color: var(--accent); color: var(--accent); }
  .btn:active { transform: scale(0.98); }

  .btn.start { background: #065f46; border-color: var(--green); color: var(--green); }
  .btn.start:hover { background: #047857; }
  .btn.stop  { background: #7f1d1d; border-color: var(--red); color: var(--red); }
  .btn.stop:hover { background: #991b1b; }
  .btn.pause { background: #78350f; border-color: var(--yellow); color: var(--yellow); }
  .btn.pause:hover { background: #92400e; }

  .toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
  }
  .toggle-row:last-child { border-bottom: none; }

  .toggle-label { color: var(--text2); font-size: 12px; }

  .toggle {
    position: relative;
    width: 36px; height: 20px;
    cursor: pointer;
  }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .toggle-slider {
    position: absolute;
    inset: 0;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    transition: 0.2s;
  }
  .toggle-slider:before {
    content: "";
    position: absolute;
    height: 14px; width: 14px;
    left: 2px; top: 2px;
    background: var(--text2);
    border-radius: 50%;
    transition: 0.2s;
  }
  .toggle input:checked + .toggle-slider { background: #065f46; border-color: var(--green); }
  .toggle input:checked + .toggle-slider:before { transform: translateX(16px); background: var(--green); }

  .input-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 0;
    gap: 8px;
  }
  .input-label { color: var(--text2); font-size: 12px; flex: 1; }
  .input-num {
    width: 70px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 4px 8px;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text);
    text-align: right;
  }
  .input-num:focus { outline: none; border-color: var(--accent); }

  .progress-bar {
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
    margin-top: 6px;
  }
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent2), var(--accent));
    border-radius: 3px;
    transition: width 0.5s ease;
  }
  .progress-fill.rebirth { background: linear-gradient(90deg, #7c3aed, #f59e0b); }

  .zone-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    background: #1e3a5f;
    color: var(--accent);
    border: 1px solid #2a5a8f;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .log-container {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    height: 360px;
    overflow-y: auto;
    padding: 12px;
    font-size: 11px;
    flex: 1;
  }

  .log-container::-webkit-scrollbar { width: 4px; }
  .log-container::-webkit-scrollbar-track { background: var(--bg); }
  .log-container::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  .log-line {
    padding: 2px 0;
    display: flex;
    gap: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
  }
  .log-time { color: #475569; min-width: 60px; }
  .log-msg  { color: var(--text2); }
  .log-msg.info    { color: var(--text2); }
  .log-msg.success { color: var(--green); }
  .log-msg.warn    { color: var(--yellow); }
  .log-msg.error   { color: var(--red); }

  .upgrade-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
  }
  .upgrade-table th {
    text-align: left;
    color: var(--text2);
    padding: 4px 6px;
    border-bottom: 1px solid var(--border);
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }
  .upgrade-table td {
    padding: 4px 6px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
  }
  .upgrade-table tr:last-child td { border-bottom: none; }
  .badge-ok  { color: var(--green); font-weight: 600; }
  .badge-max { color: var(--accent2); font-weight: 600; }
  .badge-no  { color: var(--text2); }

  .btn-group { display: flex; gap: 8px; }
  .btn-group .btn { }

  .token-input {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 7px 10px;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text);
    margin-bottom: 6px;
  }
  .token-input:focus { outline: none; border-color: var(--accent); }
  .token-label { font-size: 11px; color: var(--text2); margin-bottom: 4px; }

  .charter-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 5px 0;
    font-size: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }
  .charter-row:last-child { border-bottom: none; }
  .charter-key { color: var(--text2); }
  .charter-val { color: var(--text); font-weight: 600; }
  .charter-val.ok { color: var(--green); }
  .charter-val.no { color: var(--yellow); }
</style>
</head>
<body>

<div class="header">
  <h1>🎣 Fishin' Chiyo Bot</h1>
  <div style="display:flex; align-items:center; gap: 12px;">
    <span id="user-name" style="color: var(--text2); font-size:12px;"></span>
    <span><span class="status-dot" id="status-dot"></span><span id="status-text" style="font-size:12px;">Stopped</span></span>
  </div>
</div>

<div class="layout">
  <div class="sidebar">

    <div class="card">
      <div class="card-title">Auth Tokens</div>
      <div class="token-label">Bearer Token</div>
      <input class="token-input" id="bearer-input" type="text" placeholder="Paste bearer token...">
      <div class="token-label">Refresh Token</div>
      <input class="token-input" id="refresh-input" type="text" placeholder="Paste refresh token...">
      <button class="btn" onclick="saveTokens()" style="margin-top:4px;">Save Tokens</button>
    </div>

    <div class="card">
      <div class="card-title">Controls</div>
      <div style="display:flex; flex-direction:column; gap:8px;">
        <button class="btn start" id="btn-start" onclick="botControl('start')">▶ Start Bot</button>
        <div class="btn-group">
          <button class="btn pause" id="btn-pause" onclick="botControl('pause')">⏸ Pause</button>
          <button class="btn stop"  id="btn-stop"  onclick="botControl('stop')">⏹ Stop</button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Configuration</div>
      <div class="toggle-row">
        <span class="toggle-label">Auto Rebirth</span>
        <label class="toggle"><input type="checkbox" id="cfg-rebirth" checked onchange="updateConfig()"><span class="toggle-slider"></span></label>
      </div>
      <div class="toggle-row">
        <span class="toggle-label">Auto Charter</span>
        <label class="toggle"><input type="checkbox" id="cfg-charter" checked onchange="updateConfig()"><span class="toggle-slider"></span></label>
      </div>
      <div class="toggle-row">
        <span class="toggle-label">Auto Upgrade</span>
        <label class="toggle"><input type="checkbox" id="cfg-upgrade" checked onchange="updateConfig()"><span class="toggle-slider"></span></label>
      </div>
      <div class="toggle-row">
        <span class="toggle-label">Auto Travel</span>
        <label class="toggle"><input type="checkbox" id="cfg-travel" checked onchange="updateConfig()"><span class="toggle-slider"></span></label>
      </div>
      <div style="margin-top:10px; display:flex; flex-direction:column; gap:2px;">
        <div class="input-row">
          <span class="input-label">Casts/Loop</span>
          <input class="input-num" id="cfg-casts" type="number" value="10" min="1" max="100" onchange="updateConfig()">
        </div>
        <div class="input-row">
          <span class="input-label">Travel Interval (loops)</span>
          <input class="input-num" id="cfg-travel-interval" type="number" value="10" min="1" max="100" onchange="updateConfig()">
        </div>
        <div class="input-row">
          <span class="input-label">Start Revision</span>
          <input class="input-num" id="cfg-revision" type="number" value="271" min="1" onchange="updateConfig()">
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Charter Status</div>
      <div id="charter-status">
        <div style="color:var(--text2); font-size:12px;">Loading...</div>
      </div>
    </div>

  </div>

  <div class="main">

    <div class="stat-grid">
      <div class="stat-box">
        <div class="stat-label">💰 Coins</div>
        <div class="stat-value" id="stat-coins">0</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">💎 Gems</div>
        <div class="stat-value green" id="stat-gems">0</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">🔄 Loops</div>
        <div class="stat-value yellow" id="stat-loops">0</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">🎣 Casts</div>
        <div class="stat-value yellow" id="stat-casts">0</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">⭐ Rebirths</div>
        <div class="stat-value purple" id="stat-rebirths">0</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">🗺️ Charters</div>
        <div class="stat-value purple" id="stat-charters">0</div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Zone Status</div>
      <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
        <div>
          <div style="font-size:10px; color:var(--text2); margin-bottom:4px;">CURRENT</div>
          <span class="zone-badge" id="zone-current">pond</span>
        </div>
        <div style="color:var(--text2);">→</div>
        <div>
          <div style="font-size:10px; color:var(--text2); margin-bottom:4px;">BEST AVAILABLE</div>
          <span class="zone-badge" id="zone-best" style="background:#1a3a1a; color:var(--green); border-color:#2a6a2a;">pond</span>
        </div>
        <div style="margin-left:auto; text-align:right;">
          <div style="font-size:10px; color:var(--text2);">LAST TRAVEL LOOP</div>
          <div style="font-size:14px; color:var(--accent); font-weight:700;" id="stat-travel-loop">-</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Rebirth Progress</div>
      <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
        <div style="font-size:12px; color:var(--text2);">Prestige <span id="prestige-count" style="color:var(--text);">0</span> | Tokens: <span id="token-count" style="color:#a78bfa;">0</span> | Mult: <span id="mult-val" style="color:var(--accent);">x1.0000</span></div>
        <div style="font-size:12px;"><span id="rebirth-pct" style="color:var(--yellow);">0%</span></div>
      </div>
      <div class="progress-bar">
        <div class="progress-fill rebirth" id="rebirth-bar" style="width:0%"></div>
      </div>
      <div style="display:flex; justify-content:space-between; margin-top:5px; font-size:10px; color:var(--text2);">
        <span>Lifetime: <span id="lifetime-coins" style="color:var(--text);">0</span></span>
        <span>Threshold: <span id="rebirth-threshold" style="color:var(--text);">1,000,000</span></span>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Upgrades</div>
      <div style="overflow-x:auto;">
        <table class="upgrade-table" id="upgrade-table">
          <thead>
            <tr>
              <th>ID</th><th>LV</th><th>MAX</th><th>Cost</th><th>Status</th>
            </tr>
          </thead>
          <tbody id="upgrade-body">
            <tr><td colspan="5" style="color:var(--text2); padding:8px 6px;">No upgrades.txt found</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card" style="flex:1;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <div class="card-title" style="margin-bottom:0;">Activity Log</div>
        <button class="btn" style="width:auto; padding:4px 12px; font-size:11px;" onclick="clearLogs()">Clear</button>
      </div>
      <div class="log-container" id="log-box"></div>
    </div>

  </div>
</div>

<script>
let autoScroll = true;
let lastLogCount = 0;

function fmt(n) {
  if (n === undefined || n === null) return '0';
  if (n >= 1e12) return (n/1e12).toFixed(2) + 'T';
  if (n >= 1e9)  return (n/1e9).toFixed(2) + 'B';
  if (n >= 1e6)  return (n/1e6).toFixed(2) + 'M';
  if (n >= 1e3)  return (n/1e3).toFixed(1) + 'K';
  return n.toFixed ? n.toFixed(0) : String(n);
}

function saveTokens() {
  const bearer  = document.getElementById('bearer-input').value.trim();
  const refresh = document.getElementById('refresh-input').value.trim();
  fetch('/api/tokens', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({bearer, refresh})
  }).then(r=>r.json()).then(d=>{
    alert(d.ok ? 'Tokens saved!' : 'Error: ' + d.error);
  });
}

function botControl(action) {
  fetch('/api/control', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({action})
  }).then(r=>r.json()).then(d=>{
    console.log(action, d);
  });
}

function updateConfig() {
  const cfg = {
    auto_rebirth: document.getElementById('cfg-rebirth').checked,
    auto_charter: document.getElementById('cfg-charter').checked,
    auto_upgrade: document.getElementById('cfg-upgrade').checked,
    auto_travel:  document.getElementById('cfg-travel').checked,
    cast_per_loop: parseInt(document.getElementById('cfg-casts').value)||10,
    travel_interval: parseInt(document.getElementById('cfg-travel-interval').value)||10,
    revision: parseInt(document.getElementById('cfg-revision').value)||271,
  };
  fetch('/api/config', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(cfg)
  });
}

function clearLogs() {
  fetch('/api/logs/clear', {method:'POST'});
  document.getElementById('log-box').innerHTML = '';
  lastLogCount = 0;
}

function renderUpgrades(upgrades, coins) {
  if (!upgrades || Object.keys(upgrades).length === 0) return;
  const UPGRADE_DATA = {
    rod:20, reel:90, market_bell:140, bait:120, bobber:160, hook:180,
    reinforced_hook:260, junk_filter:420, tackle_brush:640, repair_kit:800,
    auto_repair_hook:950, tackle_net:1100, weather_vane:2200, dock:180,
    tacklebox:50, crew:600
  };
  const COST_MUL = {
    rod:1.32,reel:1.34,market_bell:1.33,bait:1.30,bobber:1.31,hook:1.30,
    reinforced_hook:1.28,junk_filter:1.27,tackle_brush:1.28,repair_kit:1.29,
    auto_repair_hook:1.28,tackle_net:1.24,weather_vane:1.27,dock:1.36,
    tacklebox:1.20,crew:1.35
  };
  // We show all known upgrades
  const rows = Object.entries(UPGRADE_DATA).map(([uid, base]) => {
    const lv   = upgrades[uid] || 0;
    const cost = base * Math.pow(COST_MUL[uid]||1.3, lv);
    return {uid, lv, cost};
  }).sort((a,b) => a.cost - b.cost);

  const tbody = document.getElementById('upgrade-body');
  tbody.innerHTML = rows.map(({uid, lv, cost}) => {
    const affordable = coins >= cost;
    const badge = affordable
      ? '<span class="badge-ok">✓</span>'
      : '<span class="badge-no">-</span>';
    return `<tr>
      <td style="color:var(--text)">${uid}</td>
      <td style="color:var(--accent)">${lv}</td>
      <td style="color:var(--text2)">-</td>
      <td style="color:var(--text2)">${fmt(cost)}</td>
      <td>${badge}</td>
    </tr>`;
  }).join('');
}

function renderCharter(charter) {
  if (!charter) return;
  const el = document.getElementById('charter-status');
  if (charter.maxed) {
    el.innerHTML = '<div style="color:var(--green); font-size:12px;">✓ All zones unlocked!</div>';
    return;
  }
  const surveyOk = charter.survey_done;
  const coinsOk  = charter.has_coins;
  el.innerHTML = `
    <div class="charter-row">
      <span class="charter-key">Source</span>
      <span class="charter-val">${charter.source_zone||'?'}</span>
    </div>
    <div class="charter-row">
      <span class="charter-key">Target</span>
      <span class="charter-val ok">${charter.target_zone||'?'}</span>
    </div>
    <div class="charter-row">
      <span class="charter-key">Survey</span>
      <span class="charter-val ${surveyOk?'ok':'no'}">${charter.caught||0}/${charter.target||0} ${surveyOk?'✓':'✗'}</span>
    </div>
    <div class="charter-row">
      <span class="charter-key">Fee</span>
      <span class="charter-val">${fmt(charter.charter_fee||0)}</span>
    </div>
    <div class="charter-row">
      <span class="charter-key">Coins</span>
      <span class="charter-val ${coinsOk?'ok':'no'}">${fmt(charter.coins||0)} ${coinsOk?'✓':'✗'}</span>
    </div>
  `;
}

function poll() {
  fetch('/api/state')
    .then(r=>r.json())
    .then(d => {
      const s = d.stats;
      const running = d.running;
      const paused  = d.paused;

      // Status dot
      const dot  = document.getElementById('status-dot');
      const stxt = document.getElementById('status-text');
      dot.className = 'status-dot' + (running ? (paused ? ' paused' : ' running') : '');
      stxt.textContent = running ? (paused ? 'Paused' : 'Running') : 'Stopped';

      if (s.username) document.getElementById('user-name').textContent = '@' + s.username;

      document.getElementById('stat-coins').textContent    = fmt(s.coins);
      document.getElementById('stat-gems').textContent     = fmt(s.gems);
      document.getElementById('stat-loops').textContent    = s.loop_count;
      document.getElementById('stat-casts').textContent    = s.cast_count;
      document.getElementById('stat-rebirths').textContent = s.rebirth_count;
      document.getElementById('stat-charters').textContent = s.charter_count;
      document.getElementById('zone-current').textContent  = s.current_zone;
      document.getElementById('zone-best').textContent     = s.best_zone;
      document.getElementById('prestige-count').textContent = s.prestige_count;
      document.getElementById('token-count').textContent   = s.current_tokens;
      document.getElementById('mult-val').textContent      = 'x' + (s.current_multiplier||1).toFixed(4);
      document.getElementById('rebirth-pct').textContent   = (s.rebirth_progress||0).toFixed(1) + '%';
      document.getElementById('rebirth-bar').style.width   = (s.rebirth_progress||0) + '%';
      document.getElementById('lifetime-coins').textContent = fmt(s.lifetime_coins);
      document.getElementById('rebirth-threshold').textContent = fmt(s.rebirth_threshold);
      document.getElementById('stat-travel-loop').textContent = s.last_travel_loop || '-';

      renderUpgrades(s.upgrades, s.coins);
      renderCharter(d.charter);

      // Logs
      const logs = d.logs;
      if (logs.length !== lastLogCount) {
        const box = document.getElementById('log-box');
        const newLogs = logs.slice(lastLogCount);
        newLogs.forEach(l => {
          const div = document.createElement('div');
          div.className = 'log-line';
          div.innerHTML = `<span class="log-time">${l.time}</span><span class="log-msg ${l.level}">${l.msg}</span>`;
          box.appendChild(div);
        });
        lastLogCount = logs.length;
        if (autoScroll) box.scrollTop = box.scrollHeight;
      }
    })
    .catch(() => {});
}

setInterval(poll, 1000);
poll();
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif parsed.path == "/api/state":
            charter = None
            if gui_state["stats"].get("upgrades"):
                try:
                    dummy_state = {
                        "upgrades": gui_state["stats"]["upgrades"],
                        "charterDex": {},
                        "coins": gui_state["stats"]["coins"],
                        "zoneId": gui_state["stats"]["current_zone"],
                    }
                    charter = get_charter_status(dummy_state)
                except:
                    pass

            data = {
                "running": gui_state["running"],
                "paused":  gui_state["paused"],
                "stats":   gui_state["stats"],
                "config":  gui_state["config"],
                "logs":    gui_state["logs"][-200:],
                "charter": charter,
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global bot_thread
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length)) if length else {}

        if parsed.path == "/api/control":
            action = body.get("action")
            if action == "start" and not gui_state["running"]:
                gui_state["running"] = True
                gui_state["paused"]  = False
                stop_event.clear()
                bot_thread = threading.Thread(target=bot_loop, daemon=True)
                bot_thread.start()
                add_log("Bot started via GUI", "success")
            elif action == "pause" and gui_state["running"]:
                gui_state["paused"] = not gui_state["paused"]
                add_log("Bot " + ("paused" if gui_state["paused"] else "resumed"), "warn")
            elif action == "stop":
                stop_event.set()
                gui_state["running"] = False
                gui_state["paused"]  = False
                add_log("Bot stopped via GUI", "warn")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        elif parsed.path == "/api/tokens":
            bearer  = body.get("bearer", "")
            refresh = body.get("refresh", "")
            try:
                if bearer:  save_bearer(bearer)
                if refresh: save_refresh_token(refresh)
                add_log("Tokens saved via GUI", "success")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        elif parsed.path == "/api/config":
            gui_state["config"].update(body)
            add_log(f"Config updated: {body}", "info")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        elif parsed.path == "/api/logs/clear":
            gui_state["logs"] = []
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    PORT = 8765
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n{'='*50}")
    print(f"  Fishin' Chiyo Bot GUI")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*50}\n")
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop_event.set()
        print("\nShutdown.")