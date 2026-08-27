import urllib.parse
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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

def ottieni_offerte_avanzate(categoria="", sottocategoria="", keyword="", sort_type="Prezzo: dal più basso", max_price=None, min_discount=0, item_count=10):
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
    
    if max_price and max_price > 0:
        prezzo_centesimi = int(max_price * 100)
        base_url += f"&low-price=0&high-price={prezzo_centesimi}"

    prodotti = []
    asins_visti = set()
    page_num = 1
    max_pages = (item_count // 15) + 3

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                locale="it-IT",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            while len(prodotti) < item_count and page_num <= max_pages:
                current_url = f"{base_url}&page={page_num}"
                try:
                    page.goto(current_url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_selector("div[data-component-type='s-search-result']", timeout=10000)
                except Exception:
                    break

                content = page.content()
                soup = BeautifulSoup(content, "html.parser")
                items = soup.find_all("div", {"data-component-type": "s-search-result"})

                if not items:
                    break

                for item in items:
                    if len(prodotti) >= item_count:
                        break

                    asin = item.get("data-asin", "").strip()
                    if not asin or asin in asins_visti:
                        continue

                    price_whole = item.find("span", {"class": "a-price-whole"})
                    price_fraction = item.find("span", {"class": "a-price-fraction"})
                    prezzo_prodotto = 0.0
                    if price_whole:
                        whole_clean = price_whole.text.replace(".", "").replace(",", "").strip()
                        fraction_clean = price_fraction.text.strip() if price_fraction else "00"
                        try:
                            prezzo_prodotto = float(f"{whole_clean}.{fraction_clean}")
                        except ValueError:
                            prezzo_prodotto = 0.0

                    if prezzo_prodotto <= 0.0:
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

                    prezzo_iniziale = prezzo_prodotto
                    basis_price = item.find("span", {"class": "a-price", "data-a-strike": "true"})
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

                    if max_price and max_price > 0 and prezzo_prodotto > max_price:
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

            browser.close()

    except Exception as e:
        print(f"Errore Scraping: {e}")

    return prodotti