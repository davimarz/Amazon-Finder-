import streamlit as st
import requests
import urllib.parse
import re
import time

SORT_MAPPINGS = {
    "Prezzo minimo": "Price:LowToHigh",
    "Numero di vendite": "SalesRank",
    "Recensioni": "AvgCustomerReviews"
}

RE_ASIN = re.compile(r'(?:/dp/|/gp/product/|/d/|^)([A-Z0-9]{10})(?:[/?&]|$)', re.IGNORECASE)

_TOKEN_CACHE = {"access_token": None, "expires_at": 0}

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
        resp = requests.post(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=6)
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

    if min_price and price_val < min_price:
        return None
    if max_price and price_val > max_price:
        return None

    if solo_spedizione_gratuita and costo_sped > 0:
        return None

    sconto_val = 0
    if old_price_val > price_val > 0:
        sconto_val = int(round(((old_price_val - price_val) / old_price_val) * 100))

    if min_discount > 0 and sconto_val < min_discount:
        return None
    if max_discount < 100 and sconto_val > max_discount:
        return None

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
            "Offers.Summaries.LowestPrice",
            "Images.Primary.Large",
            "CustomerReviews.Count",
            "CustomerReviews.StarRating"
        ]
    }
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=6)
        if resp.status_code == 200:
            items = resp.json().get("ItemsResult", {}).get("Items", [])
            if items:
                parsed = parse_item_api_response(items[0], partner_tag)
                if parsed:
                    return [parsed]
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
    asin_match = RE_ASIN.search(clean_keyword)
    token = get_creators_access_token()

    if not token:
        st.error("⚠️ Impossibile autenticarsi alle API Amazon ufficiali. Verifica le credenziali nei Secrets di Streamlit.")
        return []

    # 1. Ricerca diretta per ASIN / Link prodotto tramite GetItems ufficiale
    if asin_match and ("http" in clean_keyword or len(clean_keyword) == 10):
        asin_code = asin_match.group(1)
        res_api = ottieni_dettaglio_asin_api(asin_code, token, partner_tag)
        if res_api:
            if solo_spedizione_gratuita and res_api[0]["costo_spedizione"] > 0:
                return []
            return res_api
        return []

    query_str = clean_keyword if clean_keyword else "offerte del giorno"

    # 2. Ricerca catalogo prodotti tramite SearchItems ufficiale
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
            "Offers.Summaries.LowestPrice",
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
        resp = requests.post(api_url, json=payload, headers=headers, timeout=6)
        if resp.status_code == 200:
            items = resp.json().get("SearchResult", {}).get("Items", [])
            prodotti = []
            for it in items:
                parsed = parse_item_api_response(
                    it, 
                    partner_tag, 
                    solo_spedizione_gratuita=solo_spedizione_gratuita,
                    min_price=min_price,
                    max_price=max_price,
                    min_discount=min_discount,
                    max_discount=max_discount
                )
                if parsed:
                    prodotti.append(parsed)
            return ordina_e_taglia_risultati(prodotti, sort_type, item_count)
        else:
            try:
                err_data = resp.json()
                err_msg = err_data.get("Errors", [{}])[0].get("Message", "Errore chiamata PA-API")
                st.warning(f"Risposta Amazon API: {err_msg}")
            except Exception:
                pass
    except Exception as e:
        st.error(f"Errore di connessione API Amazon: {str(e)}")

    return []
