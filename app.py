import streamlit as st
import urllib.parse
from amazon_api import ottieni_offerte_avanzate, SORT_MAPPINGS
from preferiti_db import ottieni_tutti_preferiti, aggiungi_preferito, rimuovi_preferito

st.set_page_config(page_title="Scaladeiturchi Offerte Amazon", layout="wide")

st.markdown("""
<style>
    /* Card Container Principale Glassmorphism */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, #111827 0%, #1e293b 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
        padding: 8px !important;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(59, 130, 246, 0.6) !important;
    }

    /* Pulsante Stellina Preferiti */
    div[data-testid="stButton"] button[key^="fav_"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        font-size: 1.4rem !important;
        color: #facc15 !important;
        cursor: pointer;
        box-shadow: none !important;
        min-height: auto !important;
        line-height: 1 !important;
    }

    /* Uniformazione Immagine Prodotto */
    .product-img-wrapper {
        width: 100%;
        height: 165px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        overflow: hidden;
        padding: 4px;
    }

    .product-img-wrapper img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        display: block;
        margin: auto;
    }

    /* Titolo / Descrizione a 4 righe in Blu Scuro */
    .deal-title {
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        line-height: 1.35 !important;
        color: #2563eb !important;
        margin-bottom: 6px !important;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 5.1em;
    }

    /* Spedizione / Consegna a Pagamento (Arancione Chiaro) */
    .shipping-box {
        display: inline-flex;
        align-items: center;
        background: rgba(249, 115, 22, 0.2) !important;
        color: #fb923c !important;
        border: 1px solid rgba(251, 146, 60, 0.45) !important;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.78rem !important;
        font-weight: 700;
        margin-bottom: 6px !important;
        width: fit-content;
    }

    /* Spedizione / Consegna Gratuita (Verde Chiaro) */
    .shipping-free {
        display: inline-flex;
        align-items: center;
        background: rgba(34, 197, 94, 0.2) !important;
        color: #4ade80 !important;
        border: 1px solid rgba(74, 222, 128, 0.45) !important;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.78rem !important;
        font-weight: 700;
        margin-bottom: 6px !important;
        width: fit-content;
    }

    /* Contenitore Rigo Prezzo */
    .price-container-styled {
        display: flex;
        align-items: baseline;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 8px !important;
    }

    .deal-badge {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: #ffffff;
        padding: 1px 5px;
        border-radius: 3px;
        font-weight: 800;
        font-size: 0.82rem !important;
    }

    /* Scritta Prezzo Finale in Blu Elettrico */
    .deal-price-final {
        font-size: 1.45rem !important;
        font-weight: 900 !important;
        color: #3b82f6 !important;
        letter-spacing: -0.5px;
        text-shadow: 0 1px 6px rgba(59, 130, 246, 0.35);
    }

    /* Prezzo Precedente in Blu Pastello */
    .deal-price-old {
        font-size: 0.88rem !important;
        color: #93c5fd !important;
        opacity: 0.75;
        text-decoration: line-through;
        font-weight: 500;
    }

    /* Contenitore Pulsanti */
    .action-buttons-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 4px;
    }

    .buy-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #ffd814;
        color: #0f1111 !important;
        font-size: 0.90rem !important;
        font-weight: 700 !important;
        text-decoration: none !important;
        padding: 5px 14px;
        border-radius: 14px;
        border: 1px solid #fcd200;
        text-align: center;
        flex: 1;
    }

    .buy-btn:hover {
        background-color: #f7ca00;
        color: #0f1111 !important;
    }

    .share-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: #ffffff !important;
        font-size: 0.90rem !important;
        font-weight: 700 !important;
        padding: 5px 12px;
        border-radius: 14px;
        border: 1px solid #38bdf8;
        cursor: pointer;
        flex: 1;
        box-shadow: 0 2px 5px rgba(2, 132, 199, 0.3);
    }

    .share-btn:hover {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
        color: #ffffff !important;
    }

    /* Adattamento Responsive Schermi Smartphone e Tablet */
    @media (max-width: 900px) {
        div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
    }
</style>
""", unsafe_allow_html=True)

