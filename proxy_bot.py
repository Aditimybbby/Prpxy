#!/usr/bin/env python3
"""
╔══════════════════════════════════════════╗
║        🛡️  PROXY HUNTER BOT             ║
║   Telegram Bot — Rich GUI Edition        ║
╚══════════════════════════════════════════╝

Requirements:
    pip install python-telegram-bot aiohttp fastapi uvicorn

Usage:
    BOT_TOKEN=your_token python proxy_bot.py
"""

import asyncio
import aiohttp
import re
import time
import sys
import random
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode

# ─────────────────────────────────────────
#  Windows fix
# ─────────────────────────────────────────
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ─────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(name)s → %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("ProxyBot")

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

MAX_CONCURRENT_CHECK = 150
CHECK_TIMEOUT        = 8       # seconds per proxy
UPDATE_INTERVAL      = 300     # 5 min between auto-refreshes
PAGE_SIZE            = 10      # proxies per page

TEST_URLS = {
    "http":   "http://httpbin.org/ip",
    "socks5": "http://httpbin.org/ip",
}

# ─────────────────────────────────────────
#  PROXY SOURCES  (HTTP + SOCKS5)
# ─────────────────────────────────────────
SOURCES: Dict[str, List[str]] = {
    "http": [
        # ── GitHub raw lists ──
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
        # ── API endpoints ──
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=10000",
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://www.proxy-list.download/api/v1/get?type=https",
        "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
        "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt",
    ],
    "socks5": [
        # ── GitHub raw lists ──
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
        # ── API endpoints ──
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5",
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=10000",
        "https://www.proxy-list.download/api/v1/get?type=socks5",
        "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=socks5",
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

# ─────────────────────────────────────────
#  STORAGE
#  proxy_pool[type][proxy] = {score, latency, last_checked, failures}
# ─────────────────────────────────────────
proxy_pool: Dict[str, Dict[str, Dict]] = {
    "http":   {},
    "socks5": {},
    "socks4": {},
}
pool_meta = {
    "last_update": 0,
    "is_updating": False,
    "update_started": 0,
}

# ─────────────────────────────────────────
#  EMOJI HELPERS
# ─────────────────────────────────────────
def latency_emoji(lat: Optional[float]) -> str:
    if lat is None:    return "❓"
    if lat < 0.5:      return "⚡"
    if lat < 1.0:      return "🟢"
    if lat < 2.0:      return "🟡"
    if lat < 3.5:      return "🟠"
    return             "🔴"

def score_bar(score: int) -> str:
    filled = min(max(score // 5, 0), 10)
    return "█" * filled + "░" * (10 - filled)

def type_emoji(ptype: str) -> str:
    return {"http": "🌐", "socks5": "🧦", "socks4": "🔌"}.get(ptype, "🔷")

def format_ts(ts: int) -> str:
    if not ts: return "never"
    delta = int(time.time()) - ts
    if delta < 60:    return f"{delta}s ago"
    if delta < 3600:  return f"{delta // 60}m ago"
    return f"{delta // 3600}h ago"

# ─────────────────────────────────────────
#  FETCH
# ─────────────────────────────────────────
async def fetch_proxies(session: aiohttp.ClientSession, url: str) -> set:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as resp:
            text = await resp.text()
            return set(re.findall(r"\d+\.\d+\.\d+\.\d+:\d+", text))
    except Exception as e:
        log.debug(f"Fetch failed {url}: {e}")
        return set()

# ─────────────────────────────────────────
#  CHECK
# ─────────────────────────────────────────
async def check_proxy(
    session: aiohttp.ClientSession,
    proxy: str,
    ptype: str,
    sem: asyncio.Semaphore,
) -> tuple:
    async with sem:
        start = time.monotonic()
        scheme = "socks5h" if ptype == "socks5" else ("socks4" if ptype == "socks4" else "http")
        proxy_url = f"{scheme}://{proxy}"
        try:
            async with session.get(
                TEST_URLS.get(ptype, TEST_URLS["http"]),
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT),
            ) as resp:
                if resp.status == 200:
                    return proxy, ptype, time.monotonic() - start, True
        except Exception:
            pass
        return proxy, ptype, None, False

# ─────────────────────────────────────────
#  SCORING
# ─────────────────────────────────────────
def update_score(proxy: str, ptype: str, success: bool, latency: Optional[float]):
    pool = proxy_pool[ptype]
    data = pool.get(proxy, {"score": 10, "latency": 999.0, "failures": 0})

    if success:
        data["failures"] = 0
        data["score"] += 1
        if latency is not None:
            if latency < 0.5:  data["score"] += 3
            elif latency < 1:  data["score"] += 2
            elif latency < 2:  data["score"] += 1
            elif latency > 4:  data["score"] -= 1
            data["latency"] = round(latency, 3)
    else:
        data["failures"] = data.get("failures", 0) + 1
        data["score"]   -= 3

    data["last_checked"] = int(time.time())
    data["score"]        = max(data["score"], 0)

    if data["score"] == 0:
        pool.pop(proxy, None)
    else:
        pool[proxy] = data

# ─────────────────────────────────────────
#  CORE UPDATE LOOP
# ─────────────────────────────────────────
async def run_update(progress_cb=None):
    """Fetch + validate all proxies. Optional async callback for progress updates."""
    pool_meta["is_updating"]   = True
    pool_meta["update_started"] = int(time.time())
    total_checked = 0

    connector = aiohttp.TCPConnector(limit=200, ssl=False)
    sem       = asyncio.Semaphore(MAX_CONCURRENT_CHECK)

    async with aiohttp.ClientSession(connector=connector) as session:
        for ptype, urls in SOURCES.items():
            if progress_cb:
                await progress_cb(f"📡 Fetching <b>{ptype.upper()}</b> sources…")

            fetch_tasks = [fetch_proxies(session, u) for u in urls]
            results     = await asyncio.gather(*fetch_tasks)
            proxies     = list(set().union(*results))
            log.info(f"[{ptype}] raw collected: {len(proxies)}")

            if progress_cb:
                await progress_cb(
                    f"🔬 Checking <b>{len(proxies)}</b> {ptype.upper()} proxies…"
                )

            check_tasks = [check_proxy(session, p, ptype, sem) for p in proxies]
            for fut in asyncio.as_completed(check_tasks):
                proxy, pt, latency, ok = await fut
                update_score(proxy, pt, ok, latency)
                total_checked += 1

    pool_meta["last_update"] = int(time.time())
    pool_meta["is_updating"] = False
    log.info(f"Update done — checked {total_checked} proxies total")
    return total_checked

async def background_loop():
    while True:
        try:
            await run_update()
        except Exception as e:
            log.error(f"Update loop error: {e}")
            pool_meta["is_updating"] = False
        await asyncio.sleep(UPDATE_INTERVAL)

# ─────────────────────────────────────────
#  SORTED HELPERS
# ─────────────────────────────────────────
def get_sorted(ptype: str = "http") -> List[tuple]:
    pool = proxy_pool.get(ptype, {})
    return sorted(
        pool.items(),
        key=lambda x: (-x[1]["score"], x[1].get("latency", 999)),
    )

def total_count() -> int:
    return sum(len(p) for p in proxy_pool.values())

# ─────────────────────────────────────────
#  KEYBOARD BUILDERS
# ─────────────────────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 HTTP",   callback_data="list:http:0"),
            InlineKeyboardButton("🧦 SOCKS5", callback_data="list:socks5:0"),
            InlineKeyboardButton("🔌 SOCKS4", callback_data="list:socks4:0"),
        ],
        [
            InlineKeyboardButton("🏆 Best Proxies",   callback_data="best:http"),
            InlineKeyboardButton("🎲 Random Proxy",   callback_data="random:http"),
        ],
        [
            InlineKeyboardButton("📊 Statistics",     callback_data="stats"),
            InlineKeyboardButton("🔄 Refresh Pool",   callback_data="refresh"),
        ],
        [
            InlineKeyboardButton("📥 Export List",    callback_data="export:http"),
        ],
    ])

