import asyncio
from playwright.async_api import async_playwright

class PlaywrightWorker:
    def __init__(self, site_cfg):
        self.cfg = site_cfg
        self.search_cfg = site_cfg["search_config"]

    async def execute(self, search_text):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.cfg.get("settings", {}).get("headless", True))
            page = await browser.new_page()

            await page.goto(self.cfg["url"], wait_until="domcontentloaded")

            method = self.search_cfg.get("method")

            if method == "form_fill":
                await self._handle_form_fill(page, search_text)

            pages_html = [await page.content()]

            max_pages = self.search_cfg.get("pagination", {}).get("max_pages", 1)

            if max_pages:
                pages_html += await self._handle_pagination(page, max_pages)

            await browser.close()
            return pages_html


    async def _handle_form_fill(self, page, search_text):
        cfg = self.search_cfg

        await page.fill(cfg["input_selector"], search_text)

        if cfg.get("aspnet") and cfg.get("submit_method") == "postback":
            target = cfg["postback_target"]
            await page.evaluate(f"__doPostBack('{target}', '')")
            await page.wait_for_load_state("networkidle")
        else:
            await page.click(cfg["submit_selector"])
            await page.wait_for_load_state("networkidle")


    async def _handle_pagination(self, page, max_pages):
        cfg = self.search_cfg["pagination"]
        next_sel = cfg.get("next_selector")
        pages = []

        for _ in range(max_pages - 1):
            try:
                btn = await page.query_selector(next_sel)
                if not btn:
                    break

                await btn.click()
                await page.wait_for_load_state("networkidle")

                pages.append(await page.content())

            except Exception:
                break

        return pages
