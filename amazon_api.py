"""Accesso ai prodotti Amazon per l'app Streamlit.

Priorità: Creators API. Il fallback HTML è usato solo per scoprire prodotti e
costruire il link affiliato; non pubblica prezzi/sconti/spedizione come dati
verificati quando la Creators API non è disponibile.
"""

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
OFFERS_CACHE_TTL_SECONDS = 15 * 60
METADATA_CACHE_TTL_SECONDS = 24 * 60 * 60
VETRINA_CACHE_TTL_SECONDS = 15 * 60
MAX_RESULTS = 50
MAX_CREATORS_PAGES = 5  # 10 item/pagina -> massimo 50 risultati
HTTP_TIMEOUT_SECONDS = 6
RETRY_BACKOFF_SECONDS = 0.35

SORT_MAPPINGS = {
    "Prezzo minimo": "Price:LowToHigh",
    "Popolarità": "Featured",
    "Recensioni": "AvgCustomerReviews",
}

SORT_FALLBACK_MAP = {
    "Prezzo minimo": "price-asc-rank",
    "Popolarità": "exact-aware-popularity-rank",
    "Recensioni": "review-rank",
    "Numero di vendite": "exact-aware-popularity-rank",  # compatibilità legacy
}

RE_ASIN = re.compile(r"(?:/dp/|/gp/product/|/d/|^)([A-Z0-9]{10})(?:[/?&#]|$)", re.IGNORECASE)
_TOKEN_CACHE: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}
_HTTP_SESSION = requests.Session()
_CURL_SESSION = c_requests.Session() if HAS_CURL else None

LOGGER = logging.getLogger("amazon_affiliate")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s amazon_affiliate: %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

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
    """Restituisce il tracking ID configurato; nessun ID è hardcoded."""
    return str(_amazon_secrets().get("partner_tag", "")).strip()


def build_affiliate_link(asin: str, partner_tag: Optional[str] = None) -> str:
    """Costruisce un link Amazon.it canonico con tracking ID."""
    asin_clean = (asin or "").strip().upper()
    tag = (partner_tag or get_partner_tag()).strip()
    if len(asin_clean) != 10 or not tag:
        return ""
    safe_tag = urllib.parse.quote(tag, safe="-_.")
    return f"https://www.amazon.it/dp/{asin_clean}?tag={safe_tag}"


def _creators_credentials() -> tuple[str, str, str]:
    cfg = _amazon_secrets()
    client_id = str(cfg.get("client_id") or cfg.get("credential_id") or "").strip()
    client_secret = str(cfg.get("client_secret") or cfg.get("credential_secret") or "").strip()
    token_url = str(cfg.get("token_url") or DEFAULT_EU_TOKEN_URL).strip()
    return client_id, client_secret, token_url


