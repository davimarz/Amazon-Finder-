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
RE_PRICE_TEXT = re.compile(r'(\d+[\.,]\d{2})\s*€|€\s*(\d+[\.,]\d{2})')
RE_STAR_ALT = re.compile(r'(\d+[.,]\d+)\s*(?:su|out of|di)\s*5', re.IGNORECASE)
RE_DIGITS = re.compile(r'[^\d]')
RE_REVIEWS = re.compile(r'(?:(\d{1,3}(?:\.\d{3})+|\d+))\s*(?:valutazion|recension|vot)', re.IGNORECASE)
RE_SALES = re.compile(r'(\d+k?|\d+[\.,]\d+k?)\+?\s*acquistati\s+nel\s+mese', re.IGNORECASE)

SHIPPING_PATTERNS = [
    re.compile(r'(\d+[\.,]\d{2})\s*€\s*(?:di|per\s+(?:la)?)?\s*(?:spedizione|consegna|invio|trasporto)', re.IGNORECASE),
    re.compile(r'(?:consegna|spedizione|costo\s+consegna|costi?\s+di\s+spedizione|spese\s+di\s+spedizione)\s*(?:a|per|di|da|:)?\s*€?\s*(\d+[\.,]\d{2})\s*€?', re.IGNORECASE),
    re.compile(r'\+\s*€?\s*(\d+[\.,]\d{2})\s*€?', re.IGNORECASE),
    re.compile(r'€\s*(\d+[\.,]\d{2})\s*(?:di|per\s+(?:la)?)?\s*(?:spedizione|consegna)', re.IGNORECASE),
    re.compile(r'(?:eur|euro)\s*(\d+[\.,]\d{2})\s*(?:di|per\s+(?:la)?)?\s*(?:spedizione|consegna)?', re.IGNORECASE),
    re.compile(r'(\d+[\.,]\d{2})\s*(?:eur|euro)\s*(?:di|per\s+(?:la)?)?\s*(?:spedizione|consegna)', re.IGNORECASE)
]

_TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0
}

_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

