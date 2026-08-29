import streamlit as st
import requests
import urllib.parse
import re
import time
from curl_cffi import requests as c_requests
from bs4 import BeautifulSoup

SORT_MAPPINGS = {
    "Prezzo minimo": "Price:LowToHigh",
    "Prezzo massimo": "Price:HighToLow",
    "Recensioni": "AvgCustomerReviews"
}

SORT_FALLBACK_MAP = {
    "Prezzo minimo": "price-asc-rank",
    "Prezzo massimo": "price-desc-rank",
    "Recensioni": "review-rank"
}

_TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0
}

_SESSION = None

def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = c_requests.Session(impersonate="chrome")
    return _SESSION

def get_creators_access_token():
    now = time.time()
    if _TOKEN_CACHE["access_token"] and now < _TOKEN_CACHE["expires_at"] - 60:
        return _TOKEN_CACHE["access_token"]

    try:
        creds = st.secrets["amazon_api"]
        client_id = creds["client_id"]
        client_secret = creds["client_secret"]
    except Exception:
        return None

    token_url = "https://api.amazon.com/auth/o2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "creators::product_advertising::api"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        resp = requests.post(token_url, data=payload, headers=headers, timeout=4)
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

def calcola_distribuzione_recensioni(voto_medio, num_recensioni=765):
    v = max(1.0, min(5.0, float(voto_medio))) if voto_medio else 4.5
    if v >= 4.8:
        p5, p4, p3, p2 = 88, 9, 1, 1
    elif v >= 4.5:
        p5, p4, p3, p2 = 72, 18, 5, 3
    elif v >= 4.0:
        p5, p4, p3, p2 = 55, 25, 12, 5
    elif v >= 3.0:
        p5, p4, p3, p2 = 35, 25, 20, 12
    else:
        p5, p4, p3, p2 = 20, 15, 20, 25
    p1 = max(1, 100 - (p5 + p4 + p3 + p2))
    return {"5": p5, "4": p4, "3": p3, "2": p2, "1": p1}

def analizza_spedizione_html(item_tag):
    html_str = str(item_tag).lower()
    testo_completo = item_tag.get_text(" ", strip=True).lower()

    is_prime = ("a-icon-prime" in html_str or "s-prime" in html_str or "prime" in testo_completo)
    
    frasi_gratuite = (
        "consegna senza costi aggiuntivi",
        "consegna gratuita",
        "spedizione gratuita",
        "senza costi aggiuntivi",
        "consegna gratis",
        "spedizione gratis"
    )
    ha_opzione_gratis = is_prime or any(f in testo_completo for f in frasi_gratuite)

    costo_sped = 0.0
    match_costo = re.search(r'(?:consegna\s+a|spedizione\s*[:a]|\+)\s*€?\s*(\d+[.,]\d{2})', testo_completo)
    if match_costo:
        try:
            costo_sped = float(match_costo.group(1).replace(",", "."))
        except ValueError:
            costo_sped = 0.0

    if ha_opzione_gratis and costo_sped > 0:
        return costo_sped, f"Gratis • A €{costo_sped:.2f}", is_prime, True
    if is_prime:
        return 0.0, "Prime (Gratuita)", True, True
    if ha_opzione_gratis:
        return 0.0, "Gratuita", False, True
    if costo_sped > 0:
        return costo_sped, f"Consegna a €{costo_sped:.2f}", False, False

    return 0.0, "Standard", False, False

def ordina_e_taglia_risultati(prodotti, sort_type, item_count):
    if sort_type == "Prezzo minimo":
        prodotti.sort(key=lambda x: x["prezzo_finale"])
    elif sort_type == "Prezzo massimo":
        prodotti.sort(key=lambda x: x["prezzo_finale"], reverse=True)
    elif sort_type == "Recensioni":
        prodotti.sort(key=lambda x: (x["voto_medio"], x["num_recensioni"]), reverse=True)
    return prodotti[:item_count]

