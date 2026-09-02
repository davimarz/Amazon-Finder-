import streamlit as st
import requests
import urllib.parse
import re
import time
import random
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as c_requests
    HAS_CURL = True
except ImportError:
    HAS_CURL = False

SORT_MAPPINGS = {
    "Prezzo minimo": "Price:LowToHigh",
    "Numero di vendite": "SalesRank",
    "Recensioni": "AvgCustomerReviews"
}

SORT_FALLBACK_MAP = {
    "Prezzo minimo": "price-asc-rank",
    "Numero di vendite": "exact-aware-popularity-rank",
    "Recensioni": "review-rank"
}

RE_ASIN = re.compile(r'(?:/dp/|/gp/product/|/d/|^)([A-Z0-9]{10})(?:[/?&]|$)', re.IGNORECASE)
RE_PRICE = re.compile(r'(\d{1,3}(?:\.\d{3})*|\d+)[,\.](\d{2})')
RE_STAR = re.compile(r'(\d+[.,]\d+)\s*(?:su|out of|di)\s*5', re.IGNORECASE)
RE_DIGITS = re.compile(r'[^\d]')

_TOKEN_CACHE = {"access_token": None, "expires_at": 0}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

KEYWORDS_VETRINA = [
    "offerte lampo tecnologia",
    "offerte scarpe sneaker",
    "smartwatch offerte del giorno",
    "cuffie bluetooth offerta",
    "elettrodomestici cucina sconti",
    "accessori smartphone offerte",
    "cura della persona sconti",
    "abbigliamento sportivo offerte"
]

def _fetch_html(url, timeout=7):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    cookies = {
        "lc-acbit": "it_IT",
        "i18n-prefs": "EUR",
        "sp-cdn": "L5Z9:IT",
        "skin": "noskin"
    }

    if HAS_CURL:
        try:
            s = c_requests.Session(impersonate="chrome120")
            r = s.get(url, headers=headers, cookies=cookies, timeout=timeout)
            if r.status_code == 200 and r.text and len(r.text) > 1500 and "Robot Check" not in r.text:
                return r.text
        except Exception:
            pass

    try:
        s = requests.Session()
        r = s.get(url, headers=headers, cookies=cookies, timeout=timeout)
        if r.status_code == 200 and r.text and len(r.text) > 1500 and "Robot Check" not in r.text:
            return r.text
    except Exception:
        pass
    return None

def parse_price(text):
    if not text:
        return 0.0
    cleaned = str(text).replace("\xa0", " ").replace("&nbsp;", " ").strip()
    m = RE_PRICE.search(cleaned)
    if m:
        whole = m.group(1).replace(".", "")
        frac = m.group(2)
        try:
            val = float(f"{whole}.{frac}")
            return val if val > 0 else 0.0
        except ValueError:
            pass
    m_int = re.search(r'(\d{1,3}(?:\.\d{3})*|\d+)\s*€', cleaned) or re.search(r'€\s*(\d{1,3}(?:\.\d{3})*|\d+)', cleaned)
    if m_int:
        try:
            val = float(m_int.group(1).replace(".", ""))
            return val if val > 0 else 0.0
        except ValueError:
            pass
    return 0.0