def _fetch_html(url, timeout=7):
    if HAS_CURL:
        try:
            s = c_requests.Session(impersonate="chrome120")
            r = s.get(url, headers=_HTTP_HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text and len(r.text) > 2000:
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

def get_creators_access_token():
    now = time.time()
    if _TOKEN_CACHE["access_token"] and now < _TOKEN_CACHE["expires_at"] - 60:
        return _TOKEN_CACHE["access_token"]

    try:
        creds = st.secrets.get("amazon_api", {})
        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")
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
        p5 = int(75 + (v - 4.7) * 50)
        p4 = int(15 - (v - 4.7) * 20)
        p3, p2 = 5, 3
    elif v >= 4.3:
        p5 = int(60 + (v - 4.3) * 35)
        p4 = int(22 - (v - 4.3) * 15)
        p3, p2 = 9, 5
    elif v >= 3.8:
        p5 = int(45 + (v - 3.8) * 30)
        p4 = int(26 - (v - 3.8) * 8)
        p3, p2 = 16, 8
    elif v >= 3.0:
        p5 = int(30 + (v - 3.0) * 18)
        p4, p3, p2 = 25, 22, 13
    else:
        p5, p4, p3, p2 = 15, 18, 22, 25

    p1 = max(1, 100 - (p5 + p4 + p3 + p2))
    return {"5": p5, "4": p4, "3": p3, "2": p2, "1": p1}

def analizza_recensioni_html(soup_item):
    voto_medio = 4.5
    num_recensioni = 0

    star_elem = soup_item.find("i", {"class": re.compile(r"a-icon-star|a-icon-star-small")})
    if star_elem:
        m = RE_STAR_ALT.search(star_elem.get_text(" ", strip=True))
        if m:
            try:
                voto_medio = float(m.group(1).replace(",", "."))
            except ValueError:
                pass

    review_elem = soup_item.find("span", {"id": "acrCustomerReviewText"}) or \
                  soup_item.find("span", {"class": "s-underline-text"}) or \
                  soup_item.find("a", {"href": re.compile(r"#customerReviews")})

    if review_elem:
        cleaned_num = RE_DIGITS.sub("", review_elem.get_text(strip=True))
        if cleaned_num:
            try:
                num_recensioni = int(cleaned_num)
            except ValueError:
                num_recensioni = 0

    return round(voto_medio, 1), num_recensioni

def estrai_costo_spedizione_rigoroso(soup_or_tag):
    # 1. Lettura diretta dagli attributi HTML di Amazon
    for elem in soup_or_tag.find_all(attrs={"data-csa-c-delivery-price": True}):
        val_raw = elem["data-csa-c-delivery-price"].strip()
        m = re.search(r'(\d+[\.,]\d{2})', val_raw)
        if m:
            try:
                c = float(m.group(1).replace(",", "."))
                if c > 0:
                    return c, False, False
            except ValueError:
                pass

    # 2. Lettura dai contenitori dedicati di consegna
    deliv_blocks = soup_or_tag.find_all("div", {
        "id": re.compile(r"deliveryMessageMirId|mir-layout-DELIVERY_BLOCK|delivery-message|amazonGlobal|tabular-buybox|buyBoxAccordion|shippingMessageInsideBuyBox", re.IGNORECASE)
    })
    
    if not deliv_blocks:
        deliv_blocks = soup_or_tag.find_all("div", {"class": re.compile(r"s-delivery-instructions-style|delivery-shipping-message", re.IGNORECASE)})

    texts_to_check = [b.get_text(" ", strip=True).replace("\xa0", " ") for b in deliv_blocks] if deliv_blocks else [soup_or_tag.get_text(" ", strip=True).replace("\xa0", " ")]

    for text in texts_to_check:
        for pat in SHIPPING_PATTERNS:
            m = pat.search(text)
            if m:
                try:
                    c = float(m.group(1).replace(",", "."))
                    if c > 0:
                        return c, False, False
                except ValueError:
                    pass

    # 3. Controllo Prime
    html_str = str(soup_or_tag).lower()
    full_lower = soup_or_tag.get_text(" ", strip=True).lower()
    is_prime = bool("a-icon-prime" in html_str or "s-prime" in html_str or "prime" in full_lower)
    if is_prime:
        return 0.0, True, True

    # 4. Spedizione Gratuita verificata (escludendo banner 'resi gratuiti' e 'ordini superiori a 35€')
    frasi_gratis_reali = (
        "consegna senza costi aggiuntivi",
        "consegna gratuita",
        "spedizione gratuita",
        "consegna gratis",
        "spedizione gratis"
    )
    is_free = any(f in full_lower for f in frasi_gratis_reali) and "ordini superiori" not in full_lower and "superiori a" not in full_lower
    return 0.0, False, is_free

def estrai_prezzo_tag(it):
    if not it:
        return 0.0
    price_whole = it.find("span", {"class": "a-price-whole"})
    if price_whole:
        price_fraction = it.find("span", {"class": "a-price-fraction"})
        whole_clean = price_whole.text.replace(".", "").replace(",", "").strip()
        fraction_clean = price_fraction.text.strip() if price_fraction else "00"
        try:
            val = float(f"{whole_clean}.{fraction_clean}")
            if val > 0:
                return val
        except ValueError:
            pass

    for off_tag in it.find_all("span", {"class": "a-offscreen"}):
        t = off_tag.get_text(strip=True)
        if "€" in t or re.search(r'\d+[.,]\d{2}', t):
            clean_t = t.replace("€", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
            try:
                val = float(clean_t)
                if val > 0:
                    return val
            except ValueError:
                continue

    text_match = RE_PRICE_TEXT.search(it.get_text(" ", strip=True))
    if text_match:
        val_str = text_match.group(1) or text_match.group(2)
        try:
            val = float(val_str.replace(".", "").replace(",", ".").strip())
            if val > 0:
                return val
        except ValueError:
            pass
    return 0.0

def _ottieni_prodotto_singolo_dp(asin, partner_tag):
    url = f"https://www.amazon.it/dp/{asin}?th=1"
    html_content = _fetch_html(url, timeout=7)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    title_tag = soup.find("span", {"id": "productTitle"})
    titolo = title_tag.get_text(strip=True) if title_tag else "Prodotto Amazon"

    price_block = soup.find("div", {"id": "corePrice_desktop"}) or \
                  soup.find("div", {"id": "corePriceDisplay_desktop_feature_div"}) or \
                  soup.find("div", {"id": "apex_desktop"}) or soup
    prezzo_finale = estrai_prezzo_tag(price_block)
    if prezzo_finale <= 0:
        prezzo_finale = estrai_prezzo_tag(soup)

    basis_tag = soup.find("span", {"class": "basisPrice"}) or soup.find("span", {"data-a-strike": "true"})
    prezzo_iniziale = estrai_prezzo_tag(basis_tag) if basis_tag else prezzo_finale
    if prezzo_iniziale < prezzo_finale:
        prezzo_iniziale = prezzo_finale

    sconto_val = 0
    if prezzo_iniziale > prezzo_finale > 0:
        sconto_val = int(round(((prezzo_iniziale - prezzo_finale) / prezzo_iniziale) * 100))

    costo_sped, is_prime, is_free = estrai_costo_spedizione_rigoroso(soup)

    img_tag = soup.find("img", {"id": "landingImage"}) or soup.find("img", {"id": "imgBlkFront"})
    img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else "https://via.placeholder.com/300"
    voto_estratto, recensioni_estratte = analizza_recensioni_html(soup)

    return [{
        "asin": asin,
        "titolo": titolo,
        "immagine_url": img_url,
        "prezzo_iniziale": prezzo_iniziale,
        "prezzo_finale": prezzo_finale,
        "sconto": f"-{sconto_val}%" if sconto_val > 0 else "",
        "sconto_val": sconto_val,
        "is_prime": is_prime,
        "is_sped_gratis": is_free,
        "costo_spedizione": costo_sped,
        "voto_medio": voto_estratto,
        "num_recensioni": recensioni_estratte,
        "vendite_mensili": recensioni_estratte,
        "link_affiliato": f"https://www.amazon.it/dp/{asin}?tag={partner_tag}"
    }]

def ottieni_dettaglio_asin_api(asin, token, partner_tag):
    api_url = "https://webservices.amazon.it/paapi5/getitems"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
        "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"
    }
    payload = {
        "ItemIds": [asin],
        "PartnerTag": partner_tag,
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.it",
        "Resources": [
            "ItemInfo.Title",
            "Offers.Listings.Price",
            "Offers.Listings.SavingBasis",
            "Offers.Listings.DeliveryInfo.IsPrimeEligible",
            "Offers.Listings.DeliveryInfo.IsFreeShippingEligible",
            "Offers.Listings.DeliveryInfo.ShippingCharges",
            "Images.Primary.Large",
            "CustomerReviews.Count",
            "CustomerReviews.StarRating"
        ]
    }
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=4)
        if resp.status_code == 200:
            items = resp.json().get("ItemsResult", {}).get("Items", [])
            if items:
                it = items[0]
                title = it.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "Prodotto Amazon")
                img = it.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", "https://via.placeholder.com/300")
                link = it.get("DetailPageURL", f"https://www.amazon.it/dp/{asin}?tag={partner_tag}")

                listings = it.get("Offers", {}).get("Listings", [])
                price_val = 0.0
                old_price_val = 0.0
                costo_sped = 0.0
                is_prime = False

                if listings:
                    first = listings[0]
                    price_val = float(first.get("Price", {}).get("Amount", 0.0))
                    old_price_val = float(first.get("SavingBasis", {}).get("Amount", price_val))
                    delivery = first.get("DeliveryInfo", {})
                    is_prime = delivery.get("IsPrimeEligible", False)
                    charges = delivery.get("ShippingCharges", [])
                    if charges:
                        costo_sped = float(charges[0].get("Amount", 0.0))

                sconto_val = 0
                if old_price_val > price_val > 0:
                    sconto_val = int(round(((old_price_val - price_val) / old_price_val) * 100))

                voto = float(it.get("CustomerReviews", {}).get("StarRating", {}).get("Value", 4.5))
                recensioni = int(it.get("CustomerReviews", {}).get("Count", 0))

                return [{
                    "asin": asin,
                    "titolo": title,
                    "immagine_url": img,
                    "prezzo_iniziale": old_price_val,
                    "prezzo_finale": price_val,
                    "sconto": f"-{sconto_val}%" if sconto_val > 0 else "",
                    "sconto_val": sconto_val,
                    "is_prime": is_prime,
                    "is_sped_gratis": (costo_sped == 0.0 and is_prime),
                    "costo_spedizione": costo_sped,
                    "voto_medio": voto,
                    "num_recensioni": recensioni,
                    "vendite_mensili": recensioni,
                    "link_affiliato": link
                }]
    except Exception:
        pass
    return []

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
    
    # Riconoscimento prioritario se link o ASIN
    asin_match = RE_ASIN.search(clean_keyword)
    if asin_match and ("http" in clean_keyword or len(clean_keyword) == 10):
        asin_code = asin_match.group(1)
        token = get_creators_access_token()
        if token:
            res_api = ottieni_dettaglio_asin_api(asin_code, token, partner_tag)
            if res_api and res_api[0]["costo_spedizione"] > 0:
                if solo_spedizione_gratuita:
                    return []
                return res_api

        res_dp = _ottieni_prodotto_singolo_dp(asin_code, partner_tag)
        if res_dp:
            if solo_spedizione_gratuita and res_dp[0]["costo_spedizione"] > 0:
                return []
            return res_dp

    query_str = clean_keyword if clean_keyword else "offerte"
    token = get_creators_access_token()

    if token:
        api_url = "https://webservices.amazon.it/paapi5/searchitems"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"
        }
        payload = {
            "Keywords": query_str,
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.it",
            "ItemCount": min(item_count, 10),
            "SortBy": SORT_MAPPINGS.get(sort_type, "Price:LowToHigh"),
            "Resources": [
                "ItemInfo.Title",
                "Offers.Listings.Price",
                "Offers.Listings.SavingBasis",
                "Offers.Listings.DeliveryInfo.IsPrimeEligible",
                "Offers.Listings.DeliveryInfo.IsFreeShippingEligible",
                "Offers.Listings.DeliveryInfo.ShippingCharges",
                "Images.Primary.Large",
                "CustomerReviews.Count",
                "CustomerReviews.StarRating"
            ]
        }
        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=4)
            if resp.status_code == 200:
                items = resp.json().get("SearchResult", {}).get("Items", [])
                prodotti = []
                for it in items:
                    asin = it.get("ASIN", "")
                    title = it.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "Prodotto Amazon")
                    img = it.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", "https://via.placeholder.com/300")
                    link = it.get("DetailPageURL", f"https://www.amazon.it/dp/{asin}?tag={partner_tag}")

                    listings = it.get("Offers", {}).get("Listings", [])
                    price_val = 0.0
                    old_price_val = 0.0
                    is_prime = False
                    is_free_ship = False
                    costo_sped = 0.0

                    if listings:
                        first = listings[0]
                        price_val = float(first.get("Price", {}).get("Amount", 0.0))
                        old_price_val = float(first.get("SavingBasis", {}).get("Amount", price_val))
                        delivery = first.get("DeliveryInfo", {})
                        is_prime = delivery.get("IsPrimeEligible", False)
                        charges = delivery.get("ShippingCharges", [])
                        if charges:
                            costo_sped = float(charges[0].get("Amount", 0.0))
                        is_free_ship = (costo_sped == 0.0) and (is_prime or delivery.get("IsFreeShippingEligible", False))

                    if solo_spedizione_gratuita and costo_sped > 0:
                        continue

                    sconto_val = 0
                    if old_price_val > price_val > 0:
                        sconto_val = int(round(((old_price_val - price_val) / old_price_val) * 100))

                    voto_reale = float(it.get("CustomerReviews", {}).get("StarRating", {}).get("Value", 4.5))
                    recensioni_reali = int(it.get("CustomerReviews", {}).get("Count", 0))

                    prodotti.append({
                        "asin": asin,
                        "titolo": title,
                        "immagine_url": img,
                        "prezzo_iniziale": old_price_val,
                        "prezzo_finale": price_val,
                        "sconto": f"-{sconto_val}%" if sconto_val > 0 else "",
                        "sconto_val": sconto_val,
                        "is_prime": is_prime,
                        "is_sped_gratis": is_free_ship,
                        "costo_spedizione": costo_sped,
                        "voto_medio": voto_reale,
                        "num_recensioni": recensioni_reali,
                        "vendite_mensili": recensioni_reali,
                        "link_affiliato": link
                    })
                if prodotti:
                    return ordina_e_taglia_risultati(prodotti, sort_type, item_count)
        except Exception:
            pass

    return _ottieni_offerte_fallback(
        query_str=query_str,
        sort_type=sort_type,
        solo_spedizione_gratuita=solo_spedizione_gratuita,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        max_discount=max_discount,
        item_count=item_count,
        partner_tag=partner_tag
    )

