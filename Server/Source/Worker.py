import asyncio
import random
import json
import os
from playwright.async_api import async_playwright

COOKIE_FILE = "cookies.json"


class PlaywrightWorker:
    def __init__(self, site_cfg):
        self.cfg = site_cfg
        self.search_cfg = site_cfg["search_config"]

    async def execute(self, search_text):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.cfg.get("settings", {}).get("headless", True)
            )

            context = await self._create_context(browser)

            page = await context.new_page()

            await self._apply_stealth(page)

            await page.mouse.move(50, 50, steps=10)

            await page.goto(self.cfg["url"], wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(500, 1200))

            method = self.search_cfg.get("method")

            if method == "form_fill":
                await self._handle_form_fill(page, search_text)

            pages_html = [await page.content()]

            max_pages = self.search_cfg.get("pagination", {}).get("max_pages", 1)
            if max_pages:
                pages_html += await self._handle_pagination(page, max_pages)

            await context.storage_state(path=COOKIE_FILE)

            await browser.close()
            return pages_html

    async def _create_context(self, browser):
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        if os.path.exists(COOKIE_FILE):
            return await browser.new_context(
                user_agent=ua,
                viewport={"width": 1280, "height": 720},
                storage_state=COOKIE_FILE
            )

        return await browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 720}
        )

    async def _apply_stealth(self, page):
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

    async def _handle_form_fill(self, page, search_text):
        cfg = self.search_cfg

        await page.wait_for_selector(cfg["input_selector"], state="visible")
        await asyncio.sleep(random.uniform(0.3, 0.8))

        await page.type(cfg["input_selector"], search_text,
                        delay=random.randint(60, 150))

        await asyncio.sleep(random.uniform(0.2, 1.0))

        if cfg.get("aspnet") and cfg.get("submit_method") == "postback":
            try:
                await page.click(cfg["submit_selector"], delay=random.randint(50, 150))
            except:
                target = cfg["postback_target"]
                await page.evaluate(f"__doPostBack('{target}', '')")

        else:
            await page.click(cfg["submit_selector"], delay=random.randint(50, 150))

        await asyncio.sleep(random.uniform(1.0, 2.0))
        await page.wait_for_load_state("domcontentloaded")

    async def _handle_pagination(self, page, max_pages):
        cfg = self.search_cfg["pagination"]
        next_sel = cfg.get("next_selector")
        pages = []

        for _ in range(max_pages - 1):
            try:
                btn = await page.query_selector(next_sel)
                if not btn:
                    break

                await asyncio.sleep(random.uniform(0.8, 1.8))
                await btn.click(delay=random.randint(60, 150))

                await asyncio.sleep(random.uniform(1.0, 2.0))
                await page.wait_for_load_state("domcontentloaded")

                pages.append(await page.content())

            except Exception:
                break

        return pages
