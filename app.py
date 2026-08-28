import streamlit as st
import urllib.parse
from amazon_api import ottieni_offerte_avanzate, SORT_MAPPINGS
from preferiti_db import ottieni_tutti_preferiti, aggiungi_preferito, rimuovi_preferito

st.set_page_config(page_title="Scaladeiturchi Offerte Amazon", layout="wide")

st.markdown("""
<style>
    /* Nasconde header e menu superiore */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

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

    /* Immagine Prodotto */
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

    /* Titolo / Descrizione in Blu Scuro */
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

    /* Spedizione */
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

    .deal-price-final {
        font-size: 1.45rem !important;
        font-weight: 900 !important;
        color: #3b82f6 !important;
        letter-spacing: -0.5px;
        text-shadow: 0 1px 6px rgba(59, 130, 246, 0.35);
    }

    .deal-price-old {
        font-size: 0.88rem !important;
        color: #93c5fd !important;
        opacity: 0.75;
        text-decoration: line-through;
        font-weight: 500;
    }

    /* Pulsante Acquista Amazon */
    .buy-btn-full {
        display: block;
        width: 100%;
        background-color: #ffd814;
        color: #0f1111 !important;
        font-size: 0.92rem !important;
        font-weight: 800 !important;
        text-decoration: none !important;
        padding: 7px 12px;
        border-radius: 10px;
        border: 1px solid #fcd200;
        text-align: center;
        margin-bottom: 8px;
        transition: background-color 0.15s ease;
    }

    .buy-btn-full:hover {
        background-color: #f7ca00;
        color: #0f1111 !important;
    }

    /* Griglia Icone Social */
    .social-share-row {
        display: flex;
        align-items: center;
        gap: 6px;
        justify-content: flex-start;
        flex-wrap: wrap;
    }

    .share-icon-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 8px;
        text-decoration: none !important;
        cursor: pointer;
        border: none;
        transition: transform 0.15s ease, opacity 0.15s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }

    .share-icon-btn:hover {
        transform: translateY(-2px);
        opacity: 0.92;
    }

    .share-icon-btn svg {
        width: 20px;
        height: 20px;
        display: block;
    }

    /* Colori Social */
    .btn-wa { background-color: #25D366; }
    .btn-fb { background-color: #1877F2; }
    .btn-gmail { background-color: #EA4335; }
    .btn-ig { background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); }
    .btn-tg { background-color: #229ED9; }
    .btn-copy { background-color: #475569; }

    /* Responsive */
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

if "last_target_items" not in st.session_state:
    st.session_state.last_target_items = 10

if "auto_search_triggered" not in st.session_state:
    st.session_state.auto_search_triggered = False

def trigger_search():
    st.session_state.auto_search_triggered = True

st.title("Scaladeiturchi Offerte Amazon")

tab_cerca, tab_preferiti = st.tabs(["🔍 Cerca Offerte", f"⭐ Preferiti ({len(st.session_state.preferiti_asin)})"])

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
            
            # Info Spedizione
            if p.get('info_spedizione'):
                is_free = "gratuit" in p['info_spedizione'].lower() or p.get('costo_spedizione', 0.0) == 0.0
                ship_class = "shipping-free" if is_free else "shipping-box"
                st.markdown(f"<div class='{ship_class}'>🚚 {p['info_spedizione']}</div>", unsafe_allow_html=True)

            # Prezzo e Sconto
            badge_html = f"<span class='deal-badge'>{p['sconto']}</span>" if p.get('sconto') else ""
            old_price_html = f"<span class='deal-price-old'>da €{p['prezzo_iniziale']:.2f}</span>" if p['prezzo_iniziale'] > p['prezzo_finale'] else ""

            # Preparazione URL Social
            safe_title = titolo.replace("'", " ").replace('"', ' ').replace("\n", " ").strip()
            link = p.get('link_affiliato', '')
            share_msg = f"🔥 Offerta Amazon: {safe_title}\n💰 Prezzo: €{p['prezzo_finale']:.2f}\n👉 Acquista qui: {link}"

            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_msg)}"
            fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(link)}"
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su={urllib.parse.quote('Offerta Amazon: ' + safe_title)}&body={urllib.parse.quote(share_msg)}"
            ig_url = "https://www.instagram.com/"
            tg_url = f"https://t.me/share/url?url={urllib.parse.quote(link)}&text={urllib.parse.quote(f'🔥 {safe_title} a €{p['prezzo_finale']:.2f}!')}"

            # SVGs Ufficiali
            svg_wa = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.842-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>'
            svg_fb = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>'
            svg_gmail = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.272H1.636A1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"/></svg>'
            svg_ig = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'
            svg_tg = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18.847-1.12 5.075-1.597 7.214-.202.906-.596 1.209-.974 1.239-.822.065-1.446-.533-2.242-1.055-1.246-.816-1.95-1.324-3.161-2.122-1.4-.923-.493-1.432.305-2.261.209-.217 3.843-3.521 3.914-3.823.009-.038.017-.18-.067-.255-.084-.075-.208-.05-.298-.029-.127.029-2.155 1.371-6.082 4.022-.575.396-1.096.589-1.562.579-.515-.011-1.506-.291-2.244-.531-.905-.295-1.624-.45-1.562-.951.032-.261.393-.529 1.08-.804 4.234-1.844 7.059-3.06 8.475-3.649 4.037-1.68 4.876-1.972 5.424-1.982.121-.002.391.028.566.17.148.12.189.282.208.396.019.114.043.37.024.571z"/></svg>'
            svg_copy = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>'

            copy_action = f"navigator.clipboard.writeText('{link}').then(function(){{alert('Link copiato negli appunti!');}});"

            st.markdown(
                f"<div class='price-container-styled'>"
                f"{badge_html}"
                f"<span class='deal-price-final'>€{p['prezzo_finale']:.2f}</span>"
                f"{old_price_html}"
                f"</div>"
                f"<a href='{link}' target='_blank' class='buy-btn-full'>🛒 Acquista su Amazon</a>"
                f"<div class='social-share-row'>"
                f"<a href='{wa_url}' target='_blank' class='share-icon-btn btn-wa' title='Condividi su WhatsApp'>{svg_wa}</a>"
                f"<a href='{fb_url}' target='_blank' class='share-icon-btn btn-fb' title='Condividi su Facebook'>{svg_fb}</a>"
                f"<a href='{gmail_url}' target='_blank' class='share-icon-btn btn-gmail' title='Condividi via Gmail'>{svg_gmail}</a>"
                f"<a href='{ig_url}' target='_blank' class='share-icon-btn btn-ig' title='Apri Instagram'>{svg_ig}</a>"
                f"<a href='{tg_url}' target='_blank' class='share-icon-btn btn-tg' title='Condividi su Telegram'>{svg_tg}</a>"
                f"<button onclick=\"{copy_action}\" class='share-icon-btn btn-copy' title='Copia Link'>{svg_copy}</button>"
                f"</div>",
                unsafe_allow_html=True
            )

with tab_cerca:
    keyword_libera = st.text_input(
        "🔍 Ricerca Testuale Diretta (Prioritaria):",
        placeholder="Es. cuffie bluetooth, notebook, friggitrice ad aria...",
        key="keyword_input",
        on_change=trigger_search
    )

    col_cat, col_subcat = st.columns(2)
    with col_cat:
        cat_scelta = st.selectbox("Categoria Principale (se non usi la ricerca testuale):", list(CATEGORIE.keys()))
    with col_subcat:
        sottocategorie_disponibili = ["Tutte"] + CATEGORIE[cat_scelta]
        subcat_scelta = st.selectbox("Sottocategoria:", sottocategorie_disponibili)

    # 5 Colonne: Checkbox Spedizione, Ordinamento, Prezzo Min, Prezzo Max, Sconto Minimo
    col_ship, col_sort, col_pmin, col_pmax, col_disc = st.columns([1.1, 1.3, 1, 1, 1])
    
    with col_ship:
        st.write("")
        st.write("")
        solo_sped_gratis = st.checkbox(
            "🚚 Sped. Gratuita",
            value=False,
            key="check_sped_gratis",
            on_change=trigger_search,
            help="Mostra solo i prodotti con spedizione o consegna gratuita"
        )

    with col_sort:
        opzioni_ordinamento = list(SORT_MAPPINGS.keys())
        default_index = opzioni_ordinamento.index("Prezzo: dal più basso") if "Prezzo: dal più basso" in opzioni_ordinamento else 0
        ranking_scelto = st.selectbox("Ordinamento:", opzioni_ordinamento, index=default_index)

    with col_pmin:
        prezzo_min = st.slider(
            "Prezzo Min (€):",
            min_value=0,
            max_value=500,
            value=0,
            step=5,
            help="0 = Nessun limite minimo",
            key="slider_pmin",
            on_change=trigger_search
        )

    with col_pmax:
        prezzo_max = st.slider(
            "Prezzo Max (€):",
            min_value=0,
            max_value=500,
            value=0,
            step=5,
            help="0 = Nessun limite massimo",
            key="slider_pmax",
            on_change=trigger_search
        )

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
        st.session_state.last_target_items = 10
    elif btn_20:
        target_items = 20
        st.session_state.last_target_items = 20
    elif btn_30:
        target_items = 30
        st.session_state.last_target_items = 30
    elif btn_50:
        target_items = 50
        st.session_state.last_target_items = 50
    elif btn_100:
        target_items = 100
        st.session_state.last_target_items = 100
    elif st.session_state.auto_search_triggered:
        target_items = st.session_state.last_target_items
        st.session_state.auto_search_triggered = False

    if target_items is not None:
        with st.spinner(f"Estrazione dei Top {target_items} prodotti in corso..."):
            usa_testo = bool(keyword_libera.strip())
            cat_pulita = "" if usa_testo else cat_scelta.split(" ", 1)[-1]
            subcat_pulita = "" if usa_testo or subcat_scelta == "Tutte" else subcat_scelta
            
            val_min = float(prezzo_min) if prezzo_min > 0 else None
            val_max = float(prezzo_max) if prezzo_max > 0 else None
            if val_min and val_max and val_min > val_max:
                val_min, val_max = val_max, val_min

            risultati = ottieni_offerte_avanzate(
                categoria=cat_pulita,
                sottocategoria=subcat_pulita,
                keyword=keyword_libera.strip(),
                sort_type=ranking_scelto,
                solo_spedizione_gratuita=solo_sped_gratis,
                min_price=val_min,
                max_price=val_max,
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
