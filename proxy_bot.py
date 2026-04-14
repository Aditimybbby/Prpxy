#!/usr/bin/env python3
"""
╔══════════════════════════════════════════╗
║        🛡️  PROXY HUNTER BOT  v2         ║
║  Live scanning · Geo · /test · Scheduler ║
╚══════════════════════════════════════════╝

pip install python-telegram-bot aiohttp
export BOT_TOKEN=your_token
python proxy_bot.py
"""

import asyncio
import aiohttp
import re
import time
import sys
import random
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("ProxyBot")

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
BOT_TOKEN        = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MAX_CONCURRENT   = 150
CHECK_TIMEOUT    = 8
UI_UPDATE_EVERY  = 2.5   # seconds between message edits
TEST_URL         = "http://httpbin.org/ip"
GEO_URL          = "http://ip-api.com/json/{ip}?fields=countryCode,country"

# ─────────────────────────────────────────
#  SOURCES  (40+ total)
# ─────────────────────────────────────────
SOURCES: Dict[str, List[str]] = {
    "http": [
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/http/data.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
        "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/http_proxies.txt",
        "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/https_proxies.txt",
        "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=10000",
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://www.proxy-list.download/api/v1/get?type=https",
    ],
    "socks5": [
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/socks5/data.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
        "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/socks5_proxies.txt",
        "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/socks5.txt",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5",
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=10000",
        "https://www.proxy-list.download/api/v1/get?type=socks5",
    ],
    "socks4": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt",
        "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks4.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
        "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/socks4_proxies.txt",
        "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/socks4.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4",
        "https://www.proxy-list.download/api/v1/get?type=socks4",
    ],
}

PTYPES_ALL = ["http", "socks5", "socks4"]

# ─────────────────────────────────────────
#  PER-CHAT STATE
# ─────────────────────────────────────────
@dataclass
class ScanState:
    ptype: str        = "http"
    speed_filter: str = "any"

    phase: str          = "idle"
    sources_total: int  = 0
    sources_done: int   = 0
    raw_count: int      = 0
    checked: int        = 0
    total_to_check: int = 0
    working: int        = 0
    dead: int           = 0

    results: Dict[str, Dict] = field(default_factory=dict)

    stop_event: asyncio.Event       = field(default_factory=asyncio.Event)
    task: Optional[asyncio.Task]    = None

    message_id: Optional[int]  = None
    chat_id: Optional[int]     = None
    last_edit: float            = 0.0

    schedule_hours: int                    = 0
    schedule_task: Optional[asyncio.Task]  = None


chat_states: Dict[int, ScanState] = {}


def get_state(chat_id: int) -> ScanState:
    if chat_id not in chat_states:
        chat_states[chat_id] = ScanState()
    return chat_states[chat_id]

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
COUNTRY_FLAGS = {
    "US":"🇺🇸","DE":"🇩🇪","FR":"🇫🇷","GB":"🇬🇧","NL":"🇳🇱","RU":"🇷🇺",
    "CN":"🇨🇳","JP":"🇯🇵","KR":"🇰🇷","BR":"🇧🇷","IN":"🇮🇳","CA":"🇨🇦",
    "AU":"🇦🇺","SG":"🇸🇬","HK":"🇭🇰","TR":"🇹🇷","ID":"🇮🇩","TH":"🇹🇭",
    "UA":"🇺🇦","PL":"🇵🇱","IT":"🇮🇹","ES":"🇪🇸","VN":"🇻🇳","PK":"🇵🇰",
    "BD":"🇧🇩","MX":"🇲🇽","AR":"🇦🇷","SE":"🇸🇪","NO":"🇳🇴","FI":"🇫🇮",
    "CH":"🇨🇭","AT":"🇦🇹","BE":"🇧🇪","CZ":"🇨🇿","RO":"🇷🇴","HU":"🇭🇺",
    "BG":"🇧🇬","GR":"🇬🇷","PT":"🇵🇹","ZA":"🇿🇦","EG":"🇪🇬","IR":"🇮🇷",
}

def flag(code: str) -> str:
    return COUNTRY_FLAGS.get((code or "").upper(), "🌐")

def lat_emoji(lat: Optional[float]) -> str:
    if lat is None: return "❓"
    if lat < 0.5:   return "⚡"
    if lat < 1.0:   return "🟢"
    if lat < 2.0:   return "🟡"
    if lat < 3.5:   return "🟠"
    return "🔴"

