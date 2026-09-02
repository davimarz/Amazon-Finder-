import logging
import random
import re
import time
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional

import requests
import streamlit as st
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as c_requests

    HAS_CURL = True
except ImportError:
    c_requests = None
    HAS_CURL = False


MARKETPLACE = "www.amazon.it"
CREATORS_API_BASE = "https://creatorsapi.amazon/catalog/v1"
DEFAULT_EU_TOKEN_URL = "https://api.amazon.co.uk/auth/o2/token"
CACHE_TTL_SECONDS = 120
MAX_CREATORS_PAGES = 10
MAX_RESULTS = 50  # Esportata esplicitamente per risolvere l'ImportError in app.py

# Valori supportati da SearchItems / sortBy.
SORT_MAPPINGS = {
    "Prezzo minimo": "Price:LowToHigh",
    "Popolarità": "Featured",
    "Recensioni": "AvgCustomerReviews",
}

# Parametri del sito Amazon usati come fallback.
SORT_FALLBACK_MAP = {
    "Prezzo minimo": "price-asc-rank",
    "Popolarità": "exact-aware-popularity-rank",
    "Recensioni": "review-rank",
    "Numero di vendite": "exact-aware-popularity-rank",
}

RE_ASIN = re.compile(r"(?:/dp/|/gp/product/|/d/|^)([A-Z0-9]{10})(?:[/?&#]|$)", re.IGNORECASE)
RE_PRICE = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+)[,.](\d{2})")
RE_STAR = re.compile(r"(\d+[.,]\d+)\s*(?:su|out of|di)\s*5", re.IGNORECASE)
RE_DIGITS = re.compile(r"[^\d]")

_TOKEN_CACHE: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}

_HTTP_SESSION = requests.Session()
_CURL_SESSION = c_requests.Session() if HAS_CURL else None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
]

KEYWORDS_VETRINA = [
    "offerte lampo tecnologia",
    "offerte scarpe sneaker",
    "smartwatch offerte del giorno",
    "cuffie bluetooth offerta",
    "elettrodomestici cucina sconti",
    "accessori smartphone offerte",
    "cura della persona sconti",
    "abbigliamento sportivo offerte",
]


def _amazon_secrets() -> Dict[str, Any]:
    try:
        return dict(st.secrets.get("amazon_api", {}))
    except Exception:
        return {}


def get_partner_tag() -> str:
    """Restituisce il tracking ID configurato."""
    return str(_amazon_secrets().get("partner_tag", "")).strip()


def build_affiliate_link(asin: str, partner_tag: Optional[str] = None) -> str:
    """Costruisce sempre un link Amazon.it pulito con tracking ID."""
    asin_clean = (asin or "").strip().upper()
    tag = (partner_tag or get_partner_tag()).strip()
    if not asin_clean or len(asin_clean) != 10 or not tag:
        return ""
    return f"https://www.amazon.it/dp/{asin_clean}?tag={urllib.parse.quote(tag, safe='-_.')}"


def _creators_credentials() -> tuple[str, str, str]:
    cfg = _amazon_secrets()
    client_id = str(cfg.get("client_id") or cfg.get("credential_id") or "").strip()
    client_secret = str(cfg.get("client_secret") or cfg.get("credential_secret") or "").strip()
    token_url = str(cfg.get("token_url") or DEFAULT_EU_TOKEN_URL).strip()
    return client_id, client_secret, token_url


