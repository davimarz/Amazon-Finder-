import streamlit as st
import requests
import urllib.parse
import re
import time
from curl_cffi import requests as c_requests
from bs4 import BeautifulSoup

SORT_MAPPINGS = {
    "Prezzo: dal più basso": "Price:LowToHigh",
    "Più Venduti / Rilevanza": "Relevance",
    "Prezzo: dal più alto": "Price:HighToLow",
    "Media recensioni clienti": "AvgCustomerReviews",
    "Ultime Novità": "NewestArrivals"
}

SORT_FALLBACK_MAP = {
    "Prezzo: dal più basso": "price-asc-rank",
    "Più Venduti / Rilevanza": "exact-aware-popularity-rank",
    "Prezzo: dal più alto": "price-desc-rank",
    "Media recensioni clienti": "review-rank",
    "Ultime Novità": "date-desc-rank"
}

_TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0
}

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
        resp = requests.post(token_url, data=payload, headers=headers, timeout=10)
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
        p5 = min(92, max(82, int(86 + (v - 4.8) * 30)))
        p4 = min(14, max(6, int(10 + (4.8 - v) * 20)))
        p3, p2 = 1, 1
        p1 = max(1, 100 - (p5 + p4 + p3 + p2))
    elif v >= 4.5:
        p5 = int(68 + (v - 4.5) * 45)
        p4 = int(18 - (v - 4.5) * 20)
        p3 = int(6 - (v - 4.5) * 10)
        p2 = int(3 - (v - 4.5) * 5)
        p1 = max(1, 100 - (p5 + p4 + p3 + p2))
    elif v >= 4.0:
        p5 = int(50 + (v - 4.0) * 35)
        p4 = int(24 - (v - 4.0) * 10)
        p3 = int(12 - (v - 4.0) * 10)
        p2 = int(6 - (v - 4.0) * 5)
        p1 = max(2, 100 - (p5 + p4 + p3 + p2))
    elif v >= 3.0:
        p5 = int(30 + (v - 3.0) * 20)
        p4 = int(22 + (v - 3.0) * 2)
        p3 = int(20 - (v - 3.0) * 8)
        p2 = int(12 - (v - 3.0) * 6)
        p1 = max(3, 100 - (p5 + p4 + p3 + p2))
    else:
        p5 = int(15 + v * 5)
        p4, p3, p2 = 15, 20, 25
        p1 = max(5, 100 - (p5 + p4 + p3 + p2))
        
    return {"5": p5, "4": p4, "3": p3, "2": p2, "1": p1}

def analizza_spedizione_html(item_tag):
    """
    Riconosce con precisione se un prodotto è Prime, ha consegna gratuita o a pagamento.
    Default rigoroso: se non ci sono prove certe di Prime o Spedizione Gratuita, è considerata standard/a pagamento.
    """
    html_str = str(item_tag).lower()
    testo_completo = item_tag.get_text(" ", strip=True).lower()

    # 1. Riconoscimento badge Prime reale
    is_prime = bool(
        "a-icon-prime" in html_str or
        "s-prime" in html_str or
        item_tag.find("i", class_=re.compile(r"a-icon-prime|s-prime", re.I)) or
        item_tag.find("span", {"aria-label": re.compile(r"^prime$", re.I)})
    )

    # 2. Riconoscimento costi di spedizione espliciti
    costo_sped = 0.0
    match_costo = re.search(
        r'(?:consegna\s+a\s*€?\s*(\d+[.,]\d{2}))|'
        r'(?:consegna\s+a\s*(\d+[.,]\d{2})\s*€)|'
        r'(?:€\s*(\d+[.,]\d{2})\s*(?:di\s*)?spedizione)|'
        r'(?:(\d+[.,]\d{2})\s*€\s*(?:di\s*)?spedizione)|'
        r'(?:\+\s*€?\s*(\d+[.,]\d{2})\s*(?:di\s*)?spedizione)|'
        r'(?:spedizione\s*[:a]\s*€?\s*(\d+[.,]\d{2}))',
        testo_completo,
        re.I
    )

    if match_costo:
        val_str = next(v for v in match_costo.groups() if v is not None)
        try:
            val_num = float(val_str.replace(",", "."))
            if val_num > 0:
                costo_sped = val_num
        except ValueError:
            pass

    # Se c'è un costo reale > 0 e non è Prime, è a pagamento
    if costo_sped > 0 and not is_prime:
        return costo_sped, f"Consegna a €{costo_sped:.2f}", False, False

    # 3. Diciture esplicite di consegna senza costi
    frasi_gratuite = [
        "consegna senza costi aggiuntivi",
        "consegna gratuita",
        "spedizione gratuita",
        "senza costi aggiuntivi",
        "consegna gratis",
        "spedizione gratis"
    ]
    ha_dicitura_gratis = any(f in testo_completo for f in frasi_gratuite)

    if is_prime:
        return 0.0, "Prime (Spedizione gratuita)", True, True

    if ha_dicitura_gratis:
        return 0.0, "Spedizione gratuita", False, True

    # Default restrittivo per evitare falsi positivi
    return costo_sped, "Spedizione standard", False, False