def progress_bar(done: int, total: int, width: int = 14) -> str:
    if total == 0: return "░" * width
    filled = int(width * done / total)
    return "█" * filled + "░" * (width - filled)

def pct(done: int, total: int) -> str:
    if total == 0: return "0%"
    return f"{int(100 * done / total)}%"

def type_emoji(pt: str) -> str:
    return {"http":"🌐","socks5":"🧦","socks4":"🔌","all":"📦"}.get(pt, "🔷")

def speed_label(sf: str) -> str:
    return {"any":"⚡ Any","fast":"🟢 Fast (<1s)","ultra":"⚡ Ultra (<0.5s)"}.get(sf, sf)

def passes_filter(latency: Optional[float], sf: str) -> bool:
    if sf == "any":   return True
    if latency is None: return False
    if sf == "fast":  return latency < 1.0
    if sf == "ultra": return latency < 0.5
    return True

# ─────────────────────────────────────────
#  FETCH
# ─────────────────────────────────────────
async def fetch_one(session: aiohttp.ClientSession, url: str) -> set:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as r:
            return set(re.findall(r"\d+\.\d+\.\d+\.\d+:\d+", await r.text()))
    except Exception:
        return set()

# ─────────────────────────────────────────
#  GEO LOOKUP
# ─────────────────────────────────────────
async def geo_lookup(session: aiohttp.ClientSession, ip: str) -> Tuple[str, str]:
    try:
        async with session.get(
            GEO_URL.format(ip=ip),
            timeout=aiohttp.ClientTimeout(total=4),
        ) as r:
            d = await r.json()
            return d.get("countryCode", ""), d.get("country", "")
    except Exception:
        return "", ""

# ─────────────────────────────────────────
#  CHECK ONE PROXY
# ─────────────────────────────────────────
async def check_proxy(
    session: aiohttp.ClientSession,
    proxy: str,
    ptype: str,
    sem: asyncio.Semaphore,
) -> Tuple[str, str, Optional[float], bool]:
    async with sem:
        scheme = {"socks5":"socks5h","socks4":"socks4","http":"http"}.get(ptype, "http")
        start  = time.monotonic()
        try:
            async with session.get(
                TEST_URL,
                proxy=f"{scheme}://{proxy}",
                timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT),
            ) as r:
                if r.status == 200:
                    return proxy, ptype, time.monotonic() - start, True
        except Exception:
            pass
        return proxy, ptype, None, False

# ─────────────────────────────────────────
#  SCAN MESSAGE BUILDER
# ─────────────────────────────────────────
def build_scan_msg(st: ScanState) -> str:
    te    = type_emoji(st.ptype)
    label = st.ptype.upper() if st.ptype != "all" else "ALL TYPES"

    lines = [
        f"╔══ 🛡️ <b>PROXY HUNTER</b> ══╗\n",
        f"  {te} <b>{label}</b>  ·  {speed_label(st.speed_filter)}\n\n",
    ]

    # Phase 1
    if st.phase in ("fetching","checking","done","stopped"):
        bar = progress_bar(st.sources_done, max(st.sources_total, 1))
        lines.append(
            f"📡 <b>Fetching sources</b>\n"
            f"  <code>[{bar}]</code> {st.sources_done}/{st.sources_total}\n"
            f"  Raw proxies collected: <b>{st.raw_count:,}</b>\n\n"
        )

    # Phase 2
    if st.phase in ("checking","done","stopped"):
        bar2 = progress_bar(st.checked, max(st.total_to_check, 1))
        p    = pct(st.checked, st.total_to_check)
        fast = sum(1 for d in st.results.values()
                   if d.get("latency") is not None and d["latency"] < 1.0)
        lines.append(
            f"🔬 <b>Checking proxies</b>\n"
            f"  <code>[{bar2}]</code> {p}  ({st.checked:,} / {st.total_to_check:,})\n\n"
            f"  ✅ Working   <b>{st.working:,}</b>\n"
            f"  ❌ Dead      {st.dead:,}\n"
            f"  ⚡ Fast      <b>{fast:,}</b>\n"
        )

    if st.phase == "done":
        lines.append(f"\n✅ <b>Scan complete!</b>  {st.working:,} proxies found.")
    elif st.phase == "stopped":
        lines.append(f"\n⏹ <b>Stopped.</b>  {st.working:,} proxies found so far.")

    return "".join(lines)

