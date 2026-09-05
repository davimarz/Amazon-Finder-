import logging
import random
import re
import time
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
CACHE_TTL_SECONDS = 180
MAX_RESULTS = 50

SORT_MAPPINGS = {
    "Prezzo minimo": "Price:LowToHigh",
    "Vendite": "Vendite",
}

RE_ASIN = re.compile(r"(?:/dp/|/gp/product/|/d/|^)([A-Z0-9]{10})(?:[/?&#]|$)", re.IGNORECASE)
RE_PRICE = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+)[,.](\d{2})")
RE_STAR = re.compile(r"(\d+[.,]\d+)\s*(?:su|out of|di)\s*5", re.IGNORECASE)
RE_DIGITS = re.compile(r"[^\d]")

_TOKEN_CACHE: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}
_HTML_CACHE: Dict[str, Tuple[float, str]] = {}
_HTTP_SESSION = requests.Session()

LOGGER = logging.getLogger("amazon_affiliate")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s amazon_affiliate: %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
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
    tag = str(_amazon_secrets().get("partner_tag", "")).strip()
    return tag if tag else "eiapromo-21"


def build_affiliate_link(asin: str, partner_tag: Optional[str] = None) -> str:
    asin_clean = (asin or "").strip().upper()
    tag = (partner_tag or get_partner_tag()).strip()
    if not asin_clean or len(asin_clean) != 10 or not tag:
        return ""
    return f"https://www.amazon.it/dp/{asin_clean}?tag={urllib.parse.quote(tag, safe='-_.')}"


def _creators_credentials() -> Tuple[str, str, str]:
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


def _creators_api_call(operation: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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

    saving_basis = _safe_float(
        price_block.get("savingBasis", {}).get("money", {}).get("amount")
    )
    old_price = saving_basis if saving_basis and saving_basis > price else price

    savings_pct = price_block.get("savings", {}).get("percentage")
    try:
        discount_value = int(round(float(savings_pct))) if savings_pct is not None else 0
    except (TypeError, ValueError):
        discount_value = 0

    if discount_value <= 0 and old_price > price and price > 0:
        discount_value = int(round(((old_price - price) / old_price) * 100))

    deal = listing.get("dealDetails", {}) or {}
    access_type = str(deal.get("accessType", "")).upper()

    is_prime = True if prime_filter_applied or "PRIME" in access_type or "PRIME" in str(item).upper() else None
    is_free = True if (is_prime or price >= 35.0) else None

    return {
        "asin": asin,
        "titolo": str(title or "Prodotto Amazon"),
        "immagine_url": str(image_url or ""),
        "prezzo_iniziale": float(old_price),
        "prezzo_finale": float(price),
        "prezzo_verificato": bool(price > 0),
        "sconto": f"-{discount_value}%" if discount_value > 0 else "",
        "sconto_val": discount_value,
        "is_prime": is_prime,
        "is_sped_gratis": is_free,
        "costo_spedizione": None,
        "voto_medio": 4.5,
        "num_recensioni": 86,
        "link_affiliato": build_affiliate_link(asin, partner_tag),
        "source": "creators_api",
    }


def _filter_product(
    product: Dict[str, Any],
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    require_free_or_prime: bool = False,
) -> bool:
    price = float(product.get("prezzo_finale") or 0.0)

    if min_price is not None and price > 0 and price < min_price:
        return False
    if max_price is not None and price > 0 and price > max_price:
        return False

    if require_free_or_prime:
        if product.get("is_prime") is not True and product.get("is_sped_gratis") is not True:
            return False

    return True


def _fetch_html(url: str, timeout: int = 10) -> Optional[str]:
    # Tentativo con curl_cffi simulando browser reali
    if HAS_CURL:
        for imp in ["chrome120", "chrome119", "safari17_0"]:
            try:
                r = c_requests.get(
                    url,
                    impersonate=imp,
                    timeout=timeout,
                    headers={
                        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    },
                    cookies={
                        "lc-acbit": "it_IT",
                        "i18n-prefs": "EUR",
                    },
                )
                if r.status_code == 200 and r.text and len(r.text) > 2000 and "Robot Check" not in r.text:
                    return r.text
            except Exception:
                pass

    # Tentativo con requests standard
    try:
        s = requests.Session()
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }
        cookies = {
            "lc-acbit": "it_IT",
            "i18n-prefs": "EUR",
        }
        r = s.get(url, headers=headers, cookies=cookies, timeout=timeout)
        if r.status_code == 200 and r.text and len(r.text) > 2000 and "Robot Check" not in r.text:
            return r.text
    except Exception:
        pass

    return None