def get_creators_access_token(force_refresh: bool = False) -> Optional[str]:
    now = time.time()
    if (
        not force_refresh
        and _TOKEN_CACHE.get("access_token")
        and now < float(_TOKEN_CACHE.get("expires_at", 0)) - 60
    ):
        return str(_TOKEN_CACHE["access_token"])

    client_id, client_secret, token_url = _creators_credentials()
    if not client_id or not client_secret:
        return None

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "creatorsapi::default",
    }

    try:
        response = _HTTP_SESSION.post(
            token_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        if response.status_code != 200:
            return None

        data = response.json()
        token = data.get("access_token")
        if not token:
            return None

        expires_in = int(data.get("expires_in", 3600))
        _TOKEN_CACHE["access_token"] = token
        _TOKEN_CACHE["expires_at"] = now + max(60, expires_in)
        return str(token)
    except (requests.RequestException, ValueError, TypeError):
        return None


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _creators_api_call(operation: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Chiamata Creators API con cache per pagina e rinnovo token su 401."""
    endpoint = f"{CREATORS_API_BASE}/{operation}"

    for attempt in range(2):
        token = get_creators_access_token(force_refresh=(attempt == 1))
        if not token:
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-marketplace": MARKETPLACE,
        }

        try:
            response = _HTTP_SESSION.post(endpoint, json=payload, headers=headers, timeout=6)
        except requests.RequestException:
            return None

        if response.status_code == 401 and attempt == 0:
            _TOKEN_CACHE["access_token"] = None
            _TOKEN_CACHE["expires_at"] = 0.0
            continue

        if response.status_code != 200:
            return None

        try:
            return response.json()
        except ValueError:
            return None

    return None


def parse_price(text: Any) -> float:
    if text is None:
        return 0.0

    cleaned = str(text).replace("\xa0", " ").replace("&nbsp;", " ").strip()
    match = RE_PRICE.search(cleaned)
    if match:
        whole = match.group(1).replace(".", "")
        frac = match.group(2)
        try:
            value = float(f"{whole}.{frac}")
            return value if value > 0 else 0.0
        except ValueError:
            pass

    integer_match = re.search(r"(\d{1,3}(?:\.\d{3})*|\d+)\s*€", cleaned) or re.search(
        r"€\s*(\d{1,3}(?:\.\d{3})*|\d+)", cleaned
    )
    if integer_match:
        try:
            value = float(integer_match.group(1).replace(".", ""))
            return value if value > 0 else 0.0
        except ValueError:
            pass

    return 0.0


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _api_item_to_product(
    item: Dict[str, Any],
    partner_tag: str,
    prime_filter_applied: bool = False,
) -> Optional[Dict[str, Any]]:
    asin = str(item.get("asin", "")).strip().upper()
    if len(asin) != 10:
        return None

    title = (
        item.get("itemInfo", {})
        .get("title", {})
        .get("displayValue", "Prodotto Amazon")
    )
    image_url = (
        item.get("images", {})
        .get("primary", {})
        .get("large", {})
        .get("url", "")
    )

    listings = item.get("offersV2", {}).get("listings", []) or []
    listing = listings[0] if listings else {}
    price_block = listing.get("price", {}) or {}

    price = _safe_float(price_block.get("money", {}).get("amount")) or 0.0
    if price <= 0:
        return None

    saving_basis = _safe_float(
        price_block.get("savingBasis", {}).get("money", {}).get("amount")
    )
    old_price = saving_basis if saving_basis and saving_basis > price else price

    savings_pct = price_block.get("savings", {}).get("percentage")
    try:
        discount_value = int(round(float(savings_pct))) if savings_pct is not None else 0
    except (TypeError, ValueError):
        discount_value = 0

    if discount_value <= 0 and old_price > price:
        discount_value = int(round(((old_price - price) / old_price) * 100))

    deal = listing.get("dealDetails", {}) or {}
    access_type = str(deal.get("accessType", "")).upper()
    is_prime = True if prime_filter_applied or "PRIME" in access_type else None

    return {
        "asin": asin,
        "titolo": str(title or "Prodotto Amazon"),
        "immagine_url": str(image_url or ""),
        "prezzo_iniziale": float(old_price),
        "prezzo_finale": float(price),
        "prezzo_verificato": True,
        "sconto": f"-{discount_value}%" if discount_value > 0 else "",
        "sconto_val": discount_value,
        "is_prime": is_prime,
        "is_sped_gratis": None,
        "costo_spedizione": None,
        "voto_medio": None,
        "num_recensioni": None,
        "link_affiliato": build_affiliate_link(asin, partner_tag),
        "source": "creators_api",
    }


def _filter_product(
    product: Dict[str, Any],
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    require_free_or_prime: bool = False,
) -> bool:
    price = float(product.get("prezzo_finale") or 0.0)
    discount = int(product.get("sconto_val") or 0)

    if price <= 0:
        return False
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    if discount < min_discount or discount > max_discount:
        return False

    if require_free_or_prime:
        if product.get("is_prime") is not True and product.get("is_sped_gratis") is not True:
            return False

    return True


def _fetch_html(url: str, timeout: int = 6) -> Optional[str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    cookies = {
        "lc-acbit": "it_IT",
        "i18n-prefs": "EUR",
        "sp-cdn": "L5Z9:IT",
    }

    if _CURL_SESSION is not None:
        try:
            response = _CURL_SESSION.get(url, headers=headers, cookies=cookies, timeout=timeout, impersonate="chrome")
            if (
                response.status_code == 200
                and response.text
                and len(response.text) > 1500
                and "Robot Check" not in response.text
            ):
                return response.text
        except Exception:
            pass

    try:
        response = _HTTP_SESSION.get(url, headers=headers, cookies=cookies, timeout=timeout)
        if (
            response.status_code == 200
            and response.text
            and len(response.text) > 1500
            and "Robot Check" not in response.text
        ):
            return response.text
    except requests.RequestException:
        pass

    return None


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_html_cached(url: str) -> Optional[str]:
    return _fetch_html(url, timeout=6)


def _extract_reviews(item: Any) -> tuple[Optional[float], Optional[int]]:
    rating: Optional[float] = None
    reviews: Optional[int] = None

    star_element = (
        item.select_one("i.a-icon-star-small span.a-icon-alt")
        or item.select_one("i.a-icon-star span.a-icon-alt")
        or item.select_one("span.a-icon-alt")
    )
    if star_element:
        match = RE_STAR.search(star_element.get_text(" ", strip=True))
        if match:
            try:
                rating = float(match.group(1).replace(",", "."))
            except ValueError:
                rating = None

    review_element = (
        item.select_one("span.a-size-base.s-underline-text")
        or item.select_one("a[href*='customerReviews'] span")
        or item.select_one("a[href*='#customerReviews'] span")
    )
    if review_element:
        digits = RE_DIGITS.sub("", review_element.get_text(strip=True))
        if digits:
            try:
                reviews = int(digits)
            except ValueError:
                reviews = None

    return rating, reviews


def _extract_shipping_flags(item: Any) -> tuple[Optional[bool], Optional[bool]]:
    prime_selector = (
        "i.a-icon-prime, span.a-icon-prime, "
        "[aria-label='Amazon Prime'], img[alt*='Prime'], img[alt*='prime']"
    )
    is_prime: Optional[bool] = True if item.select_one(prime_selector) else None

    text = item.get_text(" ", strip=True).lower()
    free_markers = (
        "spedizione gratuita",
        "consegna gratuita",
        "spedizione gratis",
        "consegna gratis",
    )
    is_free: Optional[bool] = True if any(marker in text for marker in free_markers) else None
    return is_prime, is_free


def _extract_products_from_html(
    html_text: str,
    partner_tag: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_discount: int = 0,
    max_discount: int = 100,
    require_free_or_prime: bool = False,
) -> List[Dict[str, Any]]:
    if not html_text:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    items = soup.find_all("div", {"data-component-type": "s-search-result"})
    if not items:
        items = [
            div
            for div in soup.find_all("div", attrs={"data-asin": True})
            if len(div.get("data-asin", "").strip()) == 10
        ]

    products: List[Dict[str, Any]] = []
    seen_asins = set()

    for item in items:
        asin = item.get("data-asin", "").strip().upper()
        if len(asin) != 10 or asin in seen_asins:
            continue

        title_element = item.select_one("h2 span") or item.find("h2")
        if not title_element:
            continue
        title = title_element.get_text(" ", strip=True)

        price_element = (
            item.select_one("span.a-price:not([data-a-strike='true']) span.a-offscreen")
            or item.select_one(".a-price span.a-offscreen")
            or item.select_one(".a-color-price")
        )
        price = parse_price(price_element.get_text(" ", strip=True)) if price_element else 0.0
        if price <= 0:
            continue

        old_price_element = (
            item.select_one("span.a-price[data-a-strike='true'] span.a-offscreen")
            or item.select_one("span.a-text-price span.a-offscreen")
        )
        old_price = parse_price(old_price_element.get_text(" ", strip=True)) if old_price_element else price
        if old_price < price:
            old_price = price

        discount_value = 0
        if old_price > price:
            discount_value = int(round(((old_price - price) / old_price) * 100))

        image_url = ""
        image_element = item.select_one("img.s-image") or item.find("img")
        if image_element:
            image_url = str(image_element.get("src") or image_element.get("data-src") or "")

        rating, reviews = _extract_reviews(item)
        is_prime, is_free = _extract_shipping_flags(item)

        product = {
            "asin": asin,
            "titolo": title,
            "immagine_url": image_url,
            "prezzo_iniziale": float(old_price),
            "prezzo_finale": float(price),
            "prezzo_verificato": True,
            "sconto": f"-{discount_value}%" if discount_value > 0 else "",
            "sconto_val": discount_value,
            "is_prime": is_prime,
            "is_sped_gratis": is_free,
            "costo_spedizione": None,
            "voto_medio": round(rating, 1) if rating is not None else None,
            "num_recensioni": reviews,
            "link_affiliato": build_affiliate_link(asin, partner_tag),
            "source": "html_fallback",
        }

        if not _filter_product(
            product,
            min_price,
            max_price,
            min_discount,
            max_discount,
            require_free_or_prime=require_free_or_prime,
        ):
            continue

        seen_asins.add(asin)
        products.append(product)

    return products


def _append_unique(target: List[Dict[str, Any]], source: Iterable[Dict[str, Any]], seen_asins: set[str], seen_titles: set[str]) -> None:
    for product in source:
        asin = str(product.get("asin", "")).strip().upper()
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', str(product.get("titolo", "")).lower())[:50]
        if asin and (asin not in seen_asins) and (clean_title not in seen_titles):
            seen_asins.add(asin)
            seen_titles.add(clean_title)
            target.append(product)


def _get_item_from_creators_api(
    asin: str,
    partner_tag: str,
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    require_free_or_prime: bool = False,
) -> Optional[Dict[str, Any]]:
    payload = {
        "itemIds": [asin],
        "itemIdType": "ASIN",
        "marketplace": MARKETPLACE,
        "partnerTag": partner_tag,
        "languagesOfPreference": ["it_IT"],
        "currencyOfPreference": "EUR",
        "resources": [
            "images.primary.large",
            "itemInfo.title",
            "offersV2.listings.price",
            "offersV2.listings.dealDetails",
        ],
    }
    data = _creators_api_call("getItems", payload)
    if not data:
        return None

    items = data.get("itemsResult", {}).get("items", []) or []
    if not items:
        return None

    product = _api_item_to_product(items[0], partner_tag, prime_filter_applied=False)
    if not product:
        return None

    if not _filter_product(
        product,
        min_price,
        max_price,
        min_discount,
        max_discount,
        require_free_or_prime=require_free_or_prime,
    ):
        return None
    return product


def _search_creators_api(
    keyword: str,
    sort_type: str,
    partner_tag: str,
    solo_spedizione_gratuita: bool,
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    item_count: int,
) -> Optional[List[Dict[str, Any]]]:
    if not get_creators_access_token():
        return None

    sort_value = SORT_MAPPINGS.get(sort_type) or SORT_MAPPINGS.get(
        "Popolarità" if sort_type == "Numero di vendite" else sort_type,
        "Featured",
    )

    collected: List[Dict[str, Any]] = []
    seen_asins: set[str] = set()
    seen_titles: set[str] = set()

    for page in range(1, MAX_CREATORS_PAGES + 1):
        payload: Dict[str, Any] = {
            "partnerTag": partner_tag,
            "keywords": keyword,
            "searchIndex": "All",
            "marketplace": MARKETPLACE,
            "languagesOfPreference": ["it_IT"],
            "currencyOfPreference": "EUR",
            "itemCount": 10,
            "itemPage": page,
            "sortBy": sort_value,
            "resources": [
                "images.primary.large",
                "itemInfo.title",
                "offersV2.listings.price",
                "offersV2.listings.dealDetails",
            ],
        }

        if min_price is not None:
            payload["minPrice"] = max(1, int(round(min_price * 100)))
        if max_price is not None:
            payload["maxPrice"] = max(1, int(round(max_price * 100)))
        if min_discount > 0:
            payload["minSavingPercent"] = min(99, int(min_discount))
        if solo_spedizione_gratuita:
            payload["deliveryFlags"] = ["Prime"]

        data = _creators_api_call("searchItems", payload)
        if data is None:
            return None if not collected else collected

        items = data.get("searchResult", {}).get("items", []) or []
        if not items:
            break

        parsed_page: List[Dict[str, Any]] = []
        for item in items:
            product = _api_item_to_product(
                item,
                partner_tag,
                prime_filter_applied=solo_spedizione_gratuita,
            )
            if not product:
                continue
            if _filter_product(product, min_price, max_price, min_discount, max_discount):
                parsed_page.append(product)

        _append_unique(collected, parsed_page, seen_asins, seen_titles)
        if len(collected) >= item_count:
            break

        if len(items) < 10:
            break

    return collected[:item_count]


def _search_html_fallback(
    keyword: str,
    sort_type: str,
    partner_tag: str,
    solo_spedizione_gratuita: bool,
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    item_count: int,
) -> List[Dict[str, Any]]:
    query_encoded = urllib.parse.quote_plus(keyword)
    sort_param = SORT_FALLBACK_MAP.get(sort_type, "exact-aware-popularity-rank")

    collected: List[Dict[str, Any]] = []
    seen_asins: set[str] = set()
    seen_titles: set[str] = set()

    max_pages = min(10, max(1, (item_count + 9) // 10 + 2))
    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.it/s?k={query_encoded}&page={page}&s={sort_param}"
        html_text = _fetch_html_cached(url)
        if not html_text:
            url = f"https://www.amazon.it/s?k={query_encoded}&page={page}"
            html_text = _fetch_html_cached(url)
        if not html_text:
            continue

        products = _extract_products_from_html(
            html_text,
            partner_tag,
            min_price=min_price,
            max_price=max_price,
            min_discount=min_discount,
            max_discount=max_discount,
            require_free_or_prime=solo_spedizione_gratuita,
        )
        _append_unique(collected, products, seen_asins, seen_titles)

        if len(collected) >= item_count:
            break

    if sort_type == "Prezzo minimo":
        collected.sort(key=lambda product: float(product.get("prezzo_finale") or 0.0))

    return collected[:item_count]


def ottieni_vetrina_casuale(partner_tag: Optional[str] = None, item_count: int = 10) -> List[Dict[str, Any]]:
    configured_tag = get_partner_tag() or str(partner_tag or "").strip()
    if not configured_tag:
        return []

    keyword = random.choice(KEYWORDS_VETRINA)
    products = ottieni_offerte_avanzate(
        keyword=keyword,
        sort_type="Popolarità",
        min_discount=5,
        item_count=item_count * 2,
        _partner_tag_override=configured_tag,
    )
    if products:
        random.shuffle(products)
        return products[:item_count]

    fallback = ottieni_offerte_avanzate(
        keyword="offerte del giorno",
        sort_type="Popolarità",
        min_discount=0,
        item_count=item_count * 2,
        _partner_tag_override=configured_tag,
    )
    if fallback:
        random.shuffle(fallback)
        return fallback[:item_count]
    return []


def ottieni_offerte_avanzate(
    keyword: str = "",
    sort_type: str = "Prezzo minimo",
    solo_spedizione_gratuita: bool = False,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_discount: int = 0,
    max_discount: int = 100,
    item_count: int = 10,
    categoria: str = "",
    sottocategoria: str = "",
    _partner_tag_override: Optional[str] = None,
) -> List[Dict[str, Any]]:
    del categoria, sottocategoria

    partner_tag = get_partner_tag() or str(_partner_tag_override or "").strip()
    if not partner_tag:
        return []

    item_count = max(1, min(int(item_count or 10), MAX_RESULTS))
    min_discount = max(0, min(int(min_discount or 0), 100))
    max_discount = max(min_discount, min(int(max_discount or 100), 100))

    clean_keyword = (keyword or "").strip()
    asin_match = RE_ASIN.search(clean_keyword)

    if asin_match and ("http" in clean_keyword.lower() or len(clean_keyword) == 10):
        asin = asin_match.group(1).upper()
        api_product = _get_item_from_creators_api(
            asin,
            partner_tag,
            min_price,
            max_price,
            min_discount,
            max_discount,
            require_free_or_prime=solo_spedizione_gratuita,
        )
        if api_product:
            return [api_product]

        fallback_products = _search_html_fallback(
            asin,
            "Popolarità",
            partner_tag,
            solo_spedizione_gratuita,
            min_price,
            max_price,
            min_discount,
            max_discount,
            10,
        )
        for product in fallback_products:
            if product.get("asin") == asin:
                return [product]
        return []

    query = clean_keyword or "offerte del giorno"

    api_products = _search_creators_api(
        query,
        sort_type,
        partner_tag,
        solo_spedizione_gratuita,
        min_price,
        max_price,
        min_discount,
        max_discount,
        item_count,
    )
    if api_products is not None:
        return api_products[:item_count]

    return _search_html_fallback(
        query,
        sort_type,
        partner_tag,
        solo_spedizione_gratuita,
        min_price,
        max_price,
        min_discount,
        max_discount,
        item_count,
    )