# ─────────────────────────────────────────
#  KEYBOARDS
# ─────────────────────────────────────────
def home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍  Get Proxies", callback_data="pick_type")],
        [
            InlineKeyboardButton("📊 Stats",       callback_data="stats"),
            InlineKeyboardButton("⚙️ Settings",    callback_data="settings"),
        ],
        [
            InlineKeyboardButton("🧪 Test a Proxy", callback_data="test_prompt"),
            InlineKeyboardButton("📖 Help",         callback_data="help"),
        ],
    ])

def pick_type_kb(st: ScanState) -> InlineKeyboardMarkup:
    def btn(pt):
        sel = "✅ " if st.ptype == pt else ""
        return InlineKeyboardButton(
            sel + type_emoji(pt) + " " + pt.upper(),
            callback_data=f"set_type:{pt}",
        )
    speed_next = {"any":"fast","fast":"ultra","ultra":"any"}
    return InlineKeyboardMarkup([
        [btn("http"),   btn("socks5")],
        [btn("socks4"), btn("all")],
        [InlineKeyboardButton(
            f"Speed: {speed_label(st.speed_filter)}  (tap to cycle)",
            callback_data=f"set_speed:{speed_next[st.speed_filter]}",
        )],
        [
            InlineKeyboardButton("🚀 Start Scan", callback_data="start_scan"),
            InlineKeyboardButton("🏠 Home",       callback_data="home"),
        ],
    ])

def scanning_kb(working: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏹  Stop",                  callback_data="stop_scan"),
        InlineKeyboardButton(f"📥 Get TXT  ({working})", callback_data="export_now"),
    ]])

def done_kb(working: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📥 Get TXT  ({working})", callback_data="export_now")],
        [
            InlineKeyboardButton("🔄 Run Again", callback_data="start_scan"),
            InlineKeyboardButton("🏠 Home",      callback_data="home"),
        ],
    ])

def settings_kb(st: ScanState) -> InlineKeyboardMarkup:
    speed_next  = {"any":"fast","fast":"ultra","ultra":"any"}
    hours_cycle = {0:1, 1:3, 3:6, 6:12, 12:24, 24:0}
    sched_lbl = (
        f"🔔 Auto-scan: every {st.schedule_hours}h"
        if st.schedule_hours > 0 else "🔔 Auto-scan: OFF"
    )
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"Speed filter: {speed_label(st.speed_filter)}",
            callback_data=f"set_speed:{speed_next[st.speed_filter]}",
        )],
        [InlineKeyboardButton(
            sched_lbl + "  (tap to cycle)",
            callback_data=f"set_schedule:{hours_cycle.get(st.schedule_hours, 0)}",
        )],
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
    ])

# ─────────────────────────────────────────
#  EDIT HELPERS
# ─────────────────────────────────────────
async def _edit_progress(bot, st: ScanState):
    if not st.message_id: return
    try:
        await bot.edit_message_text(
            chat_id=st.chat_id,
            message_id=st.message_id,
            text=build_scan_msg(st),
            parse_mode=ParseMode.HTML,
            reply_markup=scanning_kb(st.working),
        )
        st.last_edit = time.monotonic()
    except BadRequest:
        pass
    except Exception as e:
        log.debug(f"edit_progress: {e}")


async def _edit_final(bot, st: ScanState):
    if not st.message_id: return
    try:
        await bot.edit_message_text(
            chat_id=st.chat_id,
            message_id=st.message_id,
            text=build_scan_msg(st),
            parse_mode=ParseMode.HTML,
            reply_markup=done_kb(st.working),
        )
    except Exception as e:
        log.debug(f"edit_final: {e}")