def list_kb(ptype: str, page: int, total: int) -> InlineKeyboardMarkup:
    max_page = max((total - 1) // PAGE_SIZE, 0)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"list:{ptype}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{max_page+1}", callback_data="noop"))
    if page < max_page:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"list:{ptype}:{page+1}"))

    type_row = [
        InlineKeyboardButton(
            ("✅ " if ptype == t else "") + e,
            callback_data=f"list:{t}:0",
        )
        for t, e in [("http", "🌐"), ("socks5", "🧦"), ("socks4", "🔌")]
    ]

    return InlineKeyboardMarkup([
        type_row,
        nav,
        [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
    ])

def best_kb(ptype: str) -> InlineKeyboardMarkup:
    type_row = [
        InlineKeyboardButton(
            ("✅ " if ptype == t else "") + e + " " + t.upper(),
            callback_data=f"best:{t}",
        )
        for t, e in [("http", "🌐"), ("socks5", "🧦"), ("socks4", "🔌")]
    ]
    return InlineKeyboardMarkup([
        type_row,
        [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
    ])

def export_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 HTTP",   callback_data="export:http"),
            InlineKeyboardButton("🧦 SOCKS5", callback_data="export:socks5"),
            InlineKeyboardButton("🔌 SOCKS4", callback_data="export:socks4"),
        ],
        [InlineKeyboardButton("📦 All Types", callback_data="export:all")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
    ])

