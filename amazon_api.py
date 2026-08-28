import urllib.parse
import re
from curl_cffi import requests
from bs4 import BeautifulSoup

PARTNER_TAG = "eiapromo-21"

SORT_MAPPINGS = {
    "Prezzo: dal più basso": "price-asc-rank",
    "Più Venduti / Rilevanza": "exact-aware-popularity-rank",
    "Prezzo: dal più alto": "price-desc-rank",
    "Media recensioni clienti": "review-rank",
    "Ultime Novità": "date-desc-rank"
}

def calcola_distribuzione_recensioni(voto_medio, num_recensioni=765):
    v = max(1.0, min(5.0, float(voto_medio))) if voto_medio else 4.5
    
    if v >= 4.8:
        p5 = min(92, max(82, int(86 + (v - 4.8) * 30)))
        p4 = min(14, max(6, int(10 + (4.8 - v) * 20)))
        p3 = 1
        p2 = 1
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
        p4 = 15
        p3 = 20
        p2 = 25
        p1 = max(5, 100 - (p5 + p4 + p3 + p2))
        
    return {"5": p5, "4": p4, "3": p3, "2": p2, "1": p1}

def estrai_costo_spedizione(item_tag):
    testo_completo = item_tag.text.lower()
    match_generico = re.search(r'(?:€\s*(\d+[.,]\d{2})\s*(?:di\s*)?spedizione)|(?:(\d+[.,]\d{2})\s*€\s*(?:di\s*)?spedizione)|(?:spedizione\s*[:a]\s*€?\s*(\d+[.,]\d{2}))', testo_completo, re.IGNORECASE)
    if match_generico:
        val_str = next(v for v in match_generico.groups() if v is not None)
        try:
            costo = float(val_str.replace(",", "."))
            if costo > 0:
                return costo, f"Consegna a €{costo:.2f}"
        except ValueError:
            pass
    return 0.0, "Spedizione gratuita"

def verifica_se_spedizione_gratuita(item_tag, item_text):
    if "+ spedizione" in item_text or "di spedizione" in item_text:
        match = re.search(r'(?:spedizione.*?(\d+[.,]\d{2})\s*€)|(?:(\d+[.,]\d{2})\s*€.*?spedizione)', item_text)
        if match:
            val = float(next(v for v in match.groups() if v is not None).replace(",", "."))
            if val > 0:
                return False
    return True

def pulisci_titolo_descrizione(titolo_grezzo):
    if not titolo_grezzo:
        return "Prodotto Amazon"
    return titolo_grezzo.strip()