# ─────────────────────────────────────────
#  CORE SCAN TASK
# ─────────────────────────────────────────
async def run_scan(app, chat_id: int):
    st     = get_state(chat_id)
    bot    = app.bot
    ptypes = PTYPES_ALL if st.ptype == "all" else [st.ptype]

    all_urls: List[Tuple[str, str]] = [
        (url, pt)
        for pt in ptypes
        for url in SOURCES.get(pt, [])
    ]
    st.sources_total = len(all_urls)
    st.phase         = "fetching"

    connector = aiohttp.TCPConnector(limit=200, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:

        # ── Phase 1: Fetch ──
        raw_by_type: Dict[str, set] = {pt: set() for pt in ptypes}

        async def fetch_and_track(url: str, pt: str):
            if st.stop_event.is_set(): return
            found = await fetch_one(session, url)
            raw_by_type[pt].update(found)
            st.sources_done += 1
            st.raw_count = sum(len(v) for v in raw_by_type.values())
            # light UI update during fetch phase
            now = time.monotonic()
            if now - st.last_edit >= UI_UPDATE_EVERY:
                await _edit_progress(bot, st)

        await asyncio.gather(*[fetch_and_track(u, pt) for u, pt in all_urls])

        if st.stop_event.is_set():
            st.phase = "stopped"
            await _edit_final(bot, st)
            return

        # ── Phase 2: Check ──
        st.phase = "checking"
        all_proxies = [
            (p, pt)
            for pt, proxies in raw_by_type.items()
            for p in proxies
        ]
        st.total_to_check = len(all_proxies)

        sem         = asyncio.Semaphore(MAX_CONCURRENT)
        check_tasks = [check_proxy(session, p, pt, sem) for p, pt in all_proxies]

        for fut in asyncio.as_completed(check_tasks):
            if st.stop_event.is_set():
                break
            proxy, pt, latency, ok = await fut
            st.checked += 1
            if ok:
                st.working += 1
                if passes_filter(latency, st.speed_filter):
                    st.results[proxy] = {
                        "latency": latency,
                        "ptype":   pt,
                        "country": "",
                    }
            else:
                st.dead += 1

            now = time.monotonic()
            if now - st.last_edit >= UI_UPDATE_EVERY:
                await _edit_progress(bot, st)

    # Geo enrich in background (non-blocking)
    asyncio.create_task(_geo_enrich(st))

    st.phase = "stopped" if st.stop_event.is_set() else "done"
    await _edit_final(bot, st)

    # Notify if scheduled
    if st.phase == "done" and st.schedule_hours > 0:
        try:
            await bot.send_message(
                chat_id,
                f"✅ <b>Scheduled scan done!</b>  Found <b>{st.working:,}</b> proxies.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def _geo_enrich(st: ScanState):
    """Best-effort: look up country for top 50 results after scan."""
    proxies = list(st.results.keys())[:50]
    connector = aiohttp.TCPConnector(limit=10, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for proxy in proxies:
            if proxy not in st.results: continue
            ip   = proxy.split(":")[0]
            code, name = await geo_lookup(session, ip)
            st.results[proxy]["country"]     = code
            st.results[proxy]["countryName"] = name
            await asyncio.sleep(0.07)  # ip-api free: ~45 req/min

# ─────────────────────────────────────────
#  SCHEDULER
# ─────────────────────────────────────────
async def scheduler_loop(app, chat_id: int):
    st = get_state(chat_id)
    while True:
        await asyncio.sleep(st.schedule_hours * 3600)
        if st.schedule_hours == 0: break
        ptype = st.ptype
        speed = st.speed_filter
        sched = st.schedule_hours
        chat_states[chat_id] = ScanState(
            ptype=ptype, speed_filter=speed, schedule_hours=sched
        )
        new_st = get_state(chat_id)
        try:
            msg = await app.bot.send_message(
                chat_id,
                "⏰ <b>Auto-scan starting…</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏹ Stop", callback_data="stop_scan"),
                ]]),
            )
            new_st.message_id = msg.message_id
            new_st.chat_id    = chat_id
            new_st.task = asyncio.create_task(run_scan(app, chat_id))
        except Exception as e:
            log.error(f"scheduler: {e}")

# ─────────────────────────────────────────
#  EXPORT BUILDER
# ─────────────────────────────────────────
def build_export(st: ScanState, fmt: str = "plain") -> str:
    rows = sorted(
        [(p, d) for p, d in st.results.items()
         if passes_filter(d.get("latency"), st.speed_filter)],
        key=lambda x: (x[1].get("latency") or 999),
    )
    if not rows:
        return "# No proxies found matching your filter.\n"

    lines = []
    if fmt == "annotated":
        lines.append(
            f"# Proxy Hunter — {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"# Total: {len(rows)}\n#\n"
        )
        for proxy, d in rows:
            lat  = f"{d['latency']:.3f}s" if d.get("latency") else "?"
            cc   = d.get("country", "")
            fl   = flag(cc) if cc else ""
            pt   = d.get("ptype", "http")
            lines.append(f"{pt}://{proxy}  # {lat} {fl}{cc}\n")
    elif fmt == "curl":
        for proxy, d in rows:
            pt = d.get("ptype", "http")
            lines.append(f"--proxy {pt}://{proxy}\n")
    else:
        for proxy, _ in rows:
            lines.append(proxy + "\n")

    return "".join(lines)