CATEGORIE = {
    "🛍️ Abbigliamento, Scarpe e Accessori (Moda)": [
        "Abbigliamento (Uomo, Donna, Bambini, Neonati)",
        "Scarpe e borse",
        "Orologi",
        "Gioielli",
        "Valigeria e accessori da viaggio"
    ],
    "🔌 Elettronica e Informatica": [
        "Informatica (PC, Laptop, Componenti, Monitor)",
        "Elettronica (TV, Home Cinema, Audio, Fotocamere)",
        "Telefonia (Smartphone, Smartwatch, Accessori)",
        "Accessori per l'elettronica",
        "Grandi elettrodomestici (Frigoriferi, Lavatrici, Forni)"
    ],
    "🏡 Casa, Arredamento e Fai da Te": [
        "Casa e cucina (Arredamento, Tessili, Utensili, Stoviglie)",
        "Fai da te (Utensileria, Ferramenta, Materiale elettrico)",
        "Giardino e giardinaggio (Arredo giardino, Piante, Tagliaerba)",
        "Illuminazione (Lampadine, Lampade da interno ed esterno)"
    ],
    "🧸 Giochi, Prima Infanzia e Animali": [
        "Giochi e giocattoli",
        "Prima infanzia (Passeggini, Seggiolini, Cura del neonato)",
        "Prodotti per animali domestici (Cibo e accessori per cani, gatti, ecc.)"
    ],
    "🧴 Bellezza, Salute e Spesa": [
        "Alimentari e cura della casa (Cibo, Bevande, Prodotti per la pulizia)",
        "Bellezza (Make-up, Cura della pelle, Profumi, Cura dei capelli)",
        "Salute e cura della persona (Integratori, Benessere, Rasatura)"
    ],
    "⚽ Sport, Tempo Libero e Motori": [
        "Sport e tempo libero (Abbigliamento sportivo, Attrezzatura fitness, Camping)",
        "Auto e Moto (Pezzi di ricambio, Accessori, Liquidi e olii)"
    ],
    "📚 Libri, Media e Intrattenimento": [
        "Libri (Cartacei)",
        "Kindle Store (eBook eReader)",
        "CD e Vinili",
        "Videogiochi (Console, Giochi PC, PlayStation, Xbox, Nintendo)",
        "Film e TV (DVD e Blu-Ray)"
    ],
    "🏭 Categorie Speciali e Business": [
        "Commercio, Industria e Scienza (Forniture mediche, Stampa 3D)",
        "Strumenti musicali (Chitarre, Tastiere, Attrezzatura da registrazione)",
        "Handmade (Prodotti fatti a mano da artigiani)",
        "Strumenti e prodotti per ufficio / Cancelleria"
    ]
}

if "preferiti_asin" not in st.session_state:
    salvati = ottieni_tutti_preferiti()
    st.session_state.preferiti_asin = {p["asin"]: p for p in salvati}

if "offerte" not in st.session_state:
    st.session_state.offerte = []

st.title("Scaladeiturchi Offerte Amazon")

tab_cerca, tab_preferiti = st.tabs(["🔍 Cerca Offerte", f"⭐ Preferiti ({len(st.session_state.preferiti_asin)})"])

# --- RENDERING CARD PRODOTTO ---
def render_product_card(p, tab_key="main"):
    with st.container(border=True):
        c_star, c_img, c_txt = st.columns([0.25, 1.35, 2.4])
        
        is_fav = p["asin"] in st.session_state.preferiti_asin
        star_icon = "⭐" if is_fav else "☆"

        with c_star:
            if st.button(star_icon, key=f"fav_{tab_key}_{p['asin']}", help="Aggiungi o rimuovi dai preferiti"):
                if is_fav:
                    rimuovi_preferito(p["asin"])
                    st.session_state.preferiti_asin.pop(p["asin"], None)
                else:
                    aggiungi_preferito(p)
                    st.session_state.preferiti_asin[p["asin"]] = p
                st.rerun()

        with c_img:
            img_url = p.get('immagine_url', '')
            st.markdown(
                f"<div class='product-img-wrapper'><img src='{img_url}' alt='prodotto'></div>",
                unsafe_allow_html=True
            )

        with c_txt:
            titolo = p.get('titolo', 'Prodotto Amazon')
            st.markdown(f"<div class='deal-title'>{titolo}</div>", unsafe_allow_html=True)
            
            # Spedizione
            if p.get('info_spedizione'):
                is_free = "gratuit" in p['info_spedizione'].lower() or p.get('costo_spedizione', 0.0) == 0.0
                ship_class = "shipping-free" if is_free else "shipping-box"
                st.markdown(f"<div class='{ship_class}'>🚚 {p['info_spedizione']}</div>", unsafe_allow_html=True)

            # Prezzo e Sconto
            badge_html = f"<span class='deal-badge'>{p['sconto']}</span>" if p.get('sconto') else ""
            old_price_html = f"<span class='deal-price-old'>da €{p['prezzo_iniziale']:.2f}</span>" if p['prezzo_iniziale'] > p['prezzo_finale'] else ""

            # Condivisione sicura multipiattaforma
            safe_title = titolo.replace("'", " ").replace('"', ' ').replace("\n", " ").strip()
            link = p.get('link_affiliato', '')
            share_text = f"Guarda questa offerta: {safe_title} a €{p['prezzo_finale']:.2f}!"
            wa_fallback_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_text + ' ' + link)}"
            
            share_js = (
                f"if(navigator.share){{"
                f"navigator.share({{title:'{safe_title}',text:'{share_text}',url:'{link}'}}).catch((e)=>console.log(e));"
                f"}}else{{"
                f"window.open('{wa_fallback_url}','_blank');"
                f"}}return false;"
            )

            st.markdown(
                f"<div class='price-container-styled'>"
                f"{badge_html}"
                f"<span class='deal-price-final'>€{p['prezzo_finale']:.2f}</span>"
                f"{old_price_html}"
                f"</div>"
                f"<div class='action-buttons-row'>"
                f"<a href='{link}' target='_blank' class='buy-btn'>🛒 Acquista</a>"
                f"<button onclick=\"{share_js}\" class='share-btn'>🔗 Condividi</button>"
                f"</div>",
                unsafe_allow_html=True
            )