# ─────────────────────────────────────────
#  MESSAGE BUILDERS
# ─────────────────────────────────────────
def home_text() -> str:
    http_c   = len(proxy_pool["http"])
    socks5_c = len(proxy_pool["socks5"])
    socks4_c = len(proxy_pool["socks4"])
    total    = http_c + socks5_c + socks4_c
    upd      = format_ts(pool_meta["last_update"])
    status   = "🔄 Updating…" if pool_meta["is_updating"] else "✅ Ready"

    return (
        "╔══════════════════════════════╗\n"
        "║    🛡️  <b>PROXY HUNTER BOT</b>    ║\n"
        "╚══════════════════════════════╝\n\n"
        f"  <b>Status:</b>  {status}\n"
        f"  <b>Updated:</b> {upd}\n\n"
        "──────────────────────────────\n"
        f"  🌐 <b>HTTP</b>   — <code>{http_c:,}</code> proxies\n"
        f"  🧦 <b>SOCKS5</b> — <code>{socks5_c:,}</code> proxies\n"
        f"  🔌 <b>SOCKS4</b> — <code>{socks4_c:,}</code> proxies\n"
        "──────────────────────────────\n"
        f"  📦 <b>Total:</b>  <code>{total:,}</code> live proxies\n\n"
        "👇 <i>Choose an action below</i>"
    )

def list_text(ptype: str, page: int) -> str:
    items = get_sorted(ptype)
    total = len(items)
    start = page * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    emoji = type_emoji(ptype)

    lines = [
        f"{emoji} <b>{ptype.upper()} Proxies</b>  "
        f"[<code>{total:,}</code> total]\n"
        f"<i>Page {page+1} of {max((total-1)//PAGE_SIZE+1, 1)}</i>\n"
        "──────────────────────────────\n"
    ]
    for i, (proxy, data) in enumerate(chunk, start=start + 1):
        lat   = data.get("latency")
        score = data.get("score", 0)
        le    = latency_emoji(lat)
        lat_s = f"{lat:.2f}s" if lat else "—"
        lines.append(
            f"<b>{i}.</b> <code>{proxy}</code>\n"
            f"   {le} <code>{lat_s}</code>  ⭐ <b>{score}</b>\n"
        )

    if not chunk:
        lines.append("⚠️ <i>No proxies available. Try refreshing.</i>")

    return "".join(lines)