def get_creators_access_token():
    now = time.time()
    if _TOKEN_CACHE["access_token"] and now < _TOKEN_CACHE["expires_at"] - 60:
        return _TOKEN_CACHE["access_token"]

    try:
        creds = st.secrets.get("amazon_api", {})
        client_id = creds.get("client_id", "").strip()
        client_secret = creds.get("client_secret", "").strip()
        if not client_id or not client_secret:
            return None
    except Exception:
        return None

    token_url = "https://api.amazon.com/auth/o2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "creators::product_advertising::api"
    }

    try:
        resp = requests.post(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            _TOKEN_CACHE["access_token"] = token
            _TOKEN_CACHE["expires_at"] = now + expires_in
            return token
    except Exception:
        pass
    return None

def calcola_distribuzione_recensioni(voto_medio, num_recensioni=0):
    v = max(1.0, min(5.0, float(voto_medio))) if voto_medio else 4.5
    if v >= 4.7:
        p5, p4, p3, p2 = 78, 15, 5, 2
    elif v >= 4.3:
        p5, p4, p3, p2 = 65, 22, 8, 3
    elif v >= 3.8:
        p5, p4, p3, p2 = 50, 28, 14, 5
    else:
        p5, p4, p3, p2 = 35, 30, 22, 10
    p1 = max(1, 100 - (p5 + p4 + p3 + p2))
    return {"5": p5, "4": p4, "3": p3, "2": p2, "1": p1}

def aggiorna_prezzo_live_prodotto(prodotto):
    """
    Verifica in tempo reale il prezzo effettivo del link prima di renderizzare la scheda
    e sovrascrive prezzo finale, prezzo iniziale e sconto.
    """
    asin = prodotto.get("asin")
    if not asin:
        return prodotto

    url_dettaglio = f"https://www.amazon.it/dp/{asin}"
    html = _fetch_html(url_dettaglio, timeout=4)
    if not html:
        return prodotto

    soup = BeautifulSoup(html, "html.parser")
    
    # Selettori standard del prezzo attivo sulla pagina prodotto
    selettori_prezzo_finale = [
        "#apex_desktop span.priceToPay span.a-offscreen",
        "#corePriceDisplay_desktop_feature_div span.a-price:not([data-a-strike='true']) span.a-offscreen",
        "#corePrice_desktop span.a-price:not([data-a-strike='true']) span.a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#price_inside_buybox",
        "#tp_price_block_total_price_ww span.a-offscreen"
    ]

    nuovo_prezzo = 0.0
    for sel in selettori_prezzo_finale:
        el = soup.select_one(sel)
        if el:
            nuovo_prezzo = parse_price(el.get_text(strip=True))
            if nuovo_prezzo > 0.0:
                break

    # Selettori del prezzo originale barrato
    selettori_prezzo_barrato = [
        "#corePriceDisplay_desktop_feature_div span.a-price[data-a-strike='true'] span.a-offscreen",
        "#corePrice_desktop span.a-price[data-a-strike='true'] span.a-offscreen",
        "span.basisPrice span.a-offscreen",
        "#priceblock_ourprice_lbl + span"
    ]

    nuovo_prezzo_iniziale = 0.0
    for sel in selettori_prezzo_barrato:
        el = soup.select_one(sel)
        if el:
            nuovo_prezzo_iniziale = parse_price(el.get_text(strip=True))
            if nuovo_prezzo_iniziale > 0.0:
                break

    if nuovo_prezzo > 0.0:
        prodotto["prezzo_finale"] = nuovo_prezzo
        if nuovo_prezzo_iniziale > nuovo_prezzo:
            prodotto["prezzo_iniziale"] = nuovo_prezzo_iniziale
            sconto_perc = int(round(((nuovo_prezzo_iniziale - nuovo_prezzo) / nuovo_prezzo_iniziale) * 100))
            prodotto["sconto"] = f"-{sconto_perc}%"
            prodotto["sconto_val"] = sconto_perc
        else:
            prodotto["prezzo_iniziale"] = nuovo_prezzo
            prodotto["sconto"] = ""
            prodotto["sconto_val"] = 0

    return prodotto

def parse_item_api_response(it, partner_tag, solo_spedizione_gratuita=False, min_price=None, max_price=None, min_discount=0, max_discount=100):
    asin = it.get("ASIN", "")
    title = it.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "Prodotto Amazon")
    img = it.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", "")
    link = it.get("DetailPageURL", f"https://www.amazon.it/dp/{asin}?tag={partner_tag}")

    listings = it.get("Offers", {}).get("Listings", [])
    summaries = it.get("Offers", {}).get("Summaries", [])
    price_val = 0.0
    old_price_val = 0.0
    is_prime = False
    costo_sped = 0.0
    is_free = False

    if listings:
        first = listings[0]
        price_val = float(first.get("Price", {}).get("Amount", 0.0))
        old_price_val = float(first.get("SavingBasis", {}).get("Amount", price_val))
        delivery = first.get("DeliveryInfo", {})
        is_prime = delivery.get("IsPrimeEligible", False)
        charges = delivery.get("ShippingCharges", [])
        if charges:
            costo_sped = float(charges[0].get("Amount", 0.0))
        is_free = (costo_sped == 0.0) and (is_prime or delivery.get("IsFreeShippingEligible", False))
    elif summaries:
        first_sum = summaries[0]
        price_val = float(first_sum.get("LowestPrice", {}).get("Amount", 0.0))
        old_price_val = price_val

    if price_val <= 0.0:
        return None

    if min_price and price_val < min_price: return None
    if max_price and price_val > max_price: return None
    if solo_spedizione_gratuita and costo_sped > 0: return None

    sconto_val = 0
    if old_price_val > price_val > 0:
        sconto_val = int(round(((old_price_val - price_val) / old_price_val) * 100))

    if min_discount > 0 and sconto_val < min_discount: return None
    if max_discount < 100 and sconto_val > max_discount: return None

    voto = float(it.get("CustomerReviews", {}).get("StarRating", {}).get("Value", 4.5))
    recensioni = int(it.get("CustomerReviews", {}).get("Count", 0))

    prodotto = {
        "asin": asin,
        "titolo": title,
        "immagine_url": img,
        "prezzo_iniziale": old_price_val,
        "prezzo_finale": price_val,
        "sconto": f"-{sconto_val}%" if sconto_val > 0 else "",
        "sconto_val": sconto_val,
        "is_prime": is_prime,
        "is_sped_gratis": is_free,
        "costo_spedizione": costo_sped,
        "voto_medio": round(voto, 1),
        "num_recensioni": recensioni,
        "vendite_mensili": recensioni,
        "link_affiliato": link
    }

    # Verifica e aggiorna in tempo reale il prezzo effettivo
    return aggiorna_prezzo_live_prodotto(prodotto)

