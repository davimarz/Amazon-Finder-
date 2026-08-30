import streamlit as st
import requests
import urllib.parse
import re
import time
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

SHIPPING_PATTERNS = [
    re.compile(r'(\d+[\.,]\d{2})\s*€\s*(?:di|per\s+(?:la)?)?\s*(?:spedizione|consegna|invio|trasporto)', re.IGNORECASE),
    re.compile(r'(?:consegna|spedizione|costo\s+consegna|costi?\s+di\s+spedizione|spese\s+di\s+spedizione)\s*(?:a|per|di|da|:)?\s*€?\s*(\d+[\.,]\d{2})', re.IGNORECASE),
    re.compile(r'\+\s*€?\s*(\d+[\.,]\d{2})', re.IGNORECASE),
    re.compile(r'€\s*(\d+[\.,]\d{2})\s*(?:di|per\s+(?:la)?)?\s*(?:spedizione|consegna)', re.IGNORECASE),
    re.compile(r'(?:eur|euro)\s*(\d+[\.,]\d{2})', re.IGNORECASE)
]

_TOKEN_CACHE = {"access_token": None, "expires_at": 0}

_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1"
}

def _fetch_html(url, timeout=8):
    if HAS_CURL:
        try:
            s = c_requests.Session(impersonate="chrome120")
            r = s.get(url, headers=_HTTP_HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text and len(r.text) > 2500:
                return r.text
        except Exception:
            pass

    try:
        s = requests.Session()
        r = s.get(url, headers=_HTTP_HEADERS, timeout=timeout)
        if r.status_code == 200 and r.text:
            return r.text
    except Exception:
        pass
    return None

def parse_price(text):
    if not text:
        return 0.0
    m = RE_PRICE.search(str(text))
    if m:
        whole = m.group(1).replace(".", "")
        frac = m.group(2)
        try:
            val = float(f"{whole}.{frac}")
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
        resp = requests.post(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=5)
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
        p5, p4, p3, p2 = int(75 + (v - 4.7) * 50), int(15 - (v - 4.7) * 20), 5, 3
    elif v >= 4.3:
        p5, p4, p3, p2 = int(60 + (v - 4.3) * 35), int(22 - (v - 4.3) * 15), 9, 5
    elif v >= 3.8:
        p5, p4, p3, p2 = int(45 + (v - 3.8) * 30), int(26 - (v - 3.8) * 8), 16, 8
    elif v >= 3.0:
        p5, p4, p3, p2 = int(30 + (v - 3.0) * 18), 25, 22, 13
    else:
        p5, p4, p3, p2 = 15, 18, 22, 25
    p1 = max(1, 100 - (p5 + p4 + p3 + p2))
    return {"5": p5, "4": p4, "3": p3, "2": p2, "1": p1}

def _ottieni_prodotto_singolo_dp(asin, partner_tag, min_price=None, max_price=None, min_discount=0, max_discount=100, solo_spedizione_gratuita=False):
    url = f"https://www.amazon.it/dp/{asin}?th=1"
    html = _fetch_html(url, timeout=8)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    t_tag = soup.select_one("#productTitle")
    titolo = t_tag.get_text(strip=True) if t_tag else "Prodotto Amazon"

    price_val = 0.0
    p_tags = [
        soup.select_one("#corePriceDisplay_desktop_feature_div .priceToPay span.a-offscreen"),
        soup.select_one("#corePrice_desktop .priceToPay span.a-offscreen"),
        soup.select_one("#apex_desktop .priceToPay span.a-offscreen"),
        soup.select_one("#priceblock_ourprice"),
        soup.select_one("#priceblock_dealprice"),
        soup.select_one("#corePriceDisplay_desktop_feature_div .a-price-whole"),
        soup.select_one("#desktop_buybox .a-price span.a-offscreen")
    ]
    for pt in p_tags:
        if pt:
            price_val = parse_price(pt.get_text(strip=True))
            if price_val > 0:
                break

    if price_val <= 0.0:
        return []

    if min_price and price_val < min_price: return []
    if max_price and price_val > max_price: return []

    old_price_val = price_val
    basis_tags = [
        soup.select_one("#corePriceDisplay_desktop_feature_div .basisPrice span.a-offscreen"),
        soup.select_one("#corePriceDisplay_desktop_feature_div span[data-a-strike='true'] span.a-offscreen"),
        soup.select_one("#apex_desktop .basisPrice span.a-offscreen"),
        soup.select_one("#apex_desktop .a-text-price span.a-offscreen")
    ]
    for bt in basis_tags:
        if bt:
            op = parse_price(bt.get_text(strip=True))
            if op > price_val:
                old_price_val = op
                break

    sconto_str = ""
    sconto_val = 0
    if old_price_val > price_val > 0:
        sconto_val = int(round(((old_price_val - price_val) / old_price_val) * 100))
        if sconto_val > 0:
            sconto_str = f"-{sconto_val}%"

    if min_discount > 0 and sconto_val < min_discount: return []
    if max_discount < 100 and sconto_val > max_discount: return []

    deliv_box = soup.select_one("#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE") or \
                soup.select_one("#deliveryMessageMirId") or \
                soup.select_one("#delivery-message") or \
                soup.select_one("#desktop_buybox #delivery-message") or \
                soup.select_one("#tabular-buybox")

    costo_sped = 0.0
    is_prime = False
    is_free = False

    if deliv_box:
        deliv_text = deliv_box.get_text(" ", strip=True).replace(" ", " ")
        deliv_lower = deliv_text.lower()

        for pat in SHIPPING_PATTERNS:
            m = pat.search(deliv_text)
            if m:
                costo_sped = parse_price(m.group(1))
                if costo_sped > 0:
                    break

        if costo_sped == 0.0:
            is_prime = bool("prime" in deliv_lower or soup.select_one("#desktop_buybox .a-icon-prime"))
            frasi_gratis = ("senza costi aggiuntivi", "consegna gratuita", "spedizione gratuita", "consegna gratis", "spedizione gratis")
            is_free = is_prime or any(f in deliv_lower for f in frasi_gratis)

    if solo_spedizione_gratuita and costo_sped > 0:
        return []

    img_tag = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront") or soup.select_one("#main-image-container img")
    img_url = img_tag["src"] if (img_tag and "src" in img_tag.attrs) else "https://via.placeholder.com/300"

    voto_val = 4.5
    num_rev_val = 0
    star_tag = soup.select_one("#acrPopover span.a-icon-alt") or soup.select_one("#averageCustomerReviews span.a-icon-alt")
    if star_tag:
        sm = RE_STAR.search(star_tag.get_text(strip=True))
        if sm:
            try:
                voto_val = float(sm.group(1).replace(",", "."))
            except ValueError:
                pass

    rev_tag = soup.select_one("#acrCustomerReviewText")
    if rev_tag:
        digs = RE_DIGITS.sub("", rev_tag.get_text(strip=True))
        if digs:
            try:
                num_rev_val = int(digs)
            except ValueError:
                pass

    return [{
        "asin": asin,
        "titolo": titolo,
        "immagine_url": img_url,
        "prezzo_iniziale": old_price_val,
        "prezzo_finale": price_val,
        "sconto": sconto_str,
        "sconto_val": sconto_val,
        "is_prime": is_prime,
        "is_sped_gratis": is_free,
        "costo_spedizione": costo_sped,
        "voto_medio": round(voto_val, 1),
        "num_recensioni": num_rev_val,
        "vendite_mensili": num_rev_val,
        "link_affiliato": f"https://www.amazon.it/dp/{asin}?tag={partner_tag}"
    }]

def parse_item_api_response(it, partner_tag, solo_spedizione_gratuita=False, min_price=None, max_price=None, min_discount=0, max_discount=100):
    asin = it.get("ASIN", "")
    title = it.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "Prodotto Amazon")
    img = it.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", "https://via.placeholder.com/300")
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

    return {
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

def ordina_e_taglia_risultati(prodotti, sort_type, item_count):
    if sort_type == "Prezzo minimo":
        prodotti.sort(key=lambda x: x["prezzo_finale"])
    elif sort_type == "Numero di vendite":
        prodotti.sort(key=lambda x: (x.get("vendite_mensili", 0), x.get("num_recensioni", 0)), reverse=True)
    elif sort_type == "Recensioni":
        prodotti.sort(key=lambda x: (x["voto_medio"], x["num_recensioni"]), reverse=True)
    return prodotti[:item_count]

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
            payload = {"ItemIds": [asin_code], "PartnerTag": partner_tag, "PartnerType": "Associates", "Marketplace": "www.amazon.it", "Resources": ["ItemInfo.Title", "Offers.Listings.Price", "Offers.Listings.SavingBasis", "Offers.Listings.DeliveryInfo.IsPrimeEligible", "Offers.Listings.DeliveryInfo.IsFreeShippingEligible", "Offers.Listings.DeliveryInfo.ShippingCharges", "Offers.Summaries.LowestPrice", "Images.Primary.Large", "CustomerReviews.Count", "CustomerReviews.StarRating"]}
            try:
                resp = requests.post(api_url, json=payload, headers=headers, timeout=5)
                if resp.status_code == 200:
                    items = resp.json().get("ItemsResult", {}).get("Items", [])
                    if items:
                        parsed = parse_item_api_response(items[0], partner_tag, solo_spedizione_gratuita, min_price, max_price, min_discount, max_discount)
                        if parsed: return [parsed]
            except Exception:
                pass
        
        # Fallback Scraper di precisione pagina prodotto
        return _ottieni_prodotto_singolo_dp(asin_code, partner_tag, min_price, max_price, min_discount, max_discount, solo_spedizione_gratuita)

    query_str = clean_keyword if clean_keyword else "offerte del giorno"

    if token:
        api_url = "https://webservices.amazon.it/paapi5/searchitems"
        headers = {"Authorization": f"Bearer {token}", "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"}
        payload = {
            "Keywords": query_str, "PartnerTag": partner_tag, "PartnerType": "Associates", "Marketplace": "www.amazon.it",
            "ItemCount": min(item_count, 10), "SortBy": SORT_MAPPINGS.get(sort_type, "Price:LowToHigh"),
            "Resources": ["ItemInfo.Title", "Offers.Listings.Price", "Offers.Listings.SavingBasis", "Offers.Listings.DeliveryInfo.IsPrimeEligible", "Offers.Listings.DeliveryInfo.IsFreeShippingEligible", "Offers.Listings.DeliveryInfo.ShippingCharges", "Offers.Summaries.LowestPrice", "Images.Primary.Large", "CustomerReviews.Count", "CustomerReviews.StarRating"]
        }
        if min_price and min_price > 0: payload["MinPrice"] = int(min_price * 100)
        if max_price and max_price > 0: payload["MaxPrice"] = int(max_price * 100)
        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=5)
            if resp.status_code == 200:
                items = resp.json().get("SearchResult", {}).get("Items", [])
                prodotti = [p for p in (parse_item_api_response(it, partner_tag, solo_spedizione_gratuita, min_price, max_price, min_discount, max_discount) for it in items) if p]
                if prodotti: return ordina_e_taglia_risultati(prodotti, sort_type, item_count)
        except Exception:
            pass

    # Se token non valido o fallimento API -> Motore DP Scraper per la lista di ASIN (altissima precisione)
    query_encoded = urllib.parse.quote_plus(query_str)
    sort_param = SORT_FALLBACK_MAP.get(sort_type, "price-asc-rank")
    
    html_text = _fetch_html(f"https://www.amazon.it/s?k={query_encoded}&s={sort_param}", timeout=7) or _fetch_html(f"https://www.amazon.it/s?k={query_encoded}", timeout=7)
    
    prodotti = []
    if html_text:
        soup = BeautifulSoup(html_text, "html.parser")
        items = soup.find_all("div", {"data-component-type": "s-search-result"})
        if not items:
            items = [div for div in soup.find_all("div", attrs={"data-asin": True}) if len(div.get("data-asin", "").strip()) == 10]
            
        asins_visti = set()
        for it in items:
            if len(prodotti) >= item_count: break
            asin = it.get("data-asin", "").strip()
            if not asin or asin in asins_visti: continue
            
            # Utilizza lo scraper di precisione sulla singola pagina per assicurare l'assenza di errori di listino
            p_detail = _ottieni_prodotto_singolo_dp(asin, partner_tag, min_price, max_price, min_discount, max_discount, solo_spedizione_gratuita)
            if p_detail:
                prodotti.append(p_detail[0])
                asins_visti.add(asin)

    return ordina_e_taglia_risultati(prodotti, sort_type, item_count)