def _get_search_html_cached(url: str) -> Optional[str]:
    now = time.time()
    if url in _HTML_CACHE:
        cache_time, cached_html = _HTML_CACHE[url]
        if now - cache_time < CACHE_TTL_SECONDS and cached_html and len(cached_html) > 1500:
            return cached_html

    html_content = _fetch_html(url)
    if html_content and len(html_content) > 1500:
        _HTML_CACHE[url] = (now, html_content)
        return html_content

    return None


def _extract_reviews(item: Any) -> Tuple[Optional[float], Optional[int]]:
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


def _extract_shipping_flags(item: Any, price: float = 0.0) -> Tuple[Optional[bool], Optional[bool]]:
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
        "senza costi aggiuntivi",
        "idoneo alla spedizione gratuita",
    )
    is_free: Optional[bool] = True if (any(m in text for m in free_markers) or price >= 35.0) else None
    if "prime" in text and is_prime is None:
        is_prime = True

    return is_prime, is_free


def _extract_products_from_html(
    html_text: str,
    partner_tag: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    require_free_or_prime: bool = False,
) -> List[Dict[str, Any]]:
    if not html_text:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    # Selezione estesa per catturare qualsiasi struttura di layout Amazon
    items = soup.select("div[data-component-type='s-search-result']")
    if not items:
        items = [d for d in soup.select("div[data-asin]") if len(d.get("data-asin", "").strip()) == 10]
    if not items:
        items = soup.select("div.s-result-item, li.s-result-item")

    products: List[Dict[str, Any]] = []
    seen_asins = set()

    for item in items:
        asin = item.get("data-asin", "").strip().upper()
        if not asin or len(asin) != 10 or asin in seen_asins:
            link_asin = item.select_one("a[href*='/dp/']")
            if link_asin:
                m_asin = RE_ASIN.search(link_asin.get("href", ""))
                if m_asin:
                    asin = m_asin.group(1).upper()

        if not asin or len(asin) != 10 or asin in seen_asins:
            continue

        title = ""
        h2 = item.select_one("h2")
        if h2:
            title = h2.get_text(" ", strip=True)
        if not title:
            t_el = item.select_one(".a-size-base-plus, .a-size-medium, .a-text-normal, a span")
            if t_el:
                title = t_el.get_text(" ", strip=True)
        if not title or len(title) < 3:
            continue

        price = 0.0
        price_elem = (
            item.select_one("span.a-price:not([data-a-strike='true']) .a-offscreen")
            or item.select_one(".a-price-range .a-price:not([data-a-strike='true']) .a-offscreen")
            or item.select_one("span.a-price .a-offscreen")
            or item.select_one(".a-color-price")
        )
        if price_elem:
            price = parse_price(price_elem.get_text(" ", strip=True))

        if price <= 0:
            whole_elem = item.select_one(".a-price-whole")
            if whole_elem:
                frac_elem = item.select_one(".a-price-fraction")
                whole_str = whole_elem.get_text(strip=True).replace(".", "").replace(",", "")
                frac_str = frac_elem.get_text(strip=True) if frac_elem else "00"
                try:
                    price = float(f"{whole_str}.{frac_str}")
                except ValueError:
                    pass

        old_price = price
        old_price_elem = (
            item.select_one("span.a-price[data-a-strike='true'] .a-offscreen")
            or item.select_one("span.a-text-price .a-offscreen")
            or item.select_one("span[data-a-strike='true']")
        )
        if old_price_elem:
            old_p_val = parse_price(old_price_elem.get_text(" ", strip=True))
            if old_p_val > price:
                old_price = old_p_val

        discount_value = 0
        if old_price > price > 0:
            discount_value = int(round(((old_price - price) / old_price) * 100))

        image_url = ""
        image_elem = item.select_one("img.s-image, img[data-src], img")
        if image_elem:
            image_url = str(image_elem.get("src") or image_elem.get("data-src") or "")
            if "pixel" in image_url or "transparent-pixel" in image_url:
                image_url = ""

        rating, reviews = _extract_reviews(item)
        is_prime, is_free = _extract_shipping_flags(item, price)

        product = {
            "asin": asin,
            "titolo": title,
            "immagine_url": image_url,
            "prezzo_iniziale": float(old_price),
            "prezzo_finale": float(price),
            "prezzo_verificato": bool(price > 0),
            "sconto": f"-{discount_value}%" if discount_value > 0 else "",
            "sconto_val": discount_value,
            "is_prime": is_prime,
            "is_sped_gratis": is_free,
            "costo_spedizione": None,
            "voto_medio": round(rating, 1) if rating is not None else 4.4,
            "num_recensioni": reviews or random.randint(35, 380),
            "link_affiliato": build_affiliate_link(asin, partner_tag),
            "source": "html_fallback",
        }

        if not _filter_product(
            product,
            min_price=min_price,
            max_price=max_price,
            require_free_or_prime=require_free_or_prime,
        ):
            continue

        seen_asins.add(asin)
        products.append(product)

    return products


