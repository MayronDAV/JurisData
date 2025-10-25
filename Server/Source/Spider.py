import scrapy
from scrapy_playwright.page import PageMethod
import re
from urllib.parse import urljoin
import hashlib



class Spider(scrapy.Spider):
    name = "Spider"

    def __init__(self, start_urls=None, config=None, search_term=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.config = config or {}
        self.search_term = search_term or None

    async def start(self):
        self.logger.info(f"[DEBUG] Iniciando spider com search_term: {self.search_term}")
        self.logger.info(f"[DEBUG] Start URLs: {self.start_urls}")
        self.logger.info(f"[DEBUG] Sites configurados: {list(self.config.get('sites', {}).keys())}")

        yield scrapy.Request("https://example.com")

    def parse(self, response):
        yield {
            "documentos": [
                {"docTitulo": "Titulo 1.1", "docTexto": "Texto 1.1"},
                {"docTitulo": "Titulo 1.2", "docTexto": "Texto 1.2"}
            ]
        }
