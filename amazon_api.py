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

def estrai_costo_spedizione(item_tag):
    testo_completo = item_tag.text

    match_consegna_a = re.search(r'consegna\s+a\s*€?\s*(\d+[.,]\d{2})|consegna\s+a\s*(\d+[.,]\d{2})\s*€', testo_completo, re.IGNORECASE)
    if match_consegna_a:
        val_str = next(v for v in match_consegna_a.groups() if v is not None)
        try:
            costo = float(val_str.replace(",", "."))
            return costo, f"Consegna a €{costo:.2f}"
        except ValueError:
            pass

    if any(k in testo_completo.lower() for k in ["consegna senza costi aggiuntivi", "consegna gratuita", "spedizione gratuita", "prime"]):
        return 0.0, "Consegna gratuita"

    match_generico = re.search(r'(?:€\s*(\d+[.,]\d{2})\s*di\s*spedizione)|(?:(\d+[.,]\d{2})\s*€\s*di\s*spedizione)|(?:spedizione\s*[:a]\s*€?\s*(\d+[.,]\d{2}))', testo_completo, re.IGNORECASE)
    if match_generico:
        val_str = next(v for v in match_generico.groups() if v is not None)
        try:
            costo = float(val_str.replace(",", "."))
            return costo, f"Consegna a €{costo:.2f}"
        except ValueError:
            pass

    return 0.0, "Consegna non specificata"

def ottieni_offerte_avanzate(categoria="", sottocategoria="", keyword="", sort_type="Prezzo: dal più basso", min_price=None, max_price=None, min_discount=0, item_count=10):
    termini = []
    if sottocategoria and sottocategoria != "Tutte":
        termini.append(sottocategoria)
    elif categoria:
        termini.append(categoria)
        
    if keyword.strip():
        termini.append(keyword.strip())
        
    query_str = " ".join(termini) if termini else "offerte"
    query_encoded = urllib.parse.quote_plus(query_str)
    
    sort_code = SORT_MAPPINGS.get(sort_type, "price-asc-rank")
    base_url = f"https://www.amazon.it/s?k={query_encoded}&s={sort_code}"
    
    # Parametri URL di Amazon in Euro interi (senza moltiplicare per 100)
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
    max_pages = (item_count // 15) + 4
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

                # Estrazione Prezzo Finale
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

                # Controllo rigoroso del range di prezzo
                if min_price is not None and min_price > 0 and prezzo_prodotto < min_price:
                    continue

                if max_price is not None and max_price > 0 and prezzo_prodotto > max_price:
                    continue

                item_text = item.text.lower()
                if "non disponibile" in item_text or "attualmente non disponibile" in item_text:
                    continue

                costo_spedizione, info_spedizione = estrai_costo_spedizione(item)

                title_tag = item.find("h2")
                titolo_completo = ""
                if title_tag:
                    titolo_completo = title_tag.get_text(strip=True)
                if not titolo_completo:
                    img_search = item.find("img", {"class": "s-image"})
                    titolo_completo = img_search.get("alt", "").strip() if img_search else "Prodotto Amazon"

                img_tag = item.find("img", {"class": "s-image"})
                immagine_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else "https://via.placeholder.com/400"

                # Prezzo di listino e calcolo sconto
                prezzo_iniziale = prezzo_prodotto
                basis_price = item.find("span", {"class": "a-price", "data-a-strike": "true"})
                if not basis_price:
                    basis_price = item.find("span", {"class": "a-text-price"})

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
                
                if sconto_val < min_discount:
                    continue

                asins_visti.add(asin)
                sconto_perc = f"-{sconto_val}%" if sconto_val > 0 else ""
                link_affiliato = f"https://www.amazon.it/dp/{asin}?tag={PARTNER_TAG}"

                prodotti.append({
                    "asin": asin,
                    "titolo": titolo_completo,
                    "costo_spedizione": costo_spedizione,
                    "info_spedizione": info_spedizione,
                    "prezzo_iniziale": prezzo_iniziale,
                    "prezzo_finale": prezzo_prodotto,
                    "sconto": sconto_perc,
                    "sconto_val": sconto_val,
                    "descrizione": titolo_completo,
                    "immagine_url": immagine_url,
                    "link_affiliato": link_affiliato
                })

            page_num += 1

    except Exception as e:
        print(f"Errore Scraping: {e}")

    return prodotti
