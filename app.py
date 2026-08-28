import streamlit as st
import urllib.parse
from amazon_api import ottieni_offerte_avanzate, SORT_MAPPINGS, calcola_distribuzione_recensioni
from preferiti_db import ottieni_tutti_preferiti, aggiungi_preferito, rimuovi_preferito

st.set_page_config(page_title="Scaladeiturchi Offerte Amazon", layout="wide")

st.markdown("""
<style>
    /* Nasconde header e menu superiore */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Card Container Compatto */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border: 1px solid #dcdfe4 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
        padding: 10px 8px !important;
        margin-bottom: 8px !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #0284c7 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.10) !important;
    }

    /* Immagine Ingrandita a Pieno Spazio */
    .product-img-wrapper-full {
        width: 100%;
        height: 185px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
        border: 1px solid #edf2f7;
        border-radius: 8px;
        overflow: hidden;
        padding: 4px;
    }

    .product-img-wrapper-full img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        display: block;
        margin: auto;
    }

    /* Pulsante Preferiti Stellina */
    div[data-testid="stButton"] button[key^="fav_"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        font-size: 1.45rem !important;
        color: #facc15 !important;
        cursor: pointer;
        box-shadow: none !important;
        min-height: auto !important;
        line-height: 1.3 !important;
    }

    /* Pulsante Acquista */
    .buy-btn-action {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #ffd814;
        color: #0f1111 !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        text-decoration: none !important;
        padding: 6px 10px;
        border-radius: 18px;
        border: 1px solid #fcd200;
        text-align: center;
        width: 100%;
        box-shadow: 0 1px 3px rgba(213, 175, 0, 0.25);
        transition: background-color 0.15s ease;
        white-space: nowrap;
    }

    .buy-btn-action:hover {
        background-color: #f7ca00;
        color: #0f1111 !important;
    }

    /* Titolo in Blu Scuro */
    .deal-title {
        font-size: 0.88rem !important;
        font-weight: 800 !important;
        line-height: 1.3 !important;
        color: #0a2540 !important;
        margin-bottom: 4px !important;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 3.4em;
    }

    /* Rigo Spedizione e Dicitura Prime Ufficiale */
    .delivery-prime-container {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
        margin: 2px 0 4px 0 !important;
    }

    .shipping-badge-text {
        display: inline-flex;
        align-items: center;
        background: rgba(34, 197, 94, 0.10) !important;
        color: #15803d !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        padding: 1px 6px;
        border-radius: 3px;
        font-size: 0.72rem !important;
        font-weight: 700;
    }

    /* Badge Amazon Prime Ufficiale */
    .prime-badge-official {
        display: inline-flex;
        align-items: center;
        font-family: "Amazon Ember", Arial, sans-serif;
        font-size: 0.95rem;
        line-height: 1;
        letter-spacing: -0.4px;
    }

    .prime-check-mark {
        color: #e47911 !important;
        font-size: 1.05rem !important;
        font-style: normal !important;
        font-weight: 900 !important;
        margin-right: 1px;
    }

    .prime-text-cyan {
        color: #00a8e1 !important;
        font-style: italic !important;
        font-weight: 900 !important;
        font-size: 0.96rem !important;
    }

    /* Prezzi */
    .price-container-styled {
        display: flex;
        align-items: baseline;
        gap: 5px;
        flex-wrap: wrap;
        margin: 2px 0 2px 0 !important;
    }

    .deal-badge {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: #ffffff;
        padding: 1px 4px;
        border-radius: 3px;
        font-weight: 800;
        font-size: 0.75rem !important;
    }

    .deal-price-final {
        font-size: 1.30rem !important;
        font-weight: 900 !important;
        color: #0284c7 !important;
        letter-spacing: -0.5px;
    }

    .deal-price-old {
        font-size: 0.80rem !important;
        color: #64748b !important;
        text-decoration: line-through;
        font-weight: 500;
    }

    /* Scheda Feedback */
    .feedback-container {
        font-family: Arial, sans-serif;
        padding: 0 4px;
    }

    .feedback-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #0f1111;
        line-height: 1.15;
        margin-bottom: 2px;
    }

    .feedback-stars-row {
        display: flex;
        align-items: center;
        gap: 5px;
        margin-bottom: 1px;
    }

    .feedback-stars {
        color: #ff6e00;
        font-size: 1.05rem;
        letter-spacing: 0.5px;
        line-height: 1;
    }

    .feedback-score-text {
        font-size: 0.88rem;
        font-weight: 600;
        color: #0f1111;
    }

    .feedback-subcount {
        font-size: 0.78rem;
        color: #565959;
        margin-bottom: 6px;
    }

    .fb-row {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 3px;
    }

    .fb-label {
        width: 48px;
        color: #007185;
        font-size: 0.78rem;
        font-weight: 500;
        white-space: nowrap;
    }

    .fb-bar-bg {
        flex: 1;
        height: 12px;
        background-color: #ffffff;
        border: 1px solid #767676;
        border-radius: 3px;
        overflow: hidden;
        position: relative;
    }

    .fb-bar-fill {
        height: 100%;
        background-color: #ff6e00;
        border-radius: 2px 0 0 2px;
    }

    .fb-pct {
        width: 28px;
        text-align: right;
        color: #007185;
        font-size: 0.78rem;
        font-weight: 500;
    }

    /* Pulsanti Social Verticali */
    .social-share-col {
        display: flex;
        flex-direction: column;
        gap: 4px;
        align-items: center;
        justify-content: center;
    }

    .share-icon-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 27px;
        height: 27px;
        border-radius: 6px;
        text-decoration: none !important;
        cursor: pointer;
        border: none;
        transition: transform 0.15s ease, opacity 0.15s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.10);
    }

    .share-icon-btn:hover {
        transform: scale(1.10);
        opacity: 0.95;
    }

    .share-icon-btn svg {
        width: 15px;
        height: 15px;
        display: block;
    }

    .btn-wa { background-color: #25D366; }
    .btn-fb { background-color: #1877F2; }
    .btn-gmail { background-color: #EA4335; }
    .btn-ig { background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); }
    .btn-tg { background-color: #229ED9; }
    .btn-copy { background-color: #475569; }

    /* Allineamento Orizzontale Inline per i Flag Radio */
    div[data-testid="stRadio"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 10px !important;
        margin-bottom: 4px !important;
    }

    div[data-testid="stRadio"] > label {
        margin-bottom: 0px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        white-space: nowrap !important;
        font-size: 0.85rem !important;
    }

    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
        align-items: center !important;
    }
    
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: #f8fafc !important;
        padding: 3px 8px !important;
        border-radius: 6px !important;
        border: 1px solid #cbd5e1 !important;
        cursor: pointer !important;
        font-size: 0.80rem !important;
        font-weight: 600 !important;
        margin: 0 !important;
        transition: all 0.15s ease !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background: #f1f5f9 !important;
        border-color: #0284c7 !important;
    }

    @media (max-width: 900px) {
        div[data-testid="stRadio"] {
            flex-direction: column !important;
            align-items: flex-start !important;
        }
        .social-share-col {
            flex-direction: row !important;
            justify-content: center !important;
            gap: 6px;
            margin-top: 6px;
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

OPZIONI_SCONTO = {
    "Tutti": 0,
    "-10%": 10,
    "-20%": 20,
    "-30%": 30,
    "-50%": 50,
    "-70%": 70
}

# Inizializzazione Session State
if "preferiti_asin" not in st.session_state:
    salvati = ottieni_tutti_preferiti()
    st.session_state.preferiti_asin = {p["asin"]: p for p in salvati}

if "offerte" not in st.session_state:
    st.session_state.offerte = []

if "last_target_items" not in st.session_state:
    st.session_state.last_target_items = 10

if "auto_search_triggered" not in st.session_state:
    st.session_state.auto_search_triggered = False

if "keyword_input" not in st.session_state:
    st.session_state.keyword_input = ""

if "select_cat" not in st.session_state:
    st.session_state.select_cat = list(CATEGORIE.keys())[0]

def trigger_search():
    st.session_state.auto_search_triggered = True

st.title("Scaladeiturchi Offerte Amazon")

tab_cerca, tab_preferiti = st.tabs(["🔍 Cerca Offerte", f"⭐ Preferiti ({len(st.session_state.preferiti_asin)})"])

def render_product_card(p, tab_key="main"):
    with st.container(border=True):
        col_left, col_center, col_fb, col_social = st.columns([1.2, 1.5, 1.35, 0.3])
        
        is_fav = p["asin"] in st.session_state.preferiti_asin
        star_icon = "⭐" if is_fav else "☆"

        # 1. Colonna Sinistra: Foto Ingrandita
        with col_left:
            img_url = p.get('immagine_url', '')
            st.markdown(
                f"<div class='product-img-wrapper-full'><img src='{img_url}' alt='prodotto'></div>",
                unsafe_allow_html=True
            )

        # 2. Colonna Centrale: Titolo, Prezzi, Prime e sotto [Stellina + Acquista]
        with col_center:
            titolo = p.get('titolo', 'Prodotto Amazon')
            link = p.get('link_affiliato', '')
            st.markdown(f"<div class='deal-title'>{titolo}</div>", unsafe_allow_html=True)
            
            # Prezzi
            badge_html = f"<span class='deal-badge'>{p['sconto']}</span>" if p.get('sconto') else ""
            old_price_html = f"<span class='deal-price-old'>da €{p['prezzo_iniziale']:.2f}</span>" if p['prezzo_iniziale'] > p['prezzo_finale'] else ""

            st.markdown(
                f"<div class='price-container-styled'>"
                f"{badge_html}"
                f"<span class='deal-price-final'>€{p['prezzo_finale']:.2f}</span>"
                f"{old_price_html}"
                f"</div>",
                unsafe_allow_html=True
            )

            # Badge Prime Ufficiale e Spedizione sotto il prezzo
            prime_html = "<span class='prime-badge-official'><span class='prime-check-mark'>✔</span><span class='prime-text-cyan'>prime</span></span>" if p.get("is_prime") else ""
            ship_text = p.get('info_spedizione', 'Consegna senza costi aggiuntivi')
            ship_html = f"<span class='shipping-badge-text'>{ship_text}</span>" if ship_text else ""

            st.markdown(f"<div class='delivery-prime-container'>{prime_html}{ship_html}</div>", unsafe_allow_html=True)

            # Stellina + Tasto Acquista
            c_star_sub, c_buy_sub = st.columns([0.24, 0.76])
            with c_star_sub:
                if st.button(star_icon, key=f"fav_{tab_key}_{p['asin']}", help="Aggiungi o rimuovi dai preferiti"):
                    if is_fav:
                        rimuovi_preferito(p["asin"])
                        st.session_state.preferiti_asin.pop(p["asin"], None)
                    else:
                        aggiungi_preferito(p)
                        st.session_state.preferiti_asin[p["asin"]] = p
                    st.rerun()
            with c_buy_sub:
                st.markdown(f"<a href='{link}' target='_blank' class='buy-btn-action'>🛒 Acquista</a>", unsafe_allow_html=True)

        # 3. Colonna Destra: Scheda Feedback Ufficiale
        with col_fb:
            voto = p.get("voto_medio", 4.8)
            num_val = p.get("num_recensioni", 765)
            distrib = calcola_distribuzione_recensioni(voto, num_val)
            voto_str = f"{voto:.1f}".replace(".", ",")
            stelle_icon = "★" * int(voto) + "☆" * (5 - int(voto))
            
            bar_rows = []
            for s in ["5", "4", "3", "2", "1"]:
                pct = distrib.get(s, 0)
                lbl = f"{s} stell{'e' if s != '1' else 'a'}"
                row_html = (
                    f"<div class='fb-row'>"
                    f"<span class='fb-label'>{lbl}</span>"
                    f"<div class='fb-bar-bg'><div class='fb-bar-fill' style='width: {pct}%;'></div></div>"
                    f"<span class='fb-pct'>{pct}%</span>"
                    f"</div>"
                )
                bar_rows.append(row_html)

            feedback_full_html = (
                f"<div class='feedback-container'>"
                f"<div class='feedback-title'>Recensioni clienti</div>"
                f"<div class='feedback-stars-row'>"
                f"<span class='feedback-stars'>{stelle_icon}</span>"
                f"<span class='feedback-score-text'>{voto_str} su 5</span>"
                f"</div>"
                f"<div class='feedback-subcount'>{num_val} valutazioni globali</div>"
                f"{''.join(bar_rows)}"
                f"</div>"
            )
            st.markdown(feedback_full_html, unsafe_allow_html=True)

        # 4. Colonna Destra Estrema: Pulsanti Social Verticali
        with col_social:
            safe_title = titolo.replace("'", " ").replace('"', ' ').replace("\n", " ").strip()
            share_msg = f"🔥 Offerta Amazon: {safe_title}\n💰 Prezzo: €{p['prezzo_finale']:.2f}\n👉 Acquista qui: {link}"

            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_msg)}"
            fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(link)}"
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su={urllib.parse.quote('Offerta Amazon: ' + safe_title)}&body={urllib.parse.quote(share_msg)}"
            ig_url = "https://www.instagram.com/"
            tg_url = f"https://t.me/share/url?url={urllib.parse.quote(link)}&text={urllib.parse.quote(f'🔥 {safe_title} a €{p['prezzo_finale']:.2f}!')}"

            svg_wa = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.842-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>'
            svg_fb = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>'
            svg_gmail = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.272H1.636A1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"/></svg>'
            svg_ig = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'
            svg_tg = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18.847-1.12 5.075-1.597 7.214-.202.906-.596 1.209-.974 1.239-.822.065-1.446-.533-2.242-1.055-1.246-.816-1.95-1.324-3.161-2.122-1.4-.923-.493-1.432.305-2.261.209-.217 3.843-3.521 3.914-3.823.009-.038.017-.18-.067-.255-.084-.075-.208-.05-.298-.029-.127.029-2.155 1.371-6.082 4.022-.575.396-1.096.589-1.562.579-.515-.011-1.506-.291-2.244-.531-.905-.295-1.624-.45-1.562-.951.032-.261.393-.529 1.08-.804 4.234-1.844 7.059-3.06 8.475-3.649 4.037-1.68 4.876-1.972 5.424-1.982.121-.002.391.028.566.17.148.12.189.282.208.396.019.114.043.37.024.571z"/></svg>'
            svg_copy = '<svg viewBox="0 0 24 24"><path fill="#ffffff" d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>'

            copy_action = f"navigator.clipboard.writeText('{link}').then(function(){{alert('Link copiato negli appunti!');}});"

            st.markdown(
                f"<div class='social-share-col'>"
                f"<a href='{wa_url}' target='_blank' class='share-icon-btn btn-wa' title='WhatsApp'>{svg_wa}</a>"
                f"<a href='{fb_url}' target='_blank' class='share-icon-btn btn-fb' title='Facebook'>{svg_fb}</a>"
                f"<a href='{gmail_url}' target='_blank' class='share-icon-btn btn-gmail' title='Gmail'>{svg_gmail}</a>"
                f"<a href='{ig_url}' target='_blank' class='share-icon-btn btn-ig' title='Instagram'>{svg_ig}</a>"
                f"<a href='{tg_url}' target='_blank' class='share-icon-btn btn-tg' title='Telegram'>{svg_tg}</a>"
                f"<button onclick=\"{copy_action}\" class='share-icon-btn btn-copy' title='Copia Link'>{svg_copy}</button>"
                f"</div>",
                unsafe_allow_html=True
            )

with tab_cerca:
    # Riga 1: Ricerca Testuale, Categoria Principale e Sottocategoria
    col_kw, col_cat, col_subcat = st.columns([1.4, 1.3, 1.3])

    with col_kw:
        keyword_libera = st.text_input(
            "🔍 Ricerca Testuale Diretta:",
            placeholder="Es. cuffie bluetooth, notebook...",
            key="keyword_input",
            on_change=trigger_search
        )

    with col_cat:
        cat_scelta = st.selectbox(
            "Categoria Principale:",
            list(CATEGORIE.keys()),
            key="select_cat",
            on_change=trigger_search
        )

    with col_subcat:
        sottocategorie_disponibili = ["Tutte"] + CATEGORIE[cat_scelta]
        if "select_subcat" not in st.session_state or st.session_state.select_subcat not in sottocategorie_disponibili:
            st.session_state.select_subcat = "Tutte"
        subcat_scelta = st.selectbox(
            "Sottocategoria:",
            sottocategorie_disponibili,
            key="select_subcat",
            on_change=trigger_search
        )

    # Riga 2: Flag Prime + Limiti Prezzo Min/Max
    col_prime, col_pmin, col_pmax = st.columns([0.8, 1.1, 1.1])

    with col_prime:
        st.write("")
        st.write("")
        solo_prime = st.checkbox(
            "✔ Prime",
            value=False,
            key="check_prime",
            on_change=trigger_search,
            help="Mostra solo prodotti idonei ad Amazon Prime"
        )

    with col_pmin:
        prezzo_min = st.number_input(
            "Prezzo Min (€):",
            min_value=0.0,
            value=None,
            step=1.0,
            placeholder="Min...",
            key="input_pmin",
            on_change=trigger_search,
            help="Lascia vuoto per nessun limite minimo"
        )

    with col_pmax:
        prezzo_max = st.number_input(
            "Prezzo Max (€):",
            min_value=0.0,
            value=None,
            step=1.0,
            placeholder="Max...",
            key="input_pmax",
            on_change=trigger_search,
            help="Lascia vuoto per nessun limite massimo"
        )

    # Riga 3: Flag Ordinamento sulla stessa riga
    opzioni_ordinamento = list(SORT_MAPPINGS.keys())
    ranking_scelto = st.radio(
        "🏷️ Ordinamento:",
        opzioni_ordinamento,
        index=0,
        horizontal=True,
        key="radio_sort",
        on_change=trigger_search
    )

    # Riga 4: Flag Sconto Minimo sulla stessa riga
    label_sconto_scelto = st.radio(
        "🔥 Sconto Minimo:",
        list(OPZIONI_SCONTO.keys()),
        index=0,
        horizontal=True,
        key="radio_disc",
        on_change=trigger_search
    )
    sconto_minimo = OPZIONI_SCONTO[label_sconto_scelto]

    # Pulsanti Top Risultati
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
            
            val_min = float(prezzo_min) if (prezzo_min is not None and prezzo_min > 0) else None
            val_max = float(prezzo_max) if (prezzo_max is not None and prezzo_max > 0) else None
            if val_min and val_max and val_min > val_max:
                val_min, val_max = val_max, val_min

            risultati = ottieni_offerte_avanzate(
                categoria=cat_pulita,
                sottocategoria=subcat_pulita,
                keyword=keyword_libera.strip(),
                sort_type=ranking_scelto,
                solo_prime=solo_prime,
                min_price=val_min,
                max_price=val_max,
                min_discount=sconto_minimo,
                item_count=target_items
            )
            
            if risultati:
                st.session_state.offerte = risultati
            else:
                st.session_state.offerte = []
                st.warning("Nessun prodotto trovato con i filtri selezionati.")

    if st.session_state.offerte:
        st.divider()
        for idx in range(0, len(st.session_state.offerte), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(st.session_state.offerte[idx], tab_key=f"search_{idx}")
            if idx + 1 < len(st.session_state.offerte):
                with col_r:
                    render_product_card(st.session_state.offerte[idx + 1], tab_key=f"search_{idx + 1}")

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
                render_product_card(lista_preferiti[idx], tab_key=f"fav_{idx}")
            if idx + 1 < len(lista_preferiti):
                with col_r:
                    render_product_card(lista_preferiti[idx + 1], tab_key=f"fav_{idx + 1}")