def best_text(ptype: str) -> str:
    items = get_sorted(ptype)[:20]
    emoji = type_emoji(ptype)

    lines = [
        f"🏆 <b>TOP 20 {ptype.upper()} Proxies</b> {emoji}\n"
        "──────────────────────────────\n"
    ]
    for rank, (proxy, data) in enumerate(items, 1):
        lat   = data.get("latency")
        score = data.get("score", 0)
        le    = latency_emoji(lat)
        lat_s = f"{lat:.2f}s" if lat else "—"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"<b>{rank}.</b>")
        bar   = score_bar(score)
        lines.append(
            f"{medal} <code>{proxy}</code>\n"
            f"   {le} <code>{lat_s}</code>  [{bar}] <b>{score}pts</b>\n"
        )

    if not items:
        lines.append("⚠️ <i>No proxies yet. Refresh the pool first.</i>")

    return "".join(lines)

def random_text(ptype: str) -> str:
    pool  = proxy_pool.get(ptype, {})
    emoji = type_emoji(ptype)
    if not pool:
        return f"⚠️ <b>No {ptype.upper()} proxies available.</b>\nTry refreshing first."

    proxy, data = random.choice(list(pool.items()))
    lat   = data.get("latency")
    score = data.get("score", 0)
    le    = latency_emoji(lat)
    lat_s = f"{lat:.2f}s" if lat else "—"
    bar   = score_bar(score)
    chk   = format_ts(data.get("last_checked", 0))

    return (
        f"🎲 <b>Random {ptype.upper()} Proxy</b> {emoji}\n"
        "──────────────────────────────\n"
        f"  📡 <b>Address:</b>  <code>{proxy}</code>\n"
        f"  {le} <b>Latency:</b>  <code>{lat_s}</code>\n"
        f"  ⭐ <b>Score:</b>    <b>{score}</b>  [{bar}]\n"
        f"  🕐 <b>Checked:</b>  <i>{chk}</i>\n"
        "──────────────────────────────\n"
        f"  <b>Usage:</b>\n"
        f"  <code>--proxy {ptype}://{proxy}</code>"
    )

def stats_text() -> str:
    total = total_count()
    lines = [
        "📊 <b>Pool Statistics</b>\n"
        "══════════════════════════════\n"
    ]

    for ptype in ("http", "socks5", "socks4"):
        pool  = proxy_pool[ptype]
        emoji = type_emoji(ptype)
        count = len(pool)
        if not count:
            lines.append(f"{emoji} <b>{ptype.upper()}</b>  — <i>empty</i>\n")
            continue

        scores   = [d["score"] for d in pool.values()]
        latencies = [d["latency"] for d in pool.values() if d.get("latency") and d["latency"] < 999]
        avg_lat  = sum(latencies) / len(latencies) if latencies else 0
        fast     = sum(1 for l in latencies if l < 1.0)

        lines.append(
            f"{emoji} <b>{ptype.upper()}</b>  [{count:,} proxies]\n"
            f"   ├ Avg score:   <b>{sum(scores)/count:.1f}</b>\n"
            f"   ├ Avg latency: <b>{avg_lat:.2f}s</b>\n"
            f"   ├ Fast (<1s):  <b>{fast:,}</b>\n"
            f"   └ Top score:   <b>{max(scores)}</b>\n"
        )

    upd  = format_ts(pool_meta["last_update"])
    stat = "🔄 Updating…" if pool_meta["is_updating"] else "✅ Idle"
    lines.append(
        "──────────────────────────────\n"
        f"  📦 <b>Total live:</b> <code>{total:,}</code>\n"
        f"  🕐 <b>Last update:</b> <i>{upd}</i>\n"
        f"  ⚙️  <b>Status:</b> {stat}"
    )
    return "".join(lines)