def ottieni_offerte_eventi_deals(item_count=30):
    """Estrae i prodotti direttamente dalla pagina ufficiale amazon.it/events/deals"""
    url = "https://www.amazon.it/events/deals"
    headers = {
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1"
    }
    
    prodotti = []
    asins_visti = set()
    session = requests.Session(impersonate="chrome")

    try:
        response = session.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Cerca sia i risultati standard che i blocchi griglia delle offerte eventi
            items = soup.find_all("div", {"data-component-type": "s-search-result"})
            if not items:
                items = soup.find_all("div", attrs={"data-asin": True})

            for item in items:
                if len(prodotti) >= item_count:
                    break
                asin = item.get("data-asin", "").strip()
                if not asin or len(asin) != 10 or asin in asins_visti:
                    continue

                item_text = item.text.lower()
                if "non disponibile" in item_text:
                    continue

                prezzo_prodotto = 0.0
                price_whole = item.find("span", {"class": "a-price-whole"})
                price_fraction = item.find("span", {"class": "a-price-fraction"})
                
                if price_whole:
                    whole_clean = price_whole.text.replace(".", "").replace(",", "").strip()
                    fraction_clean = price_fraction.text.strip() if price_fraction else "00"
                    try:
                        prezzo_prodotto = float(f"{whole_clean}.{fraction_clean}")
                    except ValueError:
                        prezzo_prodotto = 0.0
                else:
                    price_off = item.find("span", {"class": "a-offscreen"})
                    if price_off:
                        try:
                            clean_p = price_off.text.replace("€", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
                            prezzo_prodotto = float(clean_p)
                        except ValueError:
                            prezzo_prodotto = 0.0

                if prezzo_prodotto <= 0.0:
                    continue

                title_tag = item.find("h2") or item.find("span", {"class": "a-size-base-plus"})
                titolo_grezzo = title_tag.get_text(strip=True) if title_tag else "Offerta Lampo Amazon"
                titolo_completo = pulisci_titolo_descrizione(titolo_grezzo)

                img_tag = item.find("img", {"class": "s-image"})
                immagine_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else "https://via.placeholder.com/400"

                asins_visti.add(asin)
                link_affiliato = f"https://www.amazon.it/dp/{asin}?tag={PARTNER_TAG}"

                prodotti.append({
                    "asin": asin,
                    "titolo": titolo_completo,
                    "prezzo_finale": prezzo_prodotto,
                    "prezzo_iniziale": prezzo_prodotto,
                    "sconto": "",
                    "info_spedizione": "Spedizione gratuita",
                    "is_sped_gratis": True,
                    "voto_medio": 4.8,
                    "num_recensioni": 540,
                    "immagine_url": immagine_url,
                    "link_affiliato": link_affiliato
                })
    except Exception as e:
        print(f"Errore recupero deals: {e}")

    return prodotti

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
    termini = []
    clean_keyword = keyword.strip()
    asin_url_match = re.search(r'/(?:dp|gp/product|d)/([A-Z0-9]{10})', clean_keyword, re.IGNORECASE)
    if asin_url_match:
        clean_keyword = asin_url_match.group(1)

    if sottocategoria and sottocategoria != "Tutte":
        termini.append(sottocategoria)
    elif categoria:
        termini.append(categoria)
        
    if clean_keyword:
        termini.append(clean_keyword)
        
    query_str = " ".join(termini) if termini else "offerte"
    query_encoded = urllib.parse.quote_plus(query_str)
    
    sort_code = SORT_MAPPINGS.get(sort_type, "price-asc-rank")
    base_url = f"https://www.amazon.it/s?k={query_encoded}&s={sort_code}"

    if min_price is not None and min_price > 0:
        base_url += f"&low-price={int(min_price)}"

    if max_price is not None and max_price > 0:
        base_url += f"&high-price={int(max_price)}"

    headers = {
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1"
    }

    prodotti = []
    asins_visti = set()
    page_num = 1
    max_pages = max(15, (item_count // 4) + 6)
    session = requests.Session(impersonate="chrome")

    try:
        while len(prodotti) < item_count and page_num <= max_pages:
            current_url = f"{base_url}&page={page_num}"
            response = session.get(current_url, headers=headers, timeout=15)

            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("div", {"data-component-type": "s-search-result"})

            if not items:
                items = [div for div in soup.find_all("div", attrs={"data-asin": True}) if div.get("data-asin", "").strip()]

            if not items:
                break

            for item in items:
                if len(prodotti) >= item_count:
                    break

                asin = item.get("data-asin", "").strip()
                if not asin or asin in asins_visti:
                    continue

                item_text = item.text.lower()
                if "non disponibile" in item_text or "attualmente non disponibile" in item_text:
                    continue

                is_sped_gratis = verifica_se_spedizione_gratuita(item, item_text)
                if solo_spedizione_gratuita and not is_sped_gratis:
                    continue

                prezzo_prodotto = 0.0
                price_whole = item.find("span", {"class": "a-price-whole"})
                price_fraction = item.find("span", {"class": "a-price-fraction"})
                
                if price_whole:
                    whole_clean = price_whole.text.replace(".", "").replace(",", "").strip()
                    fraction_clean = price_fraction.text.strip() if price_fraction else "00"
                    try:
                        prezzo_prodotto = float(f"{whole_clean}.{fraction_clean}")
                    except ValueError:
                        prezzo_prodotto = 0.0
                else:
                    price_off = item.find("span", {"class": "a-offscreen"})
                    if price_off:
                        try:
                            clean_p = price_off.text.replace("€", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
                            prezzo_prodotto = float(clean_p)
                        except ValueError:
                            prezzo_prodotto = 0.0

                if prezzo_prodotto <= 0.0:
                    continue

                if min_price is not None and min_price > 0 and prezzo_prodotto < min_price:
                    continue

                if max_price is not None and max_price > 0 and prezzo_prodotto > max_price:
                    continue

                costo_spedizione, info_spedizione = estrai_costo_spedizione(item)

                voto_medio = 4.8
                num_recensioni = 765
                
                rating_tag = item.find("span", {"class": "a-icon-alt"}) or item.find("i", {"class": re.compile(r"a-icon-star")})
                if rating_tag:
                    m_v = re.search(r'(\d+[.,]\d+)', rating_tag.text)
                    if m_v:
                        try:
                            voto_medio = float(m_v.group(1).replace(",", "."))
                        except ValueError:
                            voto_medio = 4.8

                rev_tag = item.find("span", {"class": re.compile(r"s-underline-text")}) or item.find("a", {"href": re.compile(r"#customerReviews")})
                if rev_tag:
                    m_r = re.search(r'([\d.,]+)', rev_tag.text)
                    if m_r:
                        c_r = m_r.group(1).replace(".", "").replace(",", "").strip()
                        if c_r.isdigit():
                            num_recensioni = int(c_r)

                title_tag = item.find("h2")
                titolo_grezzo = ""
                if title_tag:
                    titolo_grezzo = title_tag.get_text(strip=True)
                if not titolo_grezzo:
                    img_search = item.find("img", {"class": "s-image"})
                    titolo_grezzo = img_search.get("alt", "").strip() if img_search else "Prodotto Amazon"

                titolo_completo = pulisci_titolo_descrizione(titolo_grezzo)

                img_tag = item.find("img", {"class": "s-image"})
                immagine_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else "https://via.placeholder.com/400"

                prezzo_iniziale = prezzo_prodotto
                basis_price = item.find("span", {"class": "a-price", "data-a-strike": "true"}) or item.find("span", {"class": "a-text-price"})

                if basis_price:
                    basis_offscreen = basis_price.find("span", {"class": "a-offscreen"})
                    if basis_offscreen:
                        text_price = basis_offscreen.text.replace("€", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
                        try:
                            prezzo_iniziale = float(text_price)
                        except ValueError:
                            prezzo_iniziale = prezzo_prodotto

                sconto_val = 0
                if prezzo_iniziale > prezzo_prodotto and prezzo_iniziale > 0:
                    sconto_val = int(round(((prezzo_iniziale - prezzo_prodotto) / prezzo_iniziale) * 100))
                
                if sconto_val < min_discount or (max_discount is not None and sconto_val > max_discount):
                    continue

                asins_visti.add(asin)
                sconto_perc = f"-{sconto_val}%" if sconto_val > 0 else ""
                link_affiliato = f"https://www.amazon.it/dp/{asin}?tag={PARTNER_TAG}"

                prodotti.append({
                    "asin": asin,
                    "titolo": titolo_completo,
                    "costo_spedizione": costo_spedizione,
                    "info_spedizione": info_spedizione,
                    "is_sped_gratis": is_sped_gratis,
                    "prezzo_iniziale": prezzo_iniziale,
                    "prezzo_finale": prezzo_prodotto,
                    "sconto": sconto_perc,
                    "sconto_val": sconto_val,
                    "voto_medio": voto_medio,
                    "num_recensioni": num_recensioni,
                    "descrizione": titolo_completo,
                    "immagine_url": immagine_url,
                    "link_affiliato": link_affiliato
                })

            page_num += 1

    except Exception as e:
        print(f"Errore Scraping: {e}")

    if not prodotti and solo_spedizione_gratuita and clean_keyword:
        return ottieni_offerte_avanzate(
            categoria=categoria,
            sottocategoria=sottocategoria,
            keyword=keyword,
            sort_type=sort_type,
            solo_spedizione_gratuita=False,
            min_price=min_price,
            max_price=max_price,
            min_discount=min_discount,
            max_discount=max_discount,
            item_count=item_count
        )

    return prodotti
