"""
FISHIN' CHIYO - GUI AUTO BOT
Tkinter GUI with settings panel, live log, start/stop control.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import math
import json
import os
import requests

# ===========================
# KONSTANTA
# ===========================
SUPABASE_URL    = "https://qsoptshiorjhoiwwrumb.supabase.co/auth/v1/token"
SUPABASE_APIKEY = "sb_publishable_OtJtVXVlBl7_JPubRQg6rA_5uyAGLqP"
GAME_URL        = "https://fishin-chiyo.vercel.app/api/game/action"

ZONE_ORDER = [
    "pond", "lake", "river", "marsh", "pier", "reef", "open", "kelp",
    "storm", "frozen", "twilight", "abyss", "garden", "glass_current",
    "ember_vent", "starfall_rift", "moon_bloom", "clockwork_tide",
    "dreamwhale_expanse", "astral_tide", "echoing_orbit",
]

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

SETTINGS_FILE = "gui_settings.json"


# ===========================
# DEFAULT SETTINGS
# ===========================
DEFAULT_SETTINGS = {
    "cast_per_cycle": 10,
    "delay_between_cast": 0.3,
    "delay_after_sell": 0.5,
    "auto_sell": True,
    "auto_upgrade": True,
    "auto_travel": True,
    "auto_rebirth": True,
    "auto_repair": True,
    "auto_clean": True,
    "max_rebirth": 0,
    "upgrade_priority": "rod,bait,reel,market_bell,bobber,hook,tacklebox,dock",
}


# ===========================
# REBIRTH FORMULAS
# ===========================
def threshold_for_rebirth(prestige_count):
    count = max(0, int(prestige_count or 0))
    return math.ceil(1_000_000 * (1.14 ** min(count, 20)) * (1.06 ** max(0, count - 20)))


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
    except FileNotFoundError:
        return ""


def load_refresh_token():
    try:
        with open("refresh_token.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def save_bearer(token):
    with open("bearer.txt", "w") as f:
        f.write(token)


def save_refresh_token(token):
    with open("refresh_token.txt", "w") as f:
        f.write(token)


def refresh_access_token(log_fn):
    log_fn("[REFRESH] Mencoba refresh token...")
    rt = load_refresh_token()
    if not rt:
        log_fn("[REFRESH] Tidak ada refresh_token.txt!")
        return None
    headers = {"Content-Type": "application/json", "apikey": SUPABASE_APIKEY}
    try:
        resp = requests.post(SUPABASE_URL, params={"grant_type": "refresh_token"},
                             headers=headers, json={"refresh_token": rt}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("access_token"):
                save_bearer(data["access_token"])
            if data.get("refresh_token"):
                save_refresh_token(data["refresh_token"])
            log_fn("[REFRESH] Token berhasil diperbarui!")
            return data.get("access_token")
        else:
            log_fn(f"[REFRESH] Gagal: {resp.status_code}")
            return None
    except Exception as e:
        log_fn(f"[REFRESH] Error: {e}")
        return None


# ===========================
# API HELPER
# ===========================
def make_headers():
    return {
        "Authorization": f"Bearer {load_bearer()}",
        "Content-Type": "application/json",
        "Referer": "https://fishin-chiyo.vercel.app/",
        "User-Agent": "Mozilla/5.0"
    }


def send_action(action_type, payload_data, revision, log_fn):
    body = {"type": action_type, "payload": payload_data, "revision": revision}
    try:
        resp = requests.post(GAME_URL, headers=make_headers(), json=body, timeout=30)
    except requests.exceptions.Timeout:
        log_fn(f"[{action_type}] Timeout 30s")
        return {"retry": True, "success": False, "revision": revision, "state": {}}
    except requests.exceptions.ConnectionError:
        log_fn(f"[{action_type}] Connection error")
        return {"retry": True, "success": False, "revision": revision, "state": {}}

    if resp.status_code == 401:
        new_token = refresh_access_token(log_fn)
        if new_token:
            try:
                resp = requests.post(GAME_URL, headers=make_headers(), json=body, timeout=30)
            except:
                return {"retry": True, "success": False, "revision": revision, "state": {}}
        else:
            return {"retry": False, "success": False, "revision": revision, "state": {}}

    try:
        data = resp.json()
        state = data.get("state", {})
        rev = data.get("revision", state.get("revision", revision))
        if resp.status_code == 409:
            return {"retry": True, "success": False, "revision": rev, "state": state}
        if resp.status_code == 400:
            return {"retry": False, "repair": True, "success": False, "revision": rev, "state": state}
        return {"retry": False, "success": resp.status_code == 200, "revision": rev, "state": state}
    except:
        return {"retry": False, "success": False, "revision": revision, "state": {}}


# ===========================
# BOT ENGINE
# ===========================
class BotEngine:
    def __init__(self, log_fn, status_fn, settings):
        self.log = log_fn
        self.status = status_fn
        self.settings = settings
        self.running = False
        self.revision = 0
        self.state = {}
        self.rebirth_count = 0

    def stop(self):
        self.running = False

    def action(self, action_type, payload={}):
        for attempt in range(5):
            result = send_action(action_type, payload, self.revision, self.log)
            self.revision = result["revision"]
            if result.get("retry"):
                time.sleep(2)
                continue
            if result.get("repair"):
                self.repair_hook()
                time.sleep(3)
                continue
            if result.get("success"):
                self.state = result.get("state", self.state)
            return result
        return result

    def repair_hook(self):
        if self.settings.get("auto_clean", True):
            send_action("cleanHook", {"score": 1}, self.revision, self.log)
        if self.settings.get("auto_repair", True):
            r = send_action("repairHook", {}, self.revision, self.log)
            self.revision = r["revision"]

    def travel_to_best(self):
        if not self.settings.get("auto_travel", True):
            return
        line = self.state.get("upgrades", {}).get("line", 0)
        current = self.state.get("zoneId", "pond")
        best_idx = min(line, len(ZONE_ORDER) - 1)
        best = ZONE_ORDER[best_idx]
        try:
            cur_idx = ZONE_ORDER.index(current)
        except ValueError:
            cur_idx = 0
        if cur_idx < best_idx:
            self.log(f"[TRAVEL] {current} -> {best}")
            self.action("travel", {"zoneId": best})

    def auto_upgrade(self):
        if not self.settings.get("auto_upgrade", True):
            return
        coins = self.state.get("coins", 0)
        upgrades = self.state.get("upgrades", {})
        priority = [x.strip() for x in self.settings.get("upgrade_priority", "rod,bait").split(",")]
        bought = True
        while bought:
            bought = False
            for uid in priority:
                data = UPGRADE_DATA.get(uid)
                if not data:
                    continue
                lv = upgrades.get(uid, 0)
                cost = data["baseCost"] * (data["costMul"] ** lv)
                if coins >= cost:
                    r = self.action("buyUpgrade", {"id": uid, "count": 1})
                    if r.get("success"):
                        coins = self.state.get("coins", 0)
                        upgrades = self.state.get("upgrades", upgrades)
                        bought = True
                    time.sleep(0.1)

    def do_rebirth(self):
        if not self.settings.get("auto_rebirth", True):
            return False
        max_rb = int(self.settings.get("max_rebirth", 0))
        if max_rb > 0 and self.rebirth_count >= max_rb:
            return False
        if not can_rebirth(self.state):
            return False

        self.log("★★★ REBIRTH! ★★★")
        r = self.action("prestige", {})
        if r.get("success"):
            self.rebirth_count += 1
            tokens = get_total_tokens(self.state)
            mult = multiplier_from_tokens(tokens)
            self.log(f"[REBIRTH] #{self.state.get('prestigeCount',0)} | Tokens: {tokens} | x{mult:.4f}")
            time.sleep(3)
            self.travel_to_best()
            self.auto_upgrade()
            return True
        return False

    def update_status(self):
        s = self.state
        coins = s.get("coins", 0)
        zone = s.get("zoneId", "?")
        prestige = s.get("prestigeCount", 0)
        lifetime = s.get("lifetimeCoins", 0)
        threshold = threshold_for_rebirth(prestige)
        progress = min(100, lifetime / threshold * 100) if threshold > 0 else 0
        tokens = get_total_tokens(s)
        self.status(f"Zone: {zone} | Coins: {coins:,.0f} | Prestige: {prestige} | "
                    f"Tokens: {tokens} | Rebirth: {progress:.1f}% | Session RB: {self.rebirth_count}")

    def run(self):
        self.running = True
        self.log("=== BOT STARTED ===")

        # Init: sell to get state
        self.log("[INIT] Getting state...")
        r = self.action("sell")
        if not self.state:
            self.log("[ERROR] Cannot get state. Check bearer/refresh token!")
            self.running = False
            return

        name = self.state.get("user", {}).get("name", "Unknown")
        self.log(f"[INIT] Player: {name}")
        self.travel_to_best()
        self.auto_upgrade()
        self.update_status()

        cast_per = int(self.settings.get("cast_per_cycle", 10))
        delay_cast = float(self.settings.get("delay_between_cast", 0.3))
        delay_sell = float(self.settings.get("delay_after_sell", 0.5))

        while self.running:
            # Check rebirth
            if self.do_rebirth():
                self.update_status()
                continue

            # Cast
            for i in range(cast_per):
                if not self.running:
                    break
                self.action("cast", {"fightGrade": "perfect", "auto": False})
                time.sleep(delay_cast)

            if not self.running:
                break

            # Sell
            if self.settings.get("auto_sell", True):
                self.action("sell")
                time.sleep(delay_sell)

            # Travel & Upgrade
            self.travel_to_best()
            self.auto_upgrade()

            # Check rebirth again
            self.do_rebirth()

            self.update_status()

        self.log("=== BOT STOPPED ===")


# ===========================
# GUI APPLICATION
# ===========================
class ChiyoGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Fishin' Chiyo - Auto Bot GUI")
        self.root.geometry("900x650")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        self.bot_thread = None
        self.engine = None
        self.settings = self.load_settings()

        self.build_ui()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    saved = json.load(f)
                    merged = {**DEFAULT_SETTINGS, **saved}
                    return merged
            except:
                pass
        return dict(DEFAULT_SETTINGS)

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=2)

    def build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1a1a2e")
        style.configure("TLabel", background="#1a1a2e", foreground="#F5E8C7", font=("Consolas", 10))
        style.configure("TButton", font=("Consolas", 10, "bold"))
        style.configure("Header.TLabel", font=("Consolas", 14, "bold"), foreground="#E8B547")
        style.configure("Status.TLabel", font=("Consolas", 9), foreground="#7FC8E8")

        # Header
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Label(header, text="FISHIN' CHIYO - AUTO BOT", style="Header.TLabel").pack(side="left")

        # Status bar
        self.status_var = tk.StringVar(value="Ready. Configure settings and press START.")
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", padx=10, pady=2)
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(fill="x")

        # Main area: left=settings, right=log
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Settings
        left = ttk.LabelFrame(main, text=" SETTINGS ", padding=10)
        left.pack(side="left", fill="y", padx=(0, 5))

        self.vars = {}
        self._add_check(left, "auto_sell", "Auto Sell")
        self._add_check(left, "auto_upgrade", "Auto Upgrade")
        self._add_check(left, "auto_travel", "Auto Travel (best zone)")
        self._add_check(left, "auto_rebirth", "Auto Rebirth")
        self._add_check(left, "auto_repair", "Auto Repair Hook")
        self._add_check(left, "auto_clean", "Auto Clean Hook")

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)

        self._add_entry(left, "cast_per_cycle", "Cast per cycle:", 6)
        self._add_entry(left, "delay_between_cast", "Delay cast (s):", 6)
        self._add_entry(left, "delay_after_sell", "Delay sell (s):", 6)
        self._add_entry(left, "max_rebirth", "Max rebirth (0=∞):", 6)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(left, text="Upgrade Priority:").pack(anchor="w")
        self.vars["upgrade_priority"] = tk.StringVar(value=self.settings.get("upgrade_priority", ""))
        ttk.Entry(left, textvariable=self.vars["upgrade_priority"], width=30).pack(fill="x", pady=2)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)

        # Buttons
        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill="x", pady=5)

        self.start_btn = ttk.Button(btn_frame, text="▶ START", command=self.start_bot)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.stop_btn = ttk.Button(btn_frame, text="■ STOP", command=self.stop_bot, state="disabled")
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Button(left, text="Save Settings", command=self.apply_settings).pack(fill="x", pady=3)
        ttk.Button(left, text="Clear Log", command=self.clear_log).pack(fill="x", pady=3)

        # Right: Log
        right = ttk.LabelFrame(main, text=" LOG ", padding=5)
        right.pack(side="right", fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(
            right, wrap="word", font=("Consolas", 9),
            bg="#0f0f1a", fg="#E8E8E8", insertbackground="#E8B547",
            height=25
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    def _add_check(self, parent, key, label):
        var = tk.BooleanVar(value=self.settings.get(key, True))
        self.vars[key] = var
        ttk.Checkbutton(parent, text=label, variable=var).pack(anchor="w", pady=1)

    def _add_entry(self, parent, key, label, width):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Label(frame, text=label, width=18).pack(side="left")
        var = tk.StringVar(value=str(self.settings.get(key, "")))
        self.vars[key] = var
        ttk.Entry(frame, textvariable=var, width=width).pack(side="left")

    def log(self, msg):
        """Thread-safe log append."""
        def _append():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _append)

    def update_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def apply_settings(self):
        for key, var in self.vars.items():
            val = var.get()
            if isinstance(val, bool):
                self.settings[key] = val
            else:
                self.settings[key] = str(val)
        self.save_settings()
        self.log("[SETTINGS] Saved!")

    def start_bot(self):
        bearer = load_bearer()
        if not bearer:
            messagebox.showerror("Error", "bearer.txt tidak ditemukan!\n\nBuat file bearer.txt berisi access_token dari browser.")
            return

        self.apply_settings()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        self.engine = BotEngine(self.log, self.update_status, self.settings)
        self.bot_thread = threading.Thread(target=self.engine.run, daemon=True)
        self.bot_thread.start()

    def stop_bot(self):
        if self.engine:
            self.engine.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_status("Bot stopped.")

    def run(self):
        self.root.mainloop()


# ===========================
# ENTRY POINT
# ===========================
if __name__ == "__main__":
    app = ChiyoGUI()
    app.run()