# --- TAB 1: RICERCA ---
with tab_cerca:
    keyword_libera = st.text_input(
        "🔍 Ricerca Testuale Diretta (Prioritaria):",
        placeholder="Es. cuffie bluetooth, friggitrice ad aria, smartwatch..."
    )

    col_cat, col_subcat = st.columns(2)
    with col_cat:
        cat_scelta = st.selectbox("Categoria Principale (se non usi la ricerca testuale):", list(CATEGORIE.keys()))
    with col_subcat:
        sottocategorie_disponibili = ["Tutte"] + CATEGORIE[cat_scelta]
        subcat_scelta = st.selectbox("Sottocategoria:", sottocategorie_disponibili)

    col_sort, col_pmax, col_disc = st.columns([1.5, 1, 1])
    with col_sort:
        opzioni_ordinamento = list(SORT_MAPPINGS.keys())
        default_index = opzioni_ordinamento.index("Prezzo: dal più basso") if "Prezzo: dal più basso" in opzioni_ordinamento else 0
        ranking_scelto = st.selectbox("Ordinamento:", opzioni_ordinamento, index=default_index)

    with col_pmax:
        prezzo_max = st.number_input("Prezzo Max (€):", min_value=0.0, value=0.0, step=5.0, help="0 = Nessun limite")
    with col_disc:
        sconto_minimo = st.slider("Sconto Minimo (%):", min_value=0, max_value=80, value=0, step=5)

    b1, b2, b3, b4, b5 = st.columns(5)
    with b1:
        btn_10 = st.button("🚀 Top 10", type="primary", use_container_width=True)
    with b2:
        btn_20 = st.button("🚀 Top 20", use_container_width=True)
    with b3:
        btn_30 = st.button("🚀 Top 30", use_container_width=True)
    with b4:
        btn_50 = st.button("🚀 Top 50", use_container_width=True)
    with b5:
        btn_100 = st.button("🚀 Top 100", use_container_width=True)

    target_items = None
    if btn_10:
        target_items = 10
    elif btn_20:
        target_items = 20
    elif btn_30:
        target_items = 30
    elif btn_50:
        target_items = 50
    elif btn_100:
        target_items = 100

    if target_items is not None:
        with st.spinner(f"Estrazione dei Top {target_items} prodotti in corso..."):
            usa_testo = bool(keyword_libera.strip())
            cat_pulita = "" if usa_testo else cat_scelta.split(" ", 1)[-1]
            subcat_pulita = "" if usa_testo or subcat_scelta == "Tutte" else subcat_scelta
            
            risultati = ottieni_offerte_avanzate(
                categoria=cat_pulita,
                sottocategoria=subcat_pulita,
                keyword=keyword_libera.strip(),
                sort_type=ranking_scelto,
                max_price=prezzo_max if prezzo_max > 0 else None,
                min_discount=sconto_minimo,
                item_count=target_items
            )
            
            if risultati:
                st.session_state.offerte = risultati
                st.rerun()
            else:
                st.warning("Nessun prodotto trovato con i filtri selezionati.")

    if st.session_state.offerte:
        st.divider()
        for idx in range(0, len(st.session_state.offerte), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(st.session_state.offerte[idx], tab_key="search")
            if idx + 1 < len(st.session_state.offerte):
                with col_r:
                    render_product_card(st.session_state.offerte[idx + 1], tab_key="search")

# --- TAB 2: PREFERITI ---
with tab_preferiti:
    lista_preferiti = list(st.session_state.preferiti_asin.values())
    if not lista_preferiti:
        st.info("Nessun prodotto nei preferiti. Clicca sulla stellina (☆) accanto a qualsiasi prodotto per salvarlo qui!")
    else:
        st.markdown(f"Hai **{len(lista_preferiti)}** prodotti salvati nella tua lista privata:")
        st.write("")
        for idx in range(0, len(lista_preferiti), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(lista_preferiti[idx], tab_key="fav_tab")
            if idx + 1 < len(lista_preferiti):
                with col_r:
                    render_product_card(lista_preferiti[idx + 1], tab_key="fav_tab")