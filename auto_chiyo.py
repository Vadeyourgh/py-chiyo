import requests
import time
import json
import os
import random
import string

# ===========================
# KONSTANTA
# ===========================
SUPABASE_URL = "https://qsoptshiorjhoiwwrumb.supabase.co/auth/v1/token"
SUPABASE_APIKEY = "sb_publishable_OtJtVXVlBl7_JPubRQg6rA_5uyAGLqP"
GAME_URL = "https://fishin-chiyo.vercel.app/api/game/action"

# ===========================
# KONFIGURASI AUTO
# ===========================
CONFIG = {
    "auto_sell": True,
    "auto_cast": True,
    "auto_repair": True,
    "auto_clean": True,
    "auto_upgrade": True,
    "auto_zone": True,
    "auto_use_item": True,
    "auto_rebirth": True,         # auto rebirth (prestige)
    "auto_charter": True,         # auto charter zone
    "auto_equip_gear": True,      # auto equip best gear
    "cast_per_cycle": 10,
    "delay_between_cast": 0.3,
    "delay_after_sell": 0.5,
    "delay_after_repair": 3,
    "upgrade_threshold": 0.5,     # beli upgrade jika harga <= 50% dari coins
    "rebirth_min_coins": 500000,  # minimum coins sebelum rebirth
    "upgrade_max_level": {},      # per-upgrade max level, e.g. {"rod": 50, "bait": 40}
}

# ===========================
# UPGRADE PRIORITY (urutan beli)
# Berdasarkan data game state kamu
# ===========================
UPGRADE_PRIORITY = [
    "rod",
    "bait",
    "bobber",
    "hook",
    "junk_filter",
    "tackle_net",
    "weather_vane",
    "dock",
    "crew",
    "line",
    "market_bell",
    "reel",
]

# ===========================
# ZONE ORDER (dari murah ke mahal)
# Berdasarkan dex data dari game state
# ===========================
ZONE_ORDER = [
    "pond",
    "lake",
    "river",
    "marsh",
    "pier",
    "reef",
    "open",
    "kelp",
    "storm",
    "frozen",
    "twilight",
    "abyss",
    "garden",
    "glass_current",
    "ember_vent",
    "starfall_rift",
    "moon_bloom",
    "clockwork_tide",
    "dreamwhale_expanse",
    "astral_tide",
    "echoing_orbit",
]