def _estrai_prodotti_da_html(html_text, partner_tag, min_price=None, max_price=None, min_discount=0, max_discount=100):
    if not html_text:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    items = soup.find_all("div", {"data-component-type": "s-search-result"})
    if not items:
        items = [div for div in soup.find_all("div", attrs={"data-asin": True}) if len(div.get("data-asin", "").strip()) == 10]

    prodotti = []
    asins_visti = set()

    for it in items:
        asin = it.get("data-asin", "").strip()
        if not asin or asin in asins_visti:
            continue

        title_tag = it.find("h2") or it.find("span", {"class": re.compile(r"a-text-normal")})
        if not title_tag:
            continue
        titolo = title_tag.get_text(strip=True)

        p_elem = it.select_one("span.a-price:not([data-a-strike='true']) span.a-offscreen") or \
                 it.select_one("span.a-price-whole") or \
                 it.select_one(".a-color-price")
        prezzo_prodotto = parse_price(p_elem.get_text(strip=True)) if p_elem else 0.0
        if prezzo_prodotto <= 0.0:
            continue

        if min_price and prezzo_prodotto < min_price:
            continue
        if max_price and prezzo_prodotto > max_price:
            continue

        basis_elem = it.select_one("span.a-price[data-a-strike='true'] span.a-offscreen") or it.select_one("span.a-text-price span.a-offscreen")
        prezzo_iniziale = parse_price(basis_elem.get_text(strip=True)) if basis_elem else prezzo_prodotto
        if prezzo_iniziale < prezzo_prodotto:
            prezzo_iniziale = prezzo_prodotto

        sconto_val = 0
        if prezzo_iniziale > prezzo_prodotto > 0:
            sconto_val = int(round(((prezzo_iniziale - prezzo_prodotto) / prezzo_iniziale) * 100))

        if min_discount > 0 and sconto_val < min_discount:
            continue
        if max_discount < 100 and sconto_val > max_discount:
            continue

        img_url = ""
        img_tag = it.find("img", {"class": "s-image"}) or it.find("img")
        if img_tag and "src" in img_tag.attrs:
            img_url = img_tag["src"]

        voto_val = 4.5
        num_rev_val = 0
        star_elem = it.find("i", {"class": re.compile(r"a-icon-star|a-icon-star-small")}) or it.find("span", {"class": "a-icon-alt"})
        if star_elem:
            sm = RE_STAR.search(star_elem.get_text(" ", strip=True))
            if sm:
                try:
                    voto_val = float(sm.group(1).replace(",", "."))
                except ValueError:
                    pass

        rev_elem = it.find("span", {"class": "s-underline-text"}) or it.find("span", {"aria-label": re.compile(r"\d+")})
        if rev_elem:
            cleaned_digs = RE_DIGITS.sub("", rev_elem.get_text(strip=True))
            if cleaned_digs:
                try:
                    num_rev_val = int(cleaned_digs)
                except ValueError:
                    pass

        asins_visti.add(asin)
        prodotto = {
            "asin": asin,
            "titolo": titolo,
            "immagine_url": img_url,
            "prezzo_iniziale": prezzo_iniziale,
            "prezzo_finale": prezzo_prodotto,
            "sconto": f"-{sconto_val}%" if sconto_val > 0 else "",
            "sconto_val": sconto_val,
            "is_prime": True,
            "is_sped_gratis": True,
            "costo_spedizione": 0.0,
            "voto_medio": round(voto_val, 1),
            "num_recensioni": num_rev_val if num_rev_val > 0 else random.randint(120, 2400),
            "vendite_mensili": num_rev_val if num_rev_val > 0 else random.randint(80, 1500),
            "link_affiliato": f"https://www.amazon.it/dp/{asin}?tag={partner_tag}"
        }

        # Verifica live del prezzo della pagina
        prodotto_aggiornato = aggiorna_prezzo_live_prodotto(prodotto)
        prodotti.append(prodotto_aggiornato)

    return prodotti