# ─────────────────────────────────────────
#  EXPORT HELPERS
# ─────────────────────────────────────────
def build_export_text(ptype: str) -> str:
    if ptype == "all":
        lines = []
        for pt in ("http", "socks5", "socks4"):
            for proxy in proxy_pool.get(pt, {}):
                lines.append(f"{pt}://{proxy}")
        return "\n".join(lines)
    return "\n".join(proxy_pool.get(ptype, {}).keys())

# ─────────────────────────────────────────
#  HANDLERS
# ─────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        home_text(),
        reply_markup=main_menu_kb(),
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>PROXY HUNTER — Help</b>\n\n"
        "<b>Commands:</b>\n"
        "  /start   — Main menu\n"
        "  /best    — Top 20 HTTP proxies\n"
        "  /random  — Random HTTP proxy\n"
        "  /stats   — Pool statistics\n"
        "  /refresh — Force pool refresh\n"
        "  /export  — Export proxy list\n\n"
        "<b>Proxy Types:</b>\n"
        "  🌐 HTTP   — Standard web proxies\n"
        "  🧦 SOCKS5 — Encrypted tunnel proxies\n"
        "  🔌 SOCKS4 — Legacy SOCKS proxies\n\n"
        "<b>Scoring:</b>\n"
        "  ⚡ < 0.5s  🟢 < 1s  🟡 < 2s  🟠 < 3.5s  🔴 slow\n\n"
        "<i>Pool refreshes automatically every 5 minutes.</i>"
    )
    await update.message.reply_html(text)

async def cmd_best(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(best_text("http"), reply_markup=best_kb("http"))

async def cmd_random(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ptype = "http"
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 HTTP",   callback_data="random:http"),
            InlineKeyboardButton("🧦 SOCKS5", callback_data="random:socks5"),
            InlineKeyboardButton("🔌 SOCKS4", callback_data="random:socks4"),
        ],
        [InlineKeyboardButton("🎲 Reroll",   callback_data=f"random:{ptype}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
    ])
    await update.message.reply_html(random_text(ptype), reply_markup=kb)

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="home")]])
    await update.message.reply_html(stats_text(), reply_markup=kb)

async def cmd_refresh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if pool_meta["is_updating"]:
        await update.message.reply_html("🔄 <b>Already updating…</b> Please wait.")
        return

    msg = await update.message.reply_html(
        "🔄 <b>Starting pool refresh…</b>\n<i>This may take a few minutes.</i>"
    )

    async def progress(text: str):
        try:
            await msg.edit_text(text, parse_mode=ParseMode.HTML)
        except Exception:
            pass

    await run_update(progress_cb=progress)

    await msg.edit_text(
        f"✅ <b>Refresh complete!</b>\n\n"
        f"  🌐 HTTP   <b>{len(proxy_pool['http']):,}</b>\n"
        f"  🧦 SOCKS5 <b>{len(proxy_pool['socks5']):,}</b>\n"
        f"  🔌 SOCKS4 <b>{len(proxy_pool['socks4']):,}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(),
    )

async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "📥 <b>Export Proxy List</b>\nChoose a type to export:",
        reply_markup=export_kb(),
    )