# ===========================
# ITEMS YANG BISA DIPAKAI
# ===========================
USABLE_ITEMS = [
    "worm_tin",
    "shiny_spoon",
    "sturdy_float",
    "chum_bucket",
    "lucky_pearl",
    "storm_jar",
    "pocket_moon",
    "prism_chum",
    "jelly_lantern",
    "tiny_net",
]


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
    print("\n[REFRESH] Bearer kadaluarsa, mencoba refresh...")

    refresh_token = load_refresh_token()

    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_APIKEY
    }
    payload = {"refresh_token": refresh_token}
    params = {"grant_type": "refresh_token"}

    try:
        response = requests.post(SUPABASE_URL, params=params, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")

            if new_access_token:
                save_bearer(new_access_token)
                print("[REFRESH] access_token baru disimpan")

            if new_refresh_token:
                save_refresh_token(new_refresh_token)
                print("[REFRESH] refresh_token baru disimpan")

            return new_access_token
        else:
            print(f"[REFRESH] Gagal! Status: {response.status_code}")
            print(response.text)
            return None

    except Exception as e:
        print(f"[REFRESH] Error: {e}")
        return None


# ===========================
# GENERATE REQUEST ID (mirip game)
# ===========================
def gen_request_id(prefix="bot"):
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{rand}"


# ===========================
# HEADERS
# ===========================
def make_headers():
    return {
        "Authorization": f"Bearer {load_bearer()}",
        "Content-Type": "application/json",
        "Referer": "https://fishin-chiyo.vercel.app/",
        "Origin": "https://fishin-chiyo.vercel.app",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "x-fishin-request-id": gen_request_id("cast"),
    }


# ===========================
# SEND ACTION (CORE)
# ===========================
def send_action(action_type, payload_data, revision_value):
    body = {
        "type": action_type,
        "payload": payload_data,
        "revision": revision_value
    }

    headers = make_headers()
    headers["x-fishin-request-id"] = gen_request_id(action_type[:4])

    response = requests.post(GAME_URL, headers=headers, json=body)

    # Bearer expired → refresh & retry
    if response.status_code == 401:
        print("[401] Bearer expired → refreshing...")
        new_token = refresh_access_token()
        if new_token:
            headers["Authorization"] = f"Bearer {new_token}"
            response = requests.post(GAME_URL, headers=headers, json=body)
        else:
            return {
                "retry": False, "repair": False, "clean": False,
                "revision": revision_value, "success": False,
                "state": None, "error": "auth_failed"
            }

    try:
        data = response.json()
        state = data.get("state", {})
        user = state.get("user", {})

        coins = state.get("coins", 0)
        gems = state.get("gems", 0)
        zone = state.get("zoneId", "?")

        latest_revision = data.get("revision", state.get("revision", revision_value))

        print(f"  [{action_type.upper()}] Status: {response.status_code} | "
              f"Coins: {coins:,.0f} | Gems: {gems} | Zone: {zone} | Rev: {latest_revision}")

        # Conflict (409) → need to sync revision
        if response.status_code == 409:
            return {
                "retry": True, "repair": False, "clean": False,
                "revision": latest_revision, "success": False,
                "state": state, "error": "conflict"
            }

        # Error (400) → hook broken or foul
        if response.status_code == 400:
            error_msg = data.get("error", "")
            if "foul" in error_msg.lower() or "clean" in error_msg.lower():
                return {
                    "retry": False, "repair": False, "clean": True,
                    "revision": latest_revision, "success": False,
                    "state": state, "error": error_msg
                }
            if "hook" in error_msg.lower() or "broken" in error_msg.lower() or "repair" in error_msg.lower():
                return {
                    "retry": False, "repair": True, "clean": False,
                    "revision": latest_revision, "success": False,
                    "state": state, "error": error_msg
                }
            # Other 400 error
            return {
                "retry": False, "repair": False, "clean": False,
                "revision": latest_revision, "success": False,
                "state": state, "error": error_msg
            }

        return {
            "retry": False, "repair": False, "clean": False,
            "revision": latest_revision, "success": response.status_code == 200,
            "state": state, "error": None
        }

    except Exception as e:
        print(f"  [{action_type.upper()}] Error parsing response: {e}")
        return {
            "retry": False, "repair": False, "clean": False,
            "revision": revision_value, "success": False,
            "state": None, "error": str(e)
        }


# ===========================
# AUTO REPAIR HOOK
# ===========================
def auto_repair_hook(revision):
    print("\n[AUTO-REPAIR] Memperbaiki hook...")

    result = send_action("repairHook", {}, revision)
    revision = result["revision"]

    if result.get("success"):
        print("[AUTO-REPAIR] Hook berhasil diperbaiki!")
        return revision

    # Coba clean dulu lalu repair
    print("[AUTO-REPAIR] Repair gagal, mencoba cleanHook...")
    result = send_action("cleanHook", {"score": 1}, revision)
    revision = result["revision"]

    if result.get("success"):
        print("[AUTO-CLEAN] Hook berhasil dibersihkan!")

    # Coba repair lagi
    result = send_action("repairHook", {}, revision)
    revision = result["revision"]

    return revision


# ===========================
# AUTO CLEAN HOOK
# ===========================
def auto_clean_hook(revision):
    print("\n[AUTO-CLEAN] Membersihkan hook...")

    result = send_action("cleanHook", {"score": 1}, revision)
    revision = result["revision"]

    if result.get("success"):
        print("[AUTO-CLEAN] Hook berhasil dibersihkan!")

    return revision


# ===========================
# AUTO UPGRADE
# API: {"type": "buyUpgrade", "payload": {"id": "rod", "count": 1}}
# ===========================
def auto_upgrade(revision, state):
    if not CONFIG["auto_upgrade"] or state is None:
        return revision

    coins = state.get("coins", 0)
    current_upgrades = state.get("upgrades", {})

    print(f"\n[AUTO-UPGRADE] Coins: {coins:,.0f} | Checking upgrades...")

    bought_any = True
    total_bought = 0

    while bought_any:
        bought_any = False

        for upgrade_name in UPGRADE_PRIORITY:
            current_level = current_upgrades.get(upgrade_name, 0)

            # Cek max level dari config
            max_lv = CONFIG["upgrade_max_level"].get(upgrade_name, 9999)
            if current_level >= max_lv:
                continue

            # Server akan reject kalau coins tidak cukup,
            # tapi kita tetap cek threshold supaya tidak spam request
            # Estimasi kasar: cost bertambah exponential
            # Kita langsung kirim aja, server yang validasi
            # Tapi pakai threshold supaya tidak buang semua coins
            estimated_cost = coins * 0.01  # assume upgrade ~1% of coins (conservative)

            # Kirim buy request
            result = send_action("buyUpgrade", {"id": upgrade_name, "count": 1}, revision)
            revision = result["revision"]

            if result.get("success"):
                current_upgrades[upgrade_name] = current_level + 1
                if result.get("state"):
                    new_coins = result["state"].get("coins", coins)
                    spent = coins - new_coins
                    coins = new_coins
                    print(f"  [UPGRADE] ✓ {upgrade_name} Lv.{current_level} → Lv.{current_level+1} "
                          f"| Spent: {spent:,.0f} | Remaining: {coins:,.0f}")
                bought_any = True
                total_bought += 1
                time.sleep(0.2)

                # Stop jika coins sudah rendah (< threshold)
                if coins < 100:
                    bought_any = False
                    break
            elif result.get("retry"):
                revision = result["revision"]
                time.sleep(0.5)
                break
            else:
                # Tidak bisa beli (coins kurang atau max level) → skip ke next
                continue

    print(f"[AUTO-UPGRADE] Selesai. Bought: {total_bought} | Coins tersisa: {coins:,.0f}")
    return revision


# ===========================
# AUTO ZONE (travel/change zone)
# API: {"type": "changeZone", "payload": {"zoneId": "kelp"}}
# ===========================
def auto_zone(revision, state):
    if not CONFIG["auto_zone"] or state is None:
        return revision

    current_zone = state.get("zoneId", "pond")

    # Cari index zone saat ini
    try:
        current_idx = ZONE_ORDER.index(current_zone)
    except ValueError:
        # Zone tidak ada di list (mungkin zone baru)
        return revision

    # Jika sudah di zone terakhir, skip
    if current_idx >= len(ZONE_ORDER) - 1:
        return revision

    next_zone = ZONE_ORDER[current_idx + 1]

    print(f"\n[AUTO-ZONE] Mencoba pindah: {current_zone} → {next_zone}")
    result = send_action("changeZone", {"zoneId": next_zone}, revision)
    revision = result["revision"]

    if result.get("success"):
        print(f"[AUTO-ZONE] ✓ Berhasil pindah ke {next_zone}!")
    else:
        error = result.get("error", "")
        print(f"[AUTO-ZONE] ✗ Gagal pindah ({error})")

    return revision


# ===========================
# AUTO USE ITEMS
# API: {"type": "useItem", "payload": {"id": "worm_tin"}}
# ===========================
def auto_use_items(revision, state):
    if not CONFIG["auto_use_item"] or state is None:
        return revision

    items = state.get("items", {})
    active_items = state.get("activeItems", {})

    for item_id in USABLE_ITEMS:
        count = items.get(item_id, 0)
        # Jika punya item dan belum aktif
        if count > 0 and item_id not in active_items:
            print(f"  [AUTO-ITEM] Menggunakan {item_id} (qty: {count})")
            result = send_action("useItem", {"id": item_id}, revision)
            revision = result["revision"]

            if result.get("success"):
                print(f"  [AUTO-ITEM] ✓ {item_id} aktif!")
            else:
                print(f"  [AUTO-ITEM] ✗ {item_id} gagal: {result.get('error')}")
            time.sleep(0.2)

    return revision


# ===========================
# AUTO REBIRTH (Prestige)
# API: {"type": "rebirth", "payload": {}}
# ===========================
def auto_rebirth(revision, state):
    if not CONFIG["auto_rebirth"] or state is None:
        return revision

    coins = state.get("coins", 0)
    prestige_count = state.get("prestigeCount", 0)

    # Hanya rebirth jika coins mencukupi minimum threshold
    if coins < CONFIG["rebirth_min_coins"]:
        return revision

    print(f"\n[AUTO-REBIRTH] Coins: {coins:,.0f} | Prestige #{prestige_count + 1}")
    result = send_action("rebirth", {}, revision)
    revision = result["revision"]

    if result.get("success"):
        new_state = result.get("state", {})
        new_prestige = new_state.get("prestigeCount", prestige_count)
        new_tokens = new_state.get("prestigeTokens", 0)
        print(f"[AUTO-REBIRTH] ✓ Rebirth berhasil! Prestige #{new_prestige} | Tokens: {new_tokens}")
    else:
        error = result.get("error", "")
        print(f"[AUTO-REBIRTH] ✗ Gagal rebirth: {error}")

    return revision


# ===========================
# AUTO CHARTER
# API: {"type": "charter", "payload": {}}
# ===========================
def auto_charter(revision, state):
    if not CONFIG["auto_charter"] or state is None:
        return revision

    # Charter hanya bisa jika fishdex zone penuh
    # Kita coba aja, server yang validasi
    print(f"\n[AUTO-CHARTER] Mencoba charter...")
    result = send_action("charter", {}, revision)
    revision = result["revision"]

    if result.get("success"):
        print(f"[AUTO-CHARTER] ✓ Charter berhasil!")
    else:
        error = result.get("error", "")
        if error:
            print(f"[AUTO-CHARTER] ✗ Gagal: {error}")

    return revision


# ===========================
# PRINT STATUS
# ===========================
def print_status(state, cycle_count):
    if state is None:
        return

    user = state.get("user", {})
    coins = state.get("coins", 0)
    gems = state.get("gems", 0)
    zone = state.get("zoneId", "?")
    upgrades = state.get("upgrades", {})
    maintenance = state.get("maintenance", {})
    hook_durability = maintenance.get("hookDurability", 0)
    hook_max = maintenance.get("hookMax", 100)
    prestige = state.get("prestigeCount", 0)
    prestige_tokens = state.get("prestigeTokens", 0)
    active_items = state.get("activeItems", {})
    inventory_count = len(state.get("inventory", []))

    print("\n" + "=" * 60)
    print(f"  CHIYO AUTO BOT - Cycle #{cycle_count}")
    print("=" * 60)
    print(f"  Player    : {user.get('name', 'Unknown')}")
    print(f"  Coins     : {coins:,.0f}")
    print(f"  Gems      : {gems}")
    print(f"  Zone      : {zone}")
    print(f"  Hook      : {hook_durability:.1f}/{hook_max}")
    print(f"  Prestige  : #{prestige} (Tokens: {prestige_tokens})")
    print(f"  Inventory : {inventory_count} fish")
    print(f"  Active    : {', '.join(active_items.keys()) if active_items else 'none'}")
    print(f"  ─── Upgrades ───")
    print(f"  Rod: {upgrades.get('rod', 0)} | Bait: {upgrades.get('bait', 0)} | "
          f"Bobber: {upgrades.get('bobber', 0)} | Hook: {upgrades.get('hook', 0)}")
    print(f"  Net: {upgrades.get('tackle_net', 0)} | Dock: {upgrades.get('dock', 0)} | "
          f"Crew: {upgrades.get('crew', 0)} | Junk: {upgrades.get('junk_filter', 0)}")
    print(f"  Vane: {upgrades.get('weather_vane', 0)} | Line: {upgrades.get('line', 0)} | "
          f"Reel: {upgrades.get('reel', 0)} | Bell: {upgrades.get('market_bell', 0)}")
    print("=" * 60)


# ==================================
# MAIN LOOP
# ==================================
def main():
    print("=" * 60)
    print("  CHIYO FISH - FULL AUTO BOT (Python API)")
    print("  ─────────────────────────────────────────")
    print("  Features:")
    print("    ✓ Auto Cast (perfect fight grade)")
    print("    ✓ Auto Sell")
    print("    ✓ Auto Upgrade (all upgrades)")
    print("    ✓ Auto Repair & Clean Hook")
    print("    ✓ Auto Use Items (worm_tin, shiny_spoon, etc)")
    print("    ✓ Auto Zone (travel to next zone)")
    print("    ✓ Auto Rebirth (prestige)")
    print("    ✓ Auto Charter")
    print("=" * 60)

    # Starting revision — will auto-update from first response
    revision = 0
    cycle_count = 0
    last_state = None
    rebirth_cycle = 0  # track cycles since last rebirth attempt

    # === INITIAL SYNC: Get current state via heartbeat/sell ===
    print("\n[INIT] Syncing game state...")
    result = send_action("sell", {}, revision)
    revision = result["revision"]
    last_state = result.get("state") or last_state

    if last_state:
        print(f"[INIT] ✓ Synced! Rev: {revision}")
        print_status(last_state, 0)
    else:
        print("[INIT] ⚠ Tidak bisa sync, mencoba lanjut...")

    while True:
        cycle_count += 1
        rebirth_cycle += 1

        # =========================
        # STEP 1 - AUTO SELL
        # =========================
        print(f"\n{'─' * 50}")
        print(f"  CYCLE #{cycle_count} - SELL")
        print(f"{'─' * 50}")

        attempts = 0
        while attempts < 5:
            attempts += 1
            result = send_action("sell", {}, revision)
            revision = result["revision"]
            last_state = result.get("state") or last_state

            if result.get("retry"):
                time.sleep(0.5)
                continue

            if result.get("repair"):
                revision = auto_repair_hook(revision)
                time.sleep(CONFIG["delay_after_repair"])
                continue

            if result.get("clean"):
                revision = auto_clean_hook(revision)
                time.sleep(1)
                continue

            if result.get("success"):
                print("  ✓ SELL berhasil!")
                break

            # Other error — just continue
            break

        time.sleep(CONFIG["delay_after_sell"])

        # =========================
        # STEP 2 - AUTO USE ITEMS
        # =========================
        if CONFIG["auto_use_item"] and last_state:
            revision = auto_use_items(revision, last_state)

        # =========================
        # STEP 3 - AUTO UPGRADE
        # =========================
        if CONFIG["auto_upgrade"] and last_state:
            revision = auto_upgrade(revision, last_state)

        # =========================
        # STEP 4 - AUTO ZONE
        # =========================
        if CONFIG["auto_zone"] and last_state:
            revision = auto_zone(revision, last_state)

        # =========================
        # STEP 5 - AUTO CAST
        # =========================
        print(f"\n{'─' * 50}")
        print(f"  CYCLE #{cycle_count} - CAST x{CONFIG['cast_per_cycle']}")
        print(f"{'─' * 50}")

        for i in range(CONFIG["cast_per_cycle"]):
            attempt = 0
            while True:
                attempt += 1
                result = send_action(
                    "cast",
                    {"fightGrade": "perfect", "auto": False},
                    revision
                )
                revision = result["revision"]
                last_state = result.get("state") or last_state

                if result.get("retry"):
                    time.sleep(0.5)
                    continue

                if result.get("repair"):
                    revision = auto_repair_hook(revision)
                    time.sleep(CONFIG["delay_after_repair"])
                    continue

                if result.get("clean"):
                    revision = auto_clean_hook(revision)
                    time.sleep(1)
                    continue

                if result.get("success"):
                    # Show catch info if available
                    inv = last_state.get("inventory", []) if last_state else []
                    if inv:
                        last_fish = inv[-1]
                        fish_name = last_fish.get("name", "?")
                        fish_val = last_fish.get("value", 0)
                        fish_rarity = last_fish.get("rarity", "?")
                        mutation = last_fish.get("mutation")
                        mut_str = f" [{mutation['name']}]" if mutation else ""
                        print(f"  ✓ Cast {i+1}/{CONFIG['cast_per_cycle']} | "
                              f"{fish_name}{mut_str} ({fish_rarity}) ${fish_val:,}")
                    else:
                        print(f"  ✓ Cast {i+1}/{CONFIG['cast_per_cycle']}")
                    break

                if attempt >= 3:
                    print(f"  ✗ Cast {i+1} gagal setelah {attempt}x, skip")
                    break

                time.sleep(0.5)

            time.sleep(CONFIG["delay_between_cast"])

        # =========================
        # STEP 6 - AUTO CHARTER (setiap 5 cycle)
        # =========================
        if CONFIG["auto_charter"] and cycle_count % 5 == 0 and last_state:
            revision = auto_charter(revision, last_state)

        # =========================
        # STEP 7 - AUTO REBIRTH (setiap 20 cycle)
        # =========================
        if CONFIG["auto_rebirth"] and rebirth_cycle >= 20 and last_state:
            revision = auto_rebirth(revision, last_state)
            rebirth_cycle = 0

        # =========================
        # PRINT STATUS
        # =========================
        print_status(last_state, cycle_count)

        print(f"\n  → Next cycle...\n")


# ==================================
# ENTRY POINT
# ==================================
if __name__ == "__main__":
    main()