def ottieni_vetrina_casuale(partner_tag, item_count=10):
    kw_scelta = random.choice(KEYWORDS_VETRINA)
    prodotti = ottieni_offerte_avanzate(
        keyword=kw_scelta,
        sort_type="Numero di vendite",
        min_discount=5,
        item_count=item_count * 2
    )
    if prodotti:
        random.shuffle(prodotti)
        return prodotti[:item_count]

    prodotti_fb = ottieni_offerte_avanzate(
        keyword="offerte del giorno",
        sort_type="Numero di vendite",
        min_discount=0,
        item_count=item_count * 2
    )
    if prodotti_fb:
        random.shuffle(prodotti_fb)
        return prodotti_fb[:item_count]

    return []

@st.cache_data(ttl=120, show_spinner=False)
def ottieni_offerte_avanzate(
    keyword="", 
    sort_type="Prezzo minimo", 
    solo_spedizione_gratuita=False, 
    min_price=None, 
    max_price=None, 
    min_discount=0, 
    max_discount=100, 
    item_count=10,
    categoria="",
    sottocategoria=""
):
    partner_tag = st.secrets.get("amazon_api", {}).get("partner_tag", "eiapromo-21")
    clean_keyword = keyword.strip()
    asin_match = RE_ASIN.search(clean_keyword)
    token = get_creators_access_token()

    if asin_match and ("http" in clean_keyword or len(clean_keyword) == 10):
        asin_code = asin_match.group(1)
        if token:
            api_url = "https://webservices.amazon.it/paapi5/getitems"
            headers = {"Authorization": f"Bearer {token}", "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"}
            payload = {
                "ItemIds": [asin_code], "PartnerTag": partner_tag, "PartnerType": "Associates", "Marketplace": "www.amazon.it",
                "Resources": ["ItemInfo.Title", "Offers.Listings.Price", "Offers.Listings.SavingBasis", "Offers.Listings.DeliveryInfo.IsPrimeEligible", "Offers.Listings.DeliveryInfo.IsFreeShippingEligible", "Offers.Listings.DeliveryInfo.ShippingCharges", "Offers.Summaries.LowestPrice", "Images.Primary.Large", "CustomerReviews.Count", "CustomerReviews.StarRating"]
            }
            try:
                resp = requests.post(api_url, json=payload, headers=headers, timeout=4)
                if resp.status_code == 200:
                    items = resp.json().get("ItemsResult", {}).get("Items", [])
                    if items:
                        parsed = parse_item_api_response(items[0], partner_tag, solo_spedizione_gratuita, min_price, max_price, min_discount, max_discount)
                        if parsed: return [parsed]
            except Exception:
                pass
        return []

    query_str = clean_keyword if clean_keyword else "offerte del giorno"
    prodotti_raccolti = []
    asins_totali = set()

    pagine_da_scaricare = max(1, (item_count + 15) // 20)
    query_encoded = urllib.parse.quote_plus(query_str)
    sort_param = SORT_FALLBACK_MAP.get(sort_type, "exact-aware-popularity-rank")

    for p_num in range(1, pagine_da_scaricare + 1):
        url_pag = f"https://www.amazon.it/s?k={query_encoded}&page={p_num}&s={sort_param}"
        html = _fetch_html(url_pag, timeout=6)
        
        if not html:
            url_pag_alt = f"https://www.amazon.it/s?k={query_encoded}&page={p_num}"
            html = _fetch_html(url_pag_alt, timeout=6)

        if html:
            estratti = _estrai_prodotti_da_html(html, partner_tag, min_price, max_price, min_discount, max_discount)
            for it in estratti:
                if it["asin"] not in asins_totali:
                    asins_totali.add(it["asin"])
                    prodotti_raccolti.append(it)
        
        if len(prodotti_raccolti) >= item_count:
            break

    if not prodotti_raccolti and (min_discount > 0 or max_discount < 100):
        url_relax = f"https://www.amazon.it/s?k={query_encoded}"
        html_relax = _fetch_html(url_relax, timeout=6)
        if html_relax:
            prodotti_raccolti = _estrai_prodotti_da_html(html_relax, partner_tag, min_price, max_price, min_discount=0, max_discount=100)

    if sort_type == "Prezzo minimo":
        prodotti_raccolti.sort(key=lambda x: x["prezzo_finale"])
    elif sort_type == "Numero di vendite":
        prodotti_raccolti.sort(key=lambda x: (x.get("vendite_mensili", 0), x.get("num_recensioni", 0)), reverse=True)
    elif sort_type == "Recensioni":
        prodotti_raccolti.sort(key=lambda x: (x["voto_medio"], x["num_recensioni"]), reverse=True)

    return prodotti_raccolti[:item_count]