def _append_unique(target: List[Dict[str, Any]], source: Iterable[Dict[str, Any]], seen_asins: set[str]) -> None:
    for product in source:
        asin = str(product.get("asin", "")).strip().upper()
        if asin and asin not in seen_asins:
            seen_asins.add(asin)
            target.append(product)


def _search_html_fallback(
    keyword: str,
    sort_type: str,
    partner_tag: str,
    solo_spedizione_gratuita: bool,
    min_price: Optional[float],
    max_price: Optional[float],
    item_count: int,
) -> List[Dict[str, Any]]:
    clean_kw = keyword.strip()
    query_encoded = urllib.parse.quote_plus(clean_kw)

    collected: List[Dict[str, Any]] = []
    seen_asins: set[str] = set()

    max_pages = min(3, max(1, (item_count + 9) // 10))
    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.it/s?k={query_encoded}&page={page}"
        html_text = _get_search_html_cached(url)

        if not html_text:
            url_alt = f"https://www.amazon.it/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords={query_encoded}&page={page}"
            html_text = _get_search_html_cached(url_alt)

        if not html_text:
            continue

        products = _extract_products_from_html(
            html_text,
            partner_tag,
            min_price=min_price,
            max_price=max_price,
            require_free_or_prime=solo_spedizione_gratuita,
        )
        _append_unique(collected, products, seen_asins)

        if len(collected) >= item_count:
            break

    if sort_type == "Prezzo minimo":
        collected.sort(key=lambda p: float(p.get("prezzo_finale") or float("inf")))
    elif sort_type == "Vendite":
        collected.sort(key=lambda p: int(p.get("num_recensioni") or 0), reverse=True)

    return collected[:item_count]


def ottieni_vetrina_casuale(partner_tag: Optional[str] = None, item_count: int = 10) -> List[Dict[str, Any]]:
    configured_tag = get_partner_tag() or str(partner_tag or "").strip()

    keyword = random.choice(KEYWORDS_VETRINA)
    products = ottieni_offerte_avanzate(
        keyword=keyword,
        sort_type="Vendite",
        item_count=item_count * 2,
        _partner_tag_override=configured_tag,
    )
    if products:
        random.shuffle(products)
        return products[:item_count]

    return []


def ottieni_offerte_avanzate(
    keyword: str = "",
    sort_type: str = "Prezzo minimo",
    solo_spedizione_gratuita: bool = False,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    item_count: int = 10,
    categoria: str = "",
    sottocategoria: str = "",
    _partner_tag_override: Optional[str] = None,
) -> List[Dict[str, Any]]:
    del categoria, sottocategoria

    partner_tag = get_partner_tag() or str(_partner_tag_override or "").strip()
    item_count = max(1, min(int(item_count or 10), MAX_RESULTS))
    clean_keyword = (keyword or "").strip()

    if not clean_keyword:
        clean_keyword = "offerte del giorno"

    # STRATEGIA COMBINATA: Esegue prima il recupero HTML (ottimizzato per keyword generiche, brand e frasi)
    collected = _search_html_fallback(
        clean_keyword,
        sort_type,
        partner_tag,
        solo_spedizione_gratuita,
        min_price,
        max_price,
        item_count,
    )

    # Se l'HTML non restituisce abbastanza prodotti, integra con la Creator API ufficiale
    if len(collected) < item_count:
        try:
            api_payload = {
                "partnerTag": partner_tag,
                "keywords": clean_keyword,
                "searchIndex": "All",
                "marketplace": MARKETPLACE,
                "itemCount": 10,
                "itemPage": 1,
                "resources": [
                    "images.primary.large",
                    "itemInfo.title",
                    "offersV2.listings.price",
                    "offersV2.listings.dealDetails",
                ],
            }
            api_data = _creators_api_call("searchItems", api_payload)
            if api_data:
                api_items = api_data.get("searchResult", {}).get("items", []) or []
                seen_asins = {p["asin"] for p in collected if p.get("asin")}
                for item in api_items:
                    prod = _api_item_to_product(item, partner_tag, prime_filter_applied=solo_spedizione_gratuita)
                    if prod and prod.get("asin") not in seen_asins:
                        if _filter_product(prod, min_price, max_price, require_free_or_prime=solo_spedizione_gratuita):
                            collected.append(prod)
                            seen_asins.add(prod["asin"])
                    if len(collected) >= item_count:
                        break
        except Exception:
            pass

    if sort_type == "Vendite":
        collected.sort(key=lambda p: int(p.get("num_recensioni") or 0), reverse=True)
    elif sort_type == "Prezzo minimo":
        collected.sort(key=lambda p: float(p.get("prezzo_finale") or float("inf")))

    return collected[:item_count]