def ottieni_offerte_avanzate(
    categoria="", 
    sottocategoria="", 
    keyword="", 
    sort_type="Prezzo: dal più basso", 
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

    termini = []
    if sottocategoria and sottocategoria != "Tutte":
        termini.append(sottocategoria)
    elif categoria:
        termini.append(categoria)
    if clean_keyword:
        termini.append(clean_keyword)

    query_str = " ".join(termini) if termini else "offerte"

    # 1. Chiamata API Ufficiale Creators
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
            "SortBy": SORT_MAPPINGS.get(sort_type, "Relevance"),
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

        if min_price is not None and min_price > 0:
            payload["MinPrice"] = int(min_price * 100)
        if max_price is not None and max_price > 0:
            payload["MaxPrice"] = int(max_price * 100)

        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("SearchResult", {}).get("Items", [])
                prodotti = []

                for it in items:
                    asin = it.get("ASIN", "")
                    title = it.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "Prodotto Amazon")
                    img = it.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", "https://via.placeholder.com/400")
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
                            if costo_sped > 0 and not is_prime:
                                is_free_ship = False

                    if solo_spedizione_gratuita and not is_free_ship:
                        continue

                    sconto_val = 0
                    if old_price_val > price_val and old_price_val > 0:
                        sconto_val = int(round(((old_price_val - price_val) / old_price_val) * 100))

                    if sconto_val < min_discount or (max_discount is not None and sconto_val > max_discount):
                        continue

                    if is_prime:
                        info_sped = "Prime (Spedizione gratuita)"
                    elif is_free_ship:
                        info_sped = "Spedizione gratuita"
                    elif costo_sped > 0:
                        info_sped = f"Consegna a €{costo_sped:.2f}"
                    else:
                        info_sped = "Spedizione standard"

                    prodotti.append({
                        "asin": asin,
                        "titolo": title,
                        "descrizione": title,
                        "immagine_url": img,
                        "prezzo_iniziale": old_price_val,
                        "prezzo_finale": price_val,
                        "sconto": f"-{sconto_val}%" if sconto_val > 0 else "",
                        "sconto_val": sconto_val,
                        "is_prime": is_prime,
                        "is_sped_gratis": is_free_ship,
                        "info_spedizione": info_sped,
                        "costo_spedizione": costo_sped,
                        "voto_medio": float(it.get("CustomerReviews", {}).get("StarRating", {}).get("Value", 4.8)),
                        "num_recensioni": int(it.get("CustomerReviews", {}).get("Count", 765)),
                        "link_affiliato": link
                    })

                if prodotti:
                    return prodotti
        except Exception:
            pass

    # 2. Motore Fallback Potenziato
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

    if min_price is not None and min_price > 0:
        base_url += f"&low-price={int(min_price)}"
    if max_price is not None and max_price > 0:
        base_url += f"&high-price={int(max_price)}"

    headers = {
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Upgrade-Insecure-Requests": "1"
    }

    prodotti = []
    asins_visti = set()
    page_num = 1
    session = c_requests.Session(impersonate="chrome")

    try:
        while len(prodotti) < item_count and page_num <= 12:
            resp = session.get(f"{base_url}&page={page_num}", headers=headers, timeout=12)
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
                if "non disponibile" in text_full or "attualmente non disponibile" in text_full:
                    continue

                costo_sped, info_sped, is_prime, is_free_ship = analizza_spedizione_html(it)

                if solo_spedizione_gratuita and not is_free_ship:
                    continue

                price_whole = it.find("span", {"class": "a-price-whole"})
                price_fraction = it.find("span", {"class": "a-price-fraction"})
                prezzo_prodotto = 0.0

                if price_whole:
                    whole_clean = price_whole.text.replace(".", "").replace(",", "").strip()
                    fraction_clean = price_fraction.text.strip() if price_fraction else "00"
                    try:
                        prezzo_prodotto = float(f"{whole_clean}.{fraction_clean}")
                    except ValueError:
                        prezzo_prodotto = 0.0
                else:
                    price_off = it.find("span", {"class": "a-offscreen"})
                    if price_off:
                        try:
                            clean_t = price_off.text.replace("€", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
                            prezzo_prodotto = float(clean_t)
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
                img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else "https://via.placeholder.com/400"

                asins_visti.add(asin)
                prodotti.append({
                    "asin": asin,
                    "titolo": titolo,
                    "descrizione": titolo,
                    "immagine_url": img_url,
                    "prezzo_iniziale": prezzo_iniziale,
                    "prezzo_finale": prezzo_prodotto,
                    "sconto": f"-{sconto_val}%" if sconto_val > 0 else "",
                    "sconto_val": sconto_val,
                    "is_prime": is_prime,
                    "is_sped_gratis": is_free_ship,
                    "info_spedizione": info_sped,
                    "costo_spedizione": costo_sped,
                    "voto_medio": 4.8,
                    "num_recensioni": 765,
                    "link_affiliato": f"https://www.amazon.it/dp/{asin}?tag={partner_tag}"
                })

            page_num += 1
    except Exception:
        pass

    return prodotti
