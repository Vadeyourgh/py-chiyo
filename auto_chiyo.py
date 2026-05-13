import requests
import time
import json
import os

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
    "auto_use_item": True,       # auto pakai item (worm_tin, shiny_spoon, dll)
    "cast_per_cycle": 10,        # jumlah cast per siklus
    "delay_between_cast": 0.5,   # delay antar cast (detik)
    "delay_after_sell": 1,       # delay setelah sell
    "delay_after_repair": 5,     # delay setelah repair
    "upgrade_threshold": 0.3,    # beli upgrade jika harga <= 30% dari coins
}

# ===========================
# UPGRADE PRIORITY (urutan beli)
# ===========================
UPGRADE_PRIORITY = [
    "rod",
    "bait",
    "bobber",
    "hook",
    "tackle_net",
    "weather_vane",
    "line",
    "dock",
    "tacklebox",
    "crew",
]

# ===========================
# ZONE ORDER (dari murah ke mahal)
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
]

# ===========================
# HARGA UPGRADE (base formula approximate)
# Chiyo Fish upgrade costs grow exponentially
# Format: upgrade_name -> (base_cost, multiplier)
# ===========================
UPGRADE_COSTS = {
    "rod":          (100, 1.8),
    "bait":         (50, 1.6),
    "bobber":       (75, 1.7),
    "hook":         (60, 1.65),
    "tackle_net":   (200, 1.75),
    "weather_vane": (300, 1.8),
    "line":         (150, 1.7),
    "dock":         (250, 1.75),
    "tacklebox":    (200, 1.7),
    "crew":         (350, 1.8),
}


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
# SEND ACTION (CORE)
# ===========================
def send_action(action_type, payload_data, revision_value):
    payload = {
        "type": action_type,
        "payload": payload_data,
        "revision": revision_value
    }

    response = requests.post(GAME_URL, headers=make_headers(), json=payload)

    # Bearer expired → refresh & retry
    if response.status_code == 401:
        print("[401] Bearer expired → refreshing...")
        new_token = refresh_access_token()
        if new_token:
            response = requests.post(GAME_URL, headers=make_headers(), json=payload)
        else:
            return {
                "retry": False, "repair": False, "clean": False,
                "revision": revision_value, "success": False,
                "state": None
            }

    try:
        data = response.json()
        state = data.get("state", {})
        user = state.get("user", {})

        name = user.get("name", "Unknown")
        coins = state.get("coins", 0)
        gems = state.get("gems", 0)
        zone = state.get("zoneId", "?")
        upgrades = state.get("upgrades", {})

        latest_revision = data.get("revision", state.get("revision", revision_value))

        print(f"  [{action_type.upper()}] Status: {response.status_code} | "
              f"Coins: {coins:,.0f} | Gems: {gems} | Zone: {zone} | Rev: {latest_revision}")

        # Conflict (409) → retry
        if response.status_code == 409:
            return {
                "retry": True, "repair": False, "clean": False,
                "revision": latest_revision, "success": False,
                "state": state
            }

        # Hook broken (400)
        if response.status_code == 400:
            error_msg = data.get("error", "")
            if "foul" in error_msg.lower() or "clean" in error_msg.lower():
                return {
                    "retry": False, "repair": False, "clean": True,
                    "revision": latest_revision, "success": False,
                    "state": state
                }
            return {
                "retry": False, "repair": True, "clean": False,
                "revision": latest_revision, "success": False,
                "state": state
            }

        return {
            "retry": False, "repair": False, "clean": False,
            "revision": latest_revision, "success": response.status_code == 200,
            "state": state
        }

    except Exception as e:
        print(f"  [{action_type.upper()}] Error parsing response: {e}")
        return {
            "retry": False, "repair": False, "clean": False,
            "revision": revision_value, "success": False,
            "state": None
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

    # Jika masih error, coba clean dulu
    print("[AUTO-REPAIR] Repair gagal, mencoba cleanHook...")
    result = send_action("cleanHook", {"score": 1}, revision)
    revision = result["revision"]

    if result.get("success"):
        print("[AUTO-CLEAN] Hook berhasil dibersihkan!")

    # Coba repair lagi setelah clean
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
# ===========================
def auto_upgrade(revision, state):
    if not CONFIG["auto_upgrade"] or state is None:
        return revision

    coins = state.get("coins", 0)
    current_upgrades = state.get("upgrades", {})

    print(f"\n[AUTO-UPGRADE] Coins: {coins:,.0f} | Checking upgrades...")

    upgraded = True
    while upgraded:
        upgraded = False

        for upgrade_name in UPGRADE_PRIORITY:
            current_level = current_upgrades.get(upgrade_name, 0)

            # Estimasi harga berdasarkan level
            if upgrade_name in UPGRADE_COSTS:
                base, mult = UPGRADE_COSTS[upgrade_name]
                estimated_cost = base * (mult ** current_level)
            else:
                estimated_cost = 1000 * (1.8 ** current_level)

            # Beli jika cukup uang dan harga <= threshold
            if coins >= estimated_cost and estimated_cost <= coins * CONFIG["upgrade_threshold"]:
                print(f"  [UPGRADE] Membeli {upgrade_name} (Lv.{current_level} → Lv.{current_level+1}) "
                      f"| Est. cost: {estimated_cost:,.0f}")

                result = send_action("buyUpgrade", {"upgradeId": upgrade_name}, revision)
                revision = result["revision"]

                if result.get("success"):
                    current_upgrades[upgrade_name] = current_level + 1
                    if result.get("state"):
                        coins = result["state"].get("coins", coins)
                    upgraded = True
                    time.sleep(0.3)
                elif result.get("retry"):
                    revision = result["revision"]
                    time.sleep(1)
                    break
                else:
                    # Harga tidak cukup atau error lain, skip
                    break

    print(f"[AUTO-UPGRADE] Selesai. Coins tersisa: {coins:,.0f}")
    return revision


# ===========================
# AUTO ZONE
# ===========================
def auto_zone(revision, state):
    if not CONFIG["auto_zone"] or state is None:
        return revision

    current_zone = state.get("zoneId", "pond")
    coins = state.get("coins", 0)

    # Cari index zone saat ini
    try:
        current_idx = ZONE_ORDER.index(current_zone)
    except ValueError:
        return revision

    # Jika sudah di zone terakhir, skip
    if current_idx >= len(ZONE_ORDER) - 1:
        return revision

    next_zone = ZONE_ORDER[current_idx + 1]

    # Zone unlock costs (approximate)
    zone_costs = {
        "lake": 5000,
        "river": 25000,
        "marsh": 100000,
        "pier": 500000,
        "reef": 2000000,
        "open": 10000000,
        "kelp": 50000000,
        "storm": 200000000,
        "frozen": 1000000000,
        "twilight": 5000000000,
        "abyss": 25000000000,
        "garden": 100000000000,
        "glass_current": 500000000000,
        "ember_vent": 2000000000000,
        "starfall_rift": 10000000000000,
    }

    zone_cost = zone_costs.get(next_zone, float("inf"))

    if coins >= zone_cost:
        print(f"\n[AUTO-ZONE] Pindah zone: {current_zone} → {next_zone}")
        result = send_action("changeZone", {"zoneId": next_zone}, revision)
        revision = result["revision"]

        if result.get("success"):
            print(f"[AUTO-ZONE] Berhasil pindah ke {next_zone}!")
        else:
            print(f"[AUTO-ZONE] Gagal pindah zone")

    return revision


# ===========================
# AUTO USE ITEMS
# ===========================
def auto_use_items(revision, state):
    if not CONFIG["auto_use_item"] or state is None:
        return revision

    items = state.get("items", {})
    active_items = state.get("activeItems", {})

    # Items yang bisa dipakai untuk boost
    usable_items = {
        "worm_tin": "Boost catch speed",
        "shiny_spoon": "Boost coin value",
        "sturdy_float": "Reduce break chance",
        "chum_bucket": "Attract rare fish",
        "lucky_pearl": "Boost luck",
    }

    for item_id, description in usable_items.items():
        count = items.get(item_id, 0)
        # Jika punya item dan belum aktif
        if count > 0 and item_id not in active_items:
            print(f"  [AUTO-ITEM] Menggunakan {item_id} ({description})")
            result = send_action("useItem", {"itemId": item_id}, revision)
            revision = result["revision"]

            if result.get("success"):
                print(f"  [AUTO-ITEM] {item_id} aktif!")
            time.sleep(0.3)

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

    print("\n" + "=" * 50)
    print(f"  CHIYO AUTO BOT - Cycle #{cycle_count}")
    print("=" * 50)
    print(f"  Player  : {user.get('name', 'Unknown')}")
    print(f"  Coins   : {coins:,.0f}")
    print(f"  Gems    : {gems}")
    print(f"  Zone    : {zone}")
    print(f"  Hook    : {hook_durability:.1f}/{hook_max}")
    print(f"  Rod Lv  : {upgrades.get('rod', 0)} | Bait Lv: {upgrades.get('bait', 0)} | "
          f"Bobber Lv: {upgrades.get('bobber', 0)}")
    print(f"  Hook Lv : {upgrades.get('hook', 0)} | Net Lv: {upgrades.get('tackle_net', 0)} | "
          f"Dock Lv: {upgrades.get('dock', 0)}")
    print("=" * 50)


# ==================================
# MAIN LOOP
# ==================================
def main():
    print("=" * 50)
    print("  CHIYO FISH - FULL AUTO BOT")
    print("  Features: Auto Sell, Cast, Upgrade, Zone, Repair")
    print("=" * 50)

    revision = 271  # Starting revision (akan auto-update)
    cycle_count = 0
    last_state = None

    while True:
        cycle_count += 1

        # =========================
        # STEP 1 - AUTO SELL
        # =========================
        print(f"\n{'─' * 40}")
        print(f"  CYCLE #{cycle_count} - SELL")
        print(f"{'─' * 40}")

        while True:
            result = send_action("sell", {}, revision)
            revision = result["revision"]
            last_state = result.get("state") or last_state

            if result.get("retry"):
                time.sleep(1)
                continue

            if result.get("repair"):
                revision = auto_repair_hook(revision)
                time.sleep(CONFIG["delay_after_repair"])
                continue

            if result.get("clean"):
                revision = auto_clean_hook(revision)
                time.sleep(2)
                continue

            if result.get("success"):
                print("  ✓ SELL berhasil!")
                break

            print("  ✗ SELL gagal, retry...")
            time.sleep(3)

        time.sleep(CONFIG["delay_after_sell"])

        # =========================
        # STEP 2 - AUTO UPGRADE
        # =========================
        if CONFIG["auto_upgrade"] and last_state:
            revision = auto_upgrade(revision, last_state)

        # =========================
        # STEP 3 - AUTO ZONE
        # =========================
        if CONFIG["auto_zone"] and last_state:
            revision = auto_zone(revision, last_state)

        # =========================
        # STEP 4 - AUTO USE ITEMS
        # =========================
        if CONFIG["auto_use_item"] and last_state:
            revision = auto_use_items(revision, last_state)

        # =========================
        # STEP 5 - AUTO CAST
        # =========================
        print(f"\n{'─' * 40}")
        print(f"  CYCLE #{cycle_count} - CAST x{CONFIG['cast_per_cycle']}")
        print(f"{'─' * 40}")

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
                    time.sleep(1)
                    continue

                if result.get("repair"):
                    revision = auto_repair_hook(revision)
                    time.sleep(CONFIG["delay_after_repair"])
                    continue

                if result.get("clean"):
                    revision = auto_clean_hook(revision)
                    time.sleep(2)
                    continue

                if result.get("success"):
                    print(f"  ✓ Cast {i+1}/{CONFIG['cast_per_cycle']} berhasil")
                    break

                if attempt >= 3:
                    print(f"  ✗ Cast {i+1} gagal setelah {attempt} attempt, skip")
                    break

                time.sleep(1)

            time.sleep(CONFIG["delay_between_cast"])

        # =========================
        # PRINT STATUS
        # =========================
        print_status(last_state, cycle_count)

        print(f"\n  → Kembali ke SELL...\n")


# ==================================
# ENTRY POINT
# ==================================
if __name__ == "__main__":
    main()
