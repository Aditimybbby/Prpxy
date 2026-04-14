#!/usr/bin/env python3
# Hyper-fast proxy scraper + checker with feedback — March 2026
# Fixes Windows asyncio errors + shows valid/invalid counts

import asyncio
import aiohttp
import re
import time
import sys
from pathlib import Path
from typing import Set, List, Tuple

# Windows fix: Use Selector loop to reduce ConnectionResetError spam
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Tune these
MAX_CONCURRENT_FETCH = 30
MAX_CONCURRENT_CHECK = 100   # Start low on Windows; try 200-300 on good VPS
CHECK_TIMEOUT = 8            # seconds
TEST_URL = "http://httpbin.org/ip"

# Updated active sources (March 2026 — proxifly, TheSpeedX, free-proxy-list.net, proxyscrape, etc.)
SOURCES = [
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/http/data.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://free-proxy-list.net/",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
]

async def fetch_proxies(session: aiohttp.ClientSession, url: str) -> Set[str]:
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                return set()
            text = await resp.text()
            proxies = re.findall(r'(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d):[0-9]{1,5}', text)
            return set(proxies)
    except Exception:
        return set()

async def check_proxy(
    session: aiohttp.ClientSession,
    proxy: str,
    sem: asyncio.Semaphore
) -> Tuple[str, float, bool]:
    async with sem:
        start = time.monotonic()
        try:
            proxy_url = f"http://{proxy}"
            async with session.get(
                TEST_URL,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT),
                allow_redirects=False
            ) as resp:
                if resp.status in (200, 301, 302):
                    latency = time.monotonic() - start
                    return proxy, latency, True
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionResetError, OSError, Exception):
            pass  # Silent fail for bad proxies
        return proxy, 999.9, False

async def main():
    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        print("Scraping sources... (this may take 10-60s)")
        fetch_tasks = [fetch_proxies(session, url) for url in SOURCES]
        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        all_proxies: Set[str] = set()
        for res in fetch_results:
            if isinstance(res, set):
                all_proxies.update(res)

        proxies = list(all_proxies)
        total = len(proxies)
        print(f"Collected {total:,} unique proxies from sources.")

        if total == 0:
            print("No proxies found — check sources or internet.")
            return

        sem = asyncio.Semaphore(MAX_CONCURRENT_CHECK)
        print(f"Checking {total:,} proxies ({MAX_CONCURRENT_CHECK} concurrent)...")

        valid_count = 0
        invalid_count = 0
        working: List[Tuple[str, float]] = []

        check_tasks = [check_proxy(session, p, sem) for p in proxies]
        for i, future in enumerate(asyncio.as_completed(check_tasks), 1):
            result = await future
            proxy, lat, ok = result

            if ok:
                valid_count += 1
                working.append((proxy, lat))
            else:
                invalid_count += 1

            # Feedback every 500 checks
            if i % 500 == 0 or i == total:
                percent = (valid_count / i) * 100 if i > 0 else 0
                print(f"Progress: {i}/{total} checked | Valid: {valid_count} | Invalid: {invalid_count} | Success: {percent:.1f}%")

        working.sort(key=lambda x: x[1])

        print("\n" + "="*50)
        print(f"FINAL STATS:")
        print(f"Total proxies scraped: {total:,}")
        print(f"Valid/working proxies: {valid_count}")
        print(f"Invalid/failed proxies: {invalid_count}")
        print(f"Success rate: {(valid_count / total * 100) if total > 0 else 0:.1f}%")
        print("="*50)

        if working:
            output_file = Path("working_proxies.txt")
            with output_file.open("w", encoding="utf-8") as f:
                for proxy, lat in working:
                    f.write(f"{proxy}  # {lat:.2f}s\n")
            print(f"Saved {len(working)} working proxies to: {output_file.resolve()} (sorted by speed)")

            print("\nTop 20 fastest working proxies:")
            for p, lat in working[:20]:
                print(f"{p:21} → {lat:.2f}s")
        else:
            print("No working proxies this run. Free proxies die fast — try again later or use paid ones.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")