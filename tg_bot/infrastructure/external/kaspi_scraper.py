from __future__ import annotations

import asyncio
import re
from typing import List, Optional
from urllib.parse import quote_plus

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from core.logger import get_logger
from domain.entities.product import Product

logger = get_logger(__name__)

KASPI_SEARCH_URL = "https://kaspi.kz/shop/search/?text={query}&page=1"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
}


class ScraperError(Exception):
    pass


class KaspiScraper:
    def __init__(
        self,
        timeout: int = 60,
        max_retries: int = 3,
        max_results: int = 10,
    ) -> None:
        self._timeout = timeout * 1000
        self._max_retries = max_retries
        self._max_results = max_results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def scrape(
        self,
        query: str,
        budget: Optional[float] = None,
    ) -> List[Product]:
        async with async_playwright() as pw:
            browser: Browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context: BrowserContext = await browser.new_context(
                extra_http_headers=_HEADERS,
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
            )
            try:
                page: Page = await context.new_page()
                url = KASPI_SEARCH_URL.format(query=quote_plus(query))
                logger.info("scraper.navigating", url=url)

                await page.goto(url, timeout=self._timeout, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                products = await self._parse_products(page, budget)
                logger.info("scraper.done", count=len(products), query=query)
                return products
            except Exception as exc:
                logger.error("scraper.error", error=str(exc), query=query)
                raise ScraperError(f"Scraping failed: {exc}") from exc
            finally:
                await context.close()
                await browser.close()

    async def _parse_products(
        self,
        page: Page,
        budget: Optional[float],
    ) -> List[Product]:
        products: List[Product] = []

        cards = await page.query_selector_all(".item-card")
        if not cards:
            cards = await page.query_selector_all("[data-test='product-card']")

        for card in cards[: self._max_results * 2]:
            try:
                product = await self._parse_card(page, card)
                if product is None:
                    continue
                if budget is not None and product.price > budget:
                    continue
                products.append(product)
                if len(products) >= self._max_results:
                    break
            except Exception as exc:
                logger.warning("scraper.card_parse_error", error=str(exc))
                continue

        return products

    async def _parse_card(self, page: Page, card) -> Optional[Product]:
        title_el = await card.query_selector(".item-card__name")
        if not title_el:
            title_el = await card.query_selector("[data-test='product-card-name']")
        if not title_el:
            return None
        title = (await title_el.inner_text()).strip()

        price_el = await card.query_selector(".item-card__prices-price")
        if not price_el:
            price_el = await card.query_selector("[data-test='product-price']")
        if not price_el:
            return None
        price_raw = (await price_el.inner_text()).strip()
        price = self._parse_price(price_raw)
        if price is None:
            return None

        link_el = await card.query_selector("a.item-card__name-link")
        if not link_el:
            link_el = await card.query_selector("a[href*='/shop/p/']")
        url = ""
        if link_el:
            href = await link_el.get_attribute("href")
            url = f"https://kaspi.kz{href}" if href and href.startswith("/") else (href or "")

        image_el = await card.query_selector("img.item-card__image")
        image_url: Optional[str] = None
        if image_el:
            image_url = await image_el.get_attribute("src")

        rating_el = await card.query_selector(".item-card__rating span")
        rating: Optional[float] = None
        if rating_el:
            try:
                rating = float((await rating_el.inner_text()).strip())
            except ValueError:
                pass

        reviews_el = await card.query_selector(".item-card__rating-count")
        reviews_count: Optional[int] = None
        if reviews_el:
            try:
                reviews_raw = (await reviews_el.inner_text()).strip()
                reviews_count = int(re.sub(r"\D", "", reviews_raw))
            except (ValueError, AttributeError):
                pass

        return Product.from_scrape(
            title=title,
            price=price,
            url=url,
            source="kaspi",
            image_url=image_url,
            rating=rating,
            reviews_count=reviews_count,
        )

    @staticmethod
    def _parse_price(raw: str) -> Optional[float]:
        cleaned = re.sub(r"[^\d]", "", raw)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