# ─────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    get_state(update.effective_chat.id)  # init state
    await update.message.reply_html(
        "╔══════════════════════╗\n"
        "║  🛡️ <b>PROXY HUNTER BOT</b>  ║\n"
        "╚══════════════════════╝\n\n"
        "Scrapes <b>40+ sources</b>, checks every proxy live,\n"
        "and delivers working lists instantly.\n\n"
        "👇 <i>Tap <b>Get Proxies</b> to begin</i>",
        reply_markup=home_kb(),
    )


async def cmd_test(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/test IP:PORT [http|socks5|socks4]"""
    args = ctx.args or []
    if not args:
        await update.message.reply_html(
            "🧪 <b>Usage:</b>  <code>/test 1.2.3.4:8080 http</code>\n"
            "Protocol defaults to <code>http</code> if omitted."
        )
        return

    proxy = args[0].strip()
    ptype = (args[1].lower() if len(args) > 1 else "http")
    if ptype not in ("http", "socks5", "socks4"):
        ptype = "http"
    if not re.match(r"^\d{1,3}(?:\.\d{1,3}){3}:\d{1,5}$", proxy):
        await update.message.reply_html("❌ Invalid format. Use <code>IP:PORT</code>")
        return

    msg = await update.message.reply_html(f"🔬 Testing <code>{proxy}</code> ({ptype})…")

    sem = asyncio.Semaphore(1)
    connector = aiohttp.TCPConnector(limit=5, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        _, _, latency, ok = await check_proxy(session, proxy, ptype, sem)

    if ok:
        le    = lat_emoji(latency)
        lat_s = f"{latency:.3f}s"
        ip    = proxy.split(":")[0]
        async with aiohttp.ClientSession() as session:
            code, name = await geo_lookup(session, ip)
        fl = flag(code) if code else "🌐"
        result = (
            f"✅ <b>Proxy ALIVE</b>\n\n"
            f"  📡 <code>{proxy}</code>\n"
            f"  🔌 {ptype.upper()}\n"
            f"  {le} Latency: <b>{lat_s}</b>\n"
            f"  {fl} {name or 'Unknown'}"
        )
    else:
        result = (
            f"❌ <b>Proxy DEAD</b>\n\n"
            f"  📡 <code>{proxy}</code>\n"
            f"  🔌 {ptype.upper()}\n"
            f"  Timed out after {CHECK_TIMEOUT}s"
        )
    await msg.edit_text(result, parse_mode=ParseMode.HTML)


async def cmd_rotate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    st = get_state(update.effective_chat.id)
    if not st.results:
        await update.message.reply_html("⚠️ No proxies yet. Run a scan first.")
        return
    proxy, d = random.choice(list(st.results.items()))
    lat  = d.get("latency")
    pt   = d.get("ptype", "http")
    cc   = d.get("country", "")
    await update.message.reply_html(
        f"🎲 <b>Random proxy</b>\n\n"
        f"  <code>{proxy}</code>\n"
        f"  {lat_emoji(lat)} {f'{lat:.3f}s' if lat else '?'}  ·  "
        f"{pt.upper()}  ·  {flag(cc)}{cc or 'Unknown'}\n\n"
        f"  <code>--proxy {pt}://{proxy}</code>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🎲 Another one", callback_data="rotate"),
            InlineKeyboardButton("🏠 Home",        callback_data="home"),
        ]]),
    )


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    st = get_state(update.effective_chat.id)
    await _show_stats(
        lambda **kw: update.message.reply_html(**kw),
        st,
    )


async def _show_stats(reply_fn, st: ScanState):
    if not st.results:
        await reply_fn(
            text="📊 No data yet. Run a scan first.",
            reply_markup=home_kb(),
        )
        return
    lats = [d["latency"] for d in st.results.values() if d.get("latency")]
    by_type: Dict[str, int] = {}
    by_cc:   Dict[str, int] = {}
    for d in st.results.values():
        pt = d.get("ptype", "?")
        by_type[pt] = by_type.get(pt, 0) + 1
        cc = d.get("country", "")
        if cc: by_cc[cc] = by_cc.get(cc, 0) + 1

    avg_lat = sum(lats) / len(lats) if lats else 0
    fast    = sum(1 for l in lats if l < 1.0)
    ultra   = sum(1 for l in lats if l < 0.5)
    top5    = sorted(by_cc.items(), key=lambda x: -x[1])[:5]

    type_str = "  ".join(
        f"{type_emoji(pt)} {pt.upper()} <b>{c}</b>" for pt, c in by_type.items()
    )
    country_str = "\n".join(
        f"  {flag(cc)} {cc}  <b>{c}</b>" for cc, c in top5
    ) or "  <i>(geo loading in background…)</i>"

    await reply_fn(
        text=(
            "📊 <b>Last Scan Stats</b>\n"
            "══════════════════════\n\n"
            f"  📦 Working:     <b>{len(st.results):,}</b>\n"
            f"  ⚡ Avg latency: <b>{avg_lat:.2f}s</b>\n"
            f"  🟢 Fast (<1s):  <b>{fast:,}</b>\n"
            f"  ⚡ Ultra (<0.5s): <b>{ultra:,}</b>\n\n"
            f"  {type_str}\n\n"
            f"🌍 <b>Top countries:</b>\n{country_str}"
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📥 Export", callback_data="export_now"),
            InlineKeyboardButton("🏠 Home",   callback_data="home"),
        ]]),
    )

# ─────────────────────────────────────────
#  CALLBACK ROUTER
# ─────────────────────────────────────────
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q       = update.callback_query
    data    = q.data
    chat_id = q.message.chat_id
    st      = get_state(chat_id)
    await q.answer()

    # ── home ──
    if data == "home":
        await q.edit_message_text(
            "╔══════════════════════╗\n"
            "║  🛡️ <b>PROXY HUNTER BOT</b>  ║\n"
            "╚══════════════════════╝\n\n"
            "Scrapes <b>40+ sources</b>, checks every proxy live,\n"
            "and delivers working lists instantly.\n\n"
            "👇 <i>Tap <b>Get Proxies</b> to begin</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=home_kb(),
        )

    # ── pick type ──
    elif data == "pick_type":
        await q.edit_message_text(
            "🔍 <b>Configure your scan</b>\n\n"
            "Choose a protocol and speed filter,\nthen tap <b>Start Scan</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=pick_type_kb(st),
        )

    # ── set type ──
    elif data.startswith("set_type:"):
        st.ptype = data.split(":")[1]
        await q.edit_message_reply_markup(pick_type_kb(st))

    # ── set speed ──
    elif data.startswith("set_speed:"):
        st.speed_filter = data.split(":")[1]
        try:
            await q.edit_message_reply_markup(pick_type_kb(st))
        except Exception:
            try:
                await q.edit_message_reply_markup(settings_kb(st))
            except Exception:
                pass

    # ── start scan ──
    elif data == "start_scan":
        # Cancel running scan if any
        if st.task and not st.task.done():
            st.stop_event.set()
            await asyncio.sleep(0.3)
        # Reset but keep prefs
        ptype = st.ptype
        speed = st.speed_filter
        sched = st.schedule_hours
        chat_states[chat_id] = ScanState(
            ptype=ptype, speed_filter=speed, schedule_hours=sched
        )
        st = get_state(chat_id)
        st.chat_id = chat_id

        await q.edit_message_text(
            build_scan_msg(st),
            parse_mode=ParseMode.HTML,
            reply_markup=scanning_kb(0),
        )
        st.message_id = q.message.message_id
        st.task = asyncio.create_task(run_scan(ctx.application, chat_id))

    # ── stop ──
    elif data == "stop_scan":
        st.stop_event.set()
        st.phase = "stopped"
        await _edit_final(ctx.application.bot, st)

    # ── export (any time) ──
    elif data == "export_now":
        if not st.results:
            await q.answer("⚠️ No working proxies yet!", show_alert=True)
            return
        await q.message.reply_html(
            f"📥 <b>Export {len(st.results):,} proxies</b>\n\nChoose format:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📄 Plain IP:PORT",  callback_data="dl:plain"),
                    InlineKeyboardButton("📝 Annotated",      callback_data="dl:annotated"),
                ],
                [InlineKeyboardButton("🔧 curl flags",        callback_data="dl:curl")],
            ]),
        )

    # ── download ──
    elif data.startswith("dl:"):
        fmt = data.split(":")[1]
        if not st.results:
            await q.answer("⚠️ No data!", show_alert=True)
            return
        content = build_export(st, fmt=fmt)
        fname   = f"proxies_{st.ptype}_{fmt}_{int(time.time())}.txt"
        count   = content.strip().count("\n") + 1
        await q.message.reply_document(
            document=content.encode("utf-8"),
            filename=fname,
            caption=(
                f"📥 <b>{fmt.capitalize()} export</b>\n"
                f"  {type_emoji(st.ptype)} <b>{count:,}</b> proxies  ·  "
                f"{speed_label(st.speed_filter)}\n"
                f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC"
            ),
            parse_mode=ParseMode.HTML,
        )

    # ── stats ──
    elif data == "stats":
        await _show_stats(
            lambda text, **kw: q.edit_message_text(
                text, parse_mode=ParseMode.HTML, **kw
            ),
            st,
        )

    # ── rotate ──
    elif data == "rotate":
        if not st.results:
            await q.answer("No proxies yet!", show_alert=True)
            return
        proxy, d = random.choice(list(st.results.items()))
        lat  = d.get("latency")
        pt   = d.get("ptype", "http")
        cc   = d.get("country", "")
        await q.edit_message_text(
            f"🎲 <b>Random proxy</b>\n\n"
            f"  <code>{proxy}</code>\n"
            f"  {lat_emoji(lat)} {f'{lat:.3f}s' if lat else '?'}  ·  "
            f"{pt.upper()}  ·  {flag(cc)}{cc or 'Unknown'}\n\n"
            f"  <code>--proxy {pt}://{proxy}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎲 Another", callback_data="rotate"),
                InlineKeyboardButton("🏠 Home",    callback_data="home"),
            ]]),
        )

    # ── test prompt ──
    elif data == "test_prompt":
        await q.edit_message_text(
            "🧪 <b>Test a proxy</b>\n\n"
            "Send:\n<code>/test 1.2.3.4:8080 http</code>\n\n"
            "<i>Supported protocols: http, socks5, socks4</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Home", callback_data="home"),
            ]]),
        )

    # ── settings ──
    elif data == "settings":
        await q.edit_message_text(
            "⚙️ <b>Settings</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=settings_kb(st),
        )

    # ── set schedule ──
    elif data.startswith("set_schedule:"):
        hours = int(data.split(":")[1])
        st.schedule_hours = hours
        if st.schedule_task and not st.schedule_task.done():
            st.schedule_task.cancel()
        if hours > 0:
            st.schedule_task = asyncio.create_task(
                scheduler_loop(ctx.application, chat_id)
            )
        await q.edit_message_reply_markup(settings_kb(st))

    # ── help ──
    elif data == "help":
        await q.edit_message_text(
            "📖 <b>Help</b>\n\n"
            "<b>Flow:</b>\n"
            "  🔍 Get Proxies → pick protocol → Start Scan\n"
            "  Watch live progress\n"
            "  📥 Get TXT anytime (mid-scan or after)\n\n"
            "<b>Commands:</b>\n"
            "  /test IP:PORT [type] — test one proxy\n"
            "  /rotate              — random proxy from last scan\n"
            "  /stats               — stats from last scan\n\n"
            "<b>Speed filters:</b>\n"
            "  ⚡ Any — all working\n"
            "  🟢 Fast — under 1s\n"
            "  ⚡ Ultra — under 0.5s\n\n"
            "<b>Export formats:</b>\n"
            "  Plain    — IP:PORT per line\n"
            "  Annotated — with speed + country flag\n"
            "  curl     — --proxy flags",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Home", callback_data="home"),
            ]]),
        )

# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌  Set BOT_TOKEN:\n    export BOT_TOKEN=123:AAxx...")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("test",   cmd_test))
    app.add_handler(CommandHandler("rotate", cmd_rotate))
    app.add_handler(CommandHandler("stats",  cmd_stats))
    app.add_handler(CallbackQueryHandler(on_callback))

    async def post_init(application: Application):
        await application.bot.set_my_commands([
            BotCommand("start",  "🏠 Main menu"),
            BotCommand("test",   "🧪 Test: /test IP:PORT [http|socks5|socks4]"),
            BotCommand("rotate", "🎲 Random proxy from last scan"),
            BotCommand("stats",  "📊 Stats from last scan"),
        ])
        log.info("✅ Bot ready.")

    app.post_init = post_init
    log.info("🚀 Proxy Hunter Bot v2 starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