def _transient_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


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
        LOGGER.warning("Creators API non configurata: credenziali mancanti")
        return None

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "creatorsapi::default",
    }

    for attempt in range(2):
        try:
            response = _HTTP_SESSION.post(
                token_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            LOGGER.warning("Token OAuth: errore rete %s", type(exc).__name__)
            if attempt == 0:
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            return None

        if response.status_code == 200:
            try:
                data = response.json()
                token = data.get("access_token")
                if not token:
                    LOGGER.warning("Token OAuth: risposta senza access_token")
                    return None
                expires_in = int(data.get("expires_in", 3600))
                _TOKEN_CACHE["access_token"] = token
                _TOKEN_CACHE["expires_at"] = now + max(60, expires_in)
                return str(token)
            except (ValueError, TypeError):
                LOGGER.warning("Token OAuth: risposta JSON non valida")
                return None

        LOGGER.warning("Token OAuth: HTTP %s", response.status_code)
        if _transient_status(response.status_code) and attempt == 0:
            time.sleep(RETRY_BACKOFF_SECONDS)
            continue
        return None

    return None


@st.cache_data(ttl=OFFERS_CACHE_TTL_SECONDS, show_spinner=False)
def _creators_api_call(operation: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Chiamata Creators API cache-ata con retry limitato e refresh su 401."""
    endpoint = f"{CREATORS_API_BASE}/{operation}"
    token = get_creators_access_token()
    if not token:
        return None

    transient_retry_used = False
    auth_refresh_used = False

    while True:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-marketplace": MARKETPLACE,
        }
        try:
            response = _HTTP_SESSION.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            LOGGER.warning("Creators API %s: errore rete %s", operation, type(exc).__name__)
            if not transient_retry_used:
                transient_retry_used = True
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            return None

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                LOGGER.warning("Creators API %s: JSON non valido", operation)
                return None

        if response.status_code == 401 and not auth_refresh_used:
            LOGGER.warning("Creators API %s: 401, rinnovo token", operation)
            auth_refresh_used = True
            _TOKEN_CACHE["access_token"] = None
            _TOKEN_CACHE["expires_at"] = 0.0
            token = get_creators_access_token(force_refresh=True)
            if not token:
                return None
            continue

        LOGGER.warning("Creators API %s: HTTP %s", operation, response.status_code)
        if _transient_status(response.status_code) and not transient_retry_used:
            transient_retry_used = True
            time.sleep(RETRY_BACKOFF_SECONDS)
            continue
        return None


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

    title = item.get("itemInfo", {}).get("title", {}).get("displayValue", "Prodotto Amazon")
    image_url = item.get("images", {}).get("primary", {}).get("large", {}).get("url", "")

    listings = item.get("offersV2", {}).get("listings", []) or []
    listing = listings[0] if listings else {}
    price_block = listing.get("price", {}) or {}
    price = _safe_float(price_block.get("money", {}).get("amount")) or 0.0
    if price <= 0:
        return None

    saving_basis = _safe_float(price_block.get("savingBasis", {}).get("money", {}).get("amount"))
    old_price = saving_basis if saving_basis and saving_basis > price else price

    savings_pct = price_block.get("savings", {}).get("percentage")
    try:
        discount = int(round(float(savings_pct))) if savings_pct is not None else 0
    except (TypeError, ValueError):
        discount = 0
    if discount <= 0 and old_price > price:
        discount = int(round(((old_price - price) / old_price) * 100))

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
        "sconto": f"-{discount}%" if discount > 0 else "",
        "sconto_val": discount,
        "is_prime": is_prime,
        "is_sped_gratis": None,
        "costo_spedizione": None,
        "voto_medio": None,
        "num_recensioni": None,
        "link_affiliato": build_affiliate_link(asin, partner_tag),
        "source": "creators_api",
        "rilevato_il": int(time.time()),
    }


def _filter_verified_product(
    product: Dict[str, Any],
    min_price: Optional[float],
    max_price: Optional[float],
    min_discount: int,
    max_discount: int,
    require_free_or_prime: bool = False,
) -> bool:
    if product.get("prezzo_verificato") is not True:
        return False
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
    if require_free_or_prime and product.get("is_prime") is not True and product.get("is_sped_gratis") is not True:
        return False
    return True


# ------------------------- FALLBACK METADATI -----------------------------
def _fetch_html(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> Optional[str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    cookies = {"lc-acbit": "it_IT", "i18n-prefs": "EUR", "sp-cdn": "L5Z9:IT"}

    # curl_cffi è il client preferito; requests è fallback. Nessun loop aggressivo.
    if _CURL_SESSION is not None:
        for attempt in range(2):
            try:
                response = _CURL_SESSION.get(
                    url,
                    headers=headers,
                    cookies=cookies,
                    timeout=timeout,
                    impersonate="chrome",
                )
                if response.status_code == 200 and response.text and len(response.text) > 1500 and "Robot Check" not in response.text:
                    return response.text
                if not _transient_status(int(response.status_code)):
                    break
            except Exception as exc:
                LOGGER.info("Fallback HTML curl: %s", type(exc).__name__)
            if attempt == 0:
                time.sleep(RETRY_BACKOFF_SECONDS)

    for attempt in range(2):
        try:
            response = _HTTP_SESSION.get(url, headers=headers, cookies=cookies, timeout=timeout)
            if response.status_code == 200 and response.text and len(response.text) > 1500 and "Robot Check" not in response.text:
                return response.text
            LOGGER.info("Fallback HTML requests: HTTP %s", response.status_code)
            if not _transient_status(response.status_code):
                break
        except requests.RequestException as exc:
            LOGGER.info("Fallback HTML requests: %s", type(exc).__name__)
        if attempt == 0:
            time.sleep(RETRY_BACKOFF_SECONDS)
    return None


@st.cache_data(ttl=METADATA_CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_html_cached(url: str) -> Optional[str]:
    return _fetch_html(url)


def _extract_metadata_from_html(html_text: str, partner_tag: str) -> List[Dict[str, Any]]:
    """Estrae solo metadati stabili; nessun prezzo/sconto/spedizione viene pubblicato."""
    if not html_text:
        return []
    soup = BeautifulSoup(html_text, "html.parser")
    items = soup.find_all("div", {"data-component-type": "s-search-result"})
    if not items:
        items = [
            div for div in soup.find_all("div", attrs={"data-asin": True})
            if len(div.get("data-asin", "").strip()) == 10
        ]

    products: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        asin = item.get("data-asin", "").strip().upper()
        if len(asin) != 10 or asin in seen:
            continue
        title_element = item.select_one("h2 span") or item.find("h2")
        if not title_element:
            continue
        title = title_element.get_text(" ", strip=True)
        image_element = item.select_one("img.s-image") or item.find("img")
        image_url = str(image_element.get("src") or image_element.get("data-src") or "") if image_element else ""
        seen.add(asin)
        products.append({
            "asin": asin,
            "titolo": title,
            "immagine_url": image_url,
            "prezzo_iniziale": None,
            "prezzo_finale": None,
            "prezzo_verificato": False,
            "sconto": "",
            "sconto_val": None,
            "is_prime": None,
            "is_sped_gratis": None,
            "costo_spedizione": None,
            "voto_medio": None,
            "num_recensioni": None,
            "link_affiliato": build_affiliate_link(asin, partner_tag),
            "source": "html_fallback_metadata",
            "rilevato_il": int(time.time()),
        })
    return products


# Alias legacy: mantiene compatibilità ma ora restituisce solo metadati non dinamici.
def _estrai_prodotti_da_html(html_text: str, partner_tag: str, **_: Any) -> List[Dict[str, Any]]:
    return _extract_metadata_from_html(html_text, partner_tag)


def _append_unique(target: List[Dict[str, Any]], source: Iterable[Dict[str, Any]], seen: set[str]) -> None:
    for product in source:
        asin = str(product.get("asin", "")).strip().upper()
        if asin and asin not in seen:
            seen.add(asin)
            target.append(product)


# --------------------------- CREATORS API --------------------------------
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
    product = _api_item_to_product(items[0], partner_tag)
    if not product:
        return None
    return product if _filter_verified_product(
        product, min_price, max_price, min_discount, max_discount, require_free_or_prime
    ) else None


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
    seen: set[str] = set()
    pages_needed = min(MAX_CREATORS_PAGES, max(1, (item_count + 9) // 10))

    for page in range(1, pages_needed + 1):
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
        delivery_modes = [None]
        if solo_spedizione_gratuita:
            # Due query distinte evitano di assumere la semantica AND/OR di più flag
            # e permettono di sapere quale requisito è stato verificato da Amazon.
            delivery_modes = ["Prime", "FreeShipping"]

        page_had_items = False
        all_modes_short = True
        for delivery_mode in delivery_modes:
            mode_payload = dict(payload)
            if delivery_mode:
                mode_payload["deliveryFlags"] = [delivery_mode]

            data = _creators_api_call("searchItems", mode_payload)
            if data is None:
                LOGGER.warning("Ricerca Creators API non disponibile; attivo fallback metadati")
                return None if not collected else collected

            items = data.get("searchResult", {}).get("items", []) or []
            if items:
                page_had_items = True
            if len(items) >= 10:
                all_modes_short = False

            parsed: List[Dict[str, Any]] = []
            for item in items:
                product = _api_item_to_product(
                    item, partner_tag, prime_filter_applied=(delivery_mode == "Prime")
                )
                if not product:
                    continue
                if delivery_mode == "FreeShipping":
                    product["is_sped_gratis"] = True
                if product and _filter_verified_product(
                    product, min_price, max_price, min_discount, max_discount
                ):
                    parsed.append(product)
            _append_unique(collected, parsed, seen)
            if len(collected) >= item_count:
                break

        if len(collected) >= item_count:
            break
        if not page_had_items or all_modes_short:
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
    # Senza API non possiamo garantire filtri dinamici: meglio zero risultati che dati fuorvianti.
    if (
        solo_spedizione_gratuita
        or min_price is not None
        or max_price is not None
        or min_discount > 0
        or max_discount < 100
    ):
        LOGGER.info("Fallback metadati disattivato: filtri dinamici non verificabili")
        return []

    query_encoded = urllib.parse.quote_plus(keyword)
    sort_param = SORT_FALLBACK_MAP.get(sort_type, "exact-aware-popularity-rank")
    collected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    max_pages = min(4, max(1, (item_count + 15) // 16))

    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.it/s?k={query_encoded}&page={page}&s={sort_param}"
        html_text = _fetch_html_cached(url)
        if not html_text:
            continue
        _append_unique(collected, _extract_metadata_from_html(html_text, partner_tag), seen)
        if len(collected) >= item_count:
            break
    return collected[:item_count]


# ----------------------------- API PUBBLICA ------------------------------
@st.cache_data(ttl=VETRINA_CACHE_TTL_SECONDS, show_spinner=False)
def ottieni_vetrina_casuale(partner_tag: Optional[str] = None, item_count: int = 10) -> List[Dict[str, Any]]:
    configured_tag = get_partner_tag() or str(partner_tag or "").strip()
    if not configured_tag:
        return []
    item_count = max(1, min(int(item_count or 10), 20))

    # Una singola vetrina viene condivisa dalla cache tra le sessioni per 15 minuti.
    keyword = random.choice(KEYWORDS_VETRINA)
    products = ottieni_offerte_avanzate(
        keyword=keyword,
        sort_type="Popolarità",
        min_discount=5,
        item_count=min(MAX_RESULTS, item_count * 2),
        _partner_tag_override=configured_tag,
    )
    if not products:
        products = ottieni_offerte_avanzate(
            keyword="offerte del giorno",
            sort_type="Popolarità",
            min_discount=0,
            item_count=min(MAX_RESULTS, item_count * 2),
            _partner_tag_override=configured_tag,
        )
    if products:
        products = list(products)
        random.shuffle(products)
        return products[:item_count]
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
        LOGGER.warning("Ricerca non eseguita: partner_tag mancante")
        return []

    item_count = max(1, min(int(item_count or 10), MAX_RESULTS))
    min_discount = max(0, min(int(min_discount or 0), 100))
    max_discount = max(min_discount, min(int(max_discount or 100), 100))
    clean_keyword = (keyword or "").strip()
    asin_match = RE_ASIN.search(clean_keyword)

    if asin_match and ("http" in clean_keyword.lower() or len(clean_keyword) == 10):
        asin = asin_match.group(1).upper()
        api_product = _get_item_from_creators_api(
            asin, partner_tag, min_price, max_price, min_discount, max_discount,
            require_free_or_prime=solo_spedizione_gratuita,
        )
        if api_product:
            return [api_product]

        # Fallback diretto: cerca l'ASIN e restituisce solo metadati non dinamici.
        fallback = _search_html_fallback(
            asin, "Popolarità", partner_tag, solo_spedizione_gratuita,
            min_price, max_price, min_discount, max_discount, 10,
        )
        for product in fallback:
            if product.get("asin") == asin:
                return [product]
        return []

    query = clean_keyword or "offerte del giorno"
    api_products = _search_creators_api(
        query, sort_type, partner_tag, solo_spedizione_gratuita,
        min_price, max_price, min_discount, max_discount, item_count,
    )
    if api_products is not None:
        return api_products[:item_count]

    return _search_html_fallback(
        query, sort_type, partner_tag, solo_spedizione_gratuita,
        min_price, max_price, min_discount, max_discount, item_count,
    )