@st.cache_data(ttl=300, show_spinner=False)
def ottieni_offerte_avanzate(
    categoria="", 
    sottocategoria="", 
    keyword="", 
    sort_type="Prezzo minimo", 
    solo_spedizione_gratuita=False, 
    min_price=None, 
    max_price=None, 
    min_discount=0, 
    max_discount=100, 
    item_count=10
):
    token = get_creators_access_token()
    partner_tag = st.secrets.get("amazon_api", {}).get("partner_tag", "eiapromo-21")
    
    clean_keyword = keyword.strip()
    asin_match = re.search(r'/(?:dp|gp/product|d)/([A-Z0-9]{10})', clean_keyword, re.I)
    if asin_match:
        clean_keyword = asin_match.group(1)

    query_str = clean_keyword if clean_keyword else "offerte del giorno"

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
        if min_price and min_price > 0:
            payload["MinPrice"] = int(min_price * 100)
        if max_price and max_price > 0:
            payload["MaxPrice"] = int(max_price * 100)

        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=5)
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
                        is_free_ship = delivery.get("IsFreeShippingEligible", False) or is_prime
                        charges = delivery.get("ShippingCharges", [])
                        if charges:
                            costo_sped = float(charges[0].get("Amount", 0.0))

                    if solo_spedizione_gratuita and not is_free_ship:
                        continue

                    sconto_val = 0
                    if old_price_val > price_val > 0:
                        sconto_val = int(round(((old_price_val - price_val) / old_price_val) * 100))

                    if sconto_val < min_discount or (max_discount is not None and sconto_val > max_discount):
                        continue

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
                        "voto_medio": float(it.get("CustomerReviews", {}).get("StarRating", {}).get("Value", 4.8)),
                        "num_recensioni": int(it.get("CustomerReviews", {}).get("Count", 765)),
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
    sort_code = SORT_FALLBACK_MAP.get(sort_type, "price-asc-rank")
    base_url = f"https://www.amazon.it/s?k={query_encoded}&s={sort_code}"

    if min_price and min_price > 0:
        base_url += f"&low-price={int(min_price)}"
    if max_price and max_price > 0:
        base_url += f"&high-price={int(max_price)}"

    headers = {
        "Accept-Language": "it-IT,it;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    prodotti = []
    asins_visti = set()
    page_num = 1
    session = get_session()

    try:
        while len(prodotti) < item_count and page_num <= 4:
            resp = session.get(f"{base_url}&page={page_num}", headers=headers, timeout=6)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.find_all("div", {"data-component-type": "s-search-result"})
            if not items:
                items = [div for div in soup.find_all("div", attrs={"data-asin": True}) if div.get("data-asin", "").strip()]
            if not items:
                break

            for it in items:
                if len(prodotti) >= item_count:
                    break

                asin = it.get("data-asin", "").strip()
                if not asin or asin in asins_visti:
                    continue

                text_full = it.get_text(" ", strip=True).lower()
                if "non disponibile" in text_full:
                    continue

                costo_sped, info_sped, is_prime, is_free_ship = analizza_spedizione_html(it)
                if solo_spedizione_gratuita and not is_free_ship:
                    continue

                price_whole = it.find("span", {"class": "a-price-whole"})
                prezzo_prodotto = 0.0
                if price_whole:
                    price_fraction = it.find("span", {"class": "a-price-fraction"})
                    whole_clean = price_whole.text.replace(".", "").replace(",", "").strip()
                    fraction_clean = price_fraction.text.strip() if price_fraction else "00"
                    try:
                        prezzo_prodotto = float(f"{whole_clean}.{fraction_clean}")
                    except ValueError:
                        prezzo_prodotto = 0.0

                if prezzo_prodotto <= 0.0:
                    continue

                basis_price = it.find("span", {"class": "a-price", "data-a-strike": "true"}) or it.find("span", {"class": "a-text-price"})
                prezzo_iniziale = prezzo_prodotto
                if basis_price:
                    basis_offscreen = basis_price.find("span", {"class": "a-offscreen"})
                    if basis_offscreen:
                        try:
                            clean_t = basis_offscreen.text.replace("€", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
                            prezzo_iniziale = float(clean_t)
                        except ValueError:
                            prezzo_iniziale = prezzo_prodotto

                sconto_val = 0
                if prezzo_iniziale > prezzo_prodotto and prezzo_iniziale > 0:
                    sconto_val = int(round(((prezzo_iniziale - prezzo_prodotto) / prezzo_iniziale) * 100))

                if sconto_val < min_discount or (max_discount is not None and sconto_val > max_discount):
                    continue

                title_tag = it.find("h2")
                titolo = title_tag.get_text(strip=True) if title_tag else "Prodotto Amazon"
                img_tag = it.find("img", {"class": "s-image"})
                img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else "https://via.placeholder.com/300"

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
                    "is_sped_gratis": is_free_ship,
                    "costo_spedizione": costo_sped,
                    "voto_medio": 4.8,
                    "num_recensioni": 765,
                    "link_affiliato": f"https://www.amazon.it/dp/{asin}?tag={partner_tag}"
                })

            page_num += 1
    except Exception:
        pass

    return ordina_e_taglia_risultati(prodotti, sort_type, item_count)