def _ottieni_offerte_fallback(query_str, sort_type, solo_spedizione_gratuita, min_price, max_price, min_discount, max_discount, item_count, partner_tag):
    query_encoded = urllib.parse.quote_plus(query_str)
    sort_param = SORT_FALLBACK_MAP.get(sort_type, "price-asc-rank")
    urls_to_try = [
        f"https://www.amazon.it/s?k={query_encoded}&s={sort_param}",
        f"https://www.amazon.it/s?k={query_encoded}"
    ]

    prodotti = []
    asins_visti = set()

    for base_url in urls_to_try:
        html_text = _fetch_html(base_url, timeout=7)
        if not html_text:
            continue

        soup = BeautifulSoup(html_text, "html.parser")
        items = soup.find_all("div", {"data-component-type": "s-search-result"})
        if not items:
            items = [div for div in soup.find_all("div", attrs={"data-asin": True}) if len(div.get("data-asin", "").strip()) == 10]

        for it in items:
            if len(prodotti) >= item_count:
                break

            asin = it.get("data-asin", "").strip()
            if not asin or asin in asins_visti:
                continue

            text_full = it.get_text(" ", strip=True).replace("\xa0", " ")
            if "non disponibile" in text_full.lower():
                continue

            costo_sped, is_prime, is_free = estrai_costo_spedizione_rigoroso(it)
            if solo_spedizione_gratuita and costo_sped > 0:
                continue

            prezzo_prodotto = estrai_prezzo_tag(it)
            if prezzo_prodotto <= 0.0:
                continue

            if min_price and prezzo_prodotto < min_price:
                continue
            if max_price and prezzo_prodotto > max_price:
                continue

            basis_price_tag = it.find("span", {"class": "a-price", "data-a-strike": "true"}) or it.find("span", {"class": "a-text-price"})
            prezzo_iniziale = prezzo_prodotto
            if basis_price_tag:
                p_init = estrai_prezzo_tag(basis_price_tag)
                if p_init > prezzo_prodotto:
                    prezzo_iniziale = p_init

            sconto_val = 0
            if prezzo_iniziale > prezzo_prodotto > 0:
                sconto_val = int(round(((prezzo_iniziale - prezzo_prodotto) / prezzo_iniziale) * 100))

            if min_discount > 0 and sconto_val < min_discount:
                continue

            title_tag = it.find("h2")
            titolo = title_tag.get_text(strip=True) if title_tag else "Prodotto Amazon"
            img_tag = it.find("img", {"class": "s-image"})
            img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else "https://via.placeholder.com/300"

            voto_estratto, recensioni_estratte = analizza_recensioni_html(it)

            asins_visti.add(asin)
            prodotti.append({
                "asin": asin,
                "titolo": titolo,
                "immagine_url": img_url,
                "prezzo_iniziale": prezzo_iniziale,
                "prezzo_finale": prezzo_prodotto,
                "sconto": f"-{sconto_val}%" if sconto_val > 0 else "",
                "sconto_val": sconto_val,
                "is_prime": is_prime,
                "is_sped_gratis": is_free,
                "costo_spedizione": costo_sped,
                "voto_medio": voto_estratto,
                "num_recensioni": recensioni_estratte,
                "vendite_mensili": recensioni_estratte,
                "link_affiliato": f"https://www.amazon.it/dp/{asin}?tag={partner_tag}"
            })

        if prodotti:
            break

    return ordina_e_taglia_risultati(prodotti, sort_type, item_count)