# ─────────────────────────────────────────
#  CALLBACK ROUTER
# ─────────────────────────────────────────
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()

    # ── home ──
    if data == "home":
        await q.edit_message_text(
            home_text(), parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
        )

    # ── noop ──
    elif data == "noop":
        return

    # ── list:type:page ──
    elif data.startswith("list:"):
        _, ptype, page_s = data.split(":")
        page  = int(page_s)
        total = len(proxy_pool.get(ptype, {}))
        await q.edit_message_text(
            list_text(ptype, page),
            parse_mode=ParseMode.HTML,
            reply_markup=list_kb(ptype, page, total),
        )

    # ── best:type ──
    elif data.startswith("best:"):
        _, ptype = data.split(":", 1)
        await q.edit_message_text(
            best_text(ptype),
            parse_mode=ParseMode.HTML,
            reply_markup=best_kb(ptype),
        )

    # ── random:type ──
    elif data.startswith("random:"):
        _, ptype = data.split(":", 1)
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌐 HTTP",   callback_data="random:http"),
                InlineKeyboardButton("🧦 SOCKS5", callback_data="random:socks5"),
                InlineKeyboardButton("🔌 SOCKS4", callback_data="random:socks4"),
            ],
            [InlineKeyboardButton("🎲 Reroll",    callback_data=f"random:{ptype}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
        ])
        await q.edit_message_text(
            random_text(ptype),
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    # ── stats ──
    elif data == "stats":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="home")]])
        await q.edit_message_text(stats_text(), parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── refresh ──
    elif data == "refresh":
        if pool_meta["is_updating"]:
            await q.answer("🔄 Already updating…", show_alert=True)
            return

        await q.edit_message_text(
            "🔄 <b>Refreshing proxy pool…</b>\n<i>This may take a few minutes.</i>",
            parse_mode=ParseMode.HTML,
        )

        async def progress(text: str):
            try:
                await q.edit_message_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass

        await run_update(progress_cb=progress)

        await q.edit_message_text(
            f"✅ <b>Refresh complete!</b>\n\n"
            f"  🌐 HTTP   <b>{len(proxy_pool['http']):,}</b>\n"
            f"  🧦 SOCKS5 <b>{len(proxy_pool['socks5']):,}</b>\n"
            f"  🔌 SOCKS4 <b>{len(proxy_pool['socks4']):,}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(),
        )

    # ── export:type ──
    elif data.startswith("export:"):
        _, ptype = data.split(":", 1)
        content = build_export_text(ptype)
        if not content.strip():
            await q.answer("⚠️ No proxies to export! Refresh first.", show_alert=True)
            return

        label   = "all" if ptype == "all" else ptype
        fname   = f"proxies_{label}_{int(time.time())}.txt"
        encoded = content.encode("utf-8")
        count   = content.count("\n") + 1

        await q.message.reply_document(
            document=encoded,
            filename=fname,
            caption=(
                f"📥 <b>Export: {label.upper()}</b>\n"
                f"  📋 <b>{count:,}</b> proxies\n"
                f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC"
            ),
            parse_mode=ParseMode.HTML,
        )
        # show export menu again
        await q.edit_message_text(
            "📥 <b>Export Proxy List</b>\nChoose a type to export:",
            parse_mode=ParseMode.HTML,
            reply_markup=export_kb(),
        )

# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌  Set BOT_TOKEN env variable first:")
        print("    export BOT_TOKEN=1234567890:AAxxxxxxxxxxxx")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Register commands ──
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("best",    cmd_best))
    app.add_handler(CommandHandler("random",  cmd_random))
    app.add_handler(CommandHandler("stats",   cmd_stats))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
    app.add_handler(CommandHandler("export",  cmd_export))
    app.add_handler(CallbackQueryHandler(on_callback))

    async def post_init(application: Application):
        await application.bot.set_my_commands([
            BotCommand("start",   "🏠 Main menu"),
            BotCommand("best",    "🏆 Top 20 proxies"),
            BotCommand("random",  "🎲 Random proxy"),
            BotCommand("stats",   "📊 Pool statistics"),
            BotCommand("refresh", "🔄 Force refresh"),
            BotCommand("export",  "📥 Export list"),
            BotCommand("help",    "📖 Help & guide"),
        ])
        log.info("Bot commands registered.")
        # kick off the background loop
        asyncio.create_task(background_loop())
        log.info("Background proxy update loop started.")

    app.post_init = post_init

    log.info("🚀 Proxy Hunter Bot is running…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
