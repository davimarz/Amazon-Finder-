import streamlit as st
import urllib.parse
from amazon_api import ottieni_offerte_avanzate, SORT_MAPPINGS, calcola_distribuzione_recensioni
from preferiti_db import ottieni_tutti_preferiti, aggiungi_preferito, rimuovi_preferito

st.set_page_config(page_title="Scaladeiturchi | Offerte Amazon AI", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
        background-attachment: fixed !important;
        color: #f8fafc !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    .block-container {
        padding: 0.30rem 0.35rem 0.80rem 0.35rem !important;
        max-width: 100% !important;
    }

    /* Tabs compatti */
    div[data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.7) !important;
        padding: 2px 4px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
        display: flex !important;
        width: 100% !important;
    }

    button[data-baseweb="tab"] {
        flex: 1 1 0% !important;
        color: #94a3b8 !important;
        font-weight: 800 !important;
        font-size: 0.80rem !important;
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 6px !important;
        padding: 4px 6px !important;
        min-height: 26px !important;
        height: 26px !important;
        text-align: center !important;
        justify-content: center !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
        border-color: #38bdf8 !important;
    }

    div[data-baseweb="tab-highlight"] { display: none !important; }

    /* Header compatto */
    .hero-title-main {
        font-size: clamp(1.3rem, 4.2vw, 1.8rem);
        font-weight: 900;
        line-height: 1.05;
        margin: 0;
        background: linear-gradient(90deg, #38bdf8 0%, #60a5fa 50%, #93c5fd 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle-box {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: clamp(0.75rem, 2.4vw, 0.90rem);
        font-weight: 700;
        color: #f1f5f9;
        margin: 0;
    }

    .ai-badge {
        background: #0284c7;
        color: #ffffff;
        font-size: 0.68em;
        font-weight: 800;
        padding: 1px 4px;
        border-radius: 4px;
    }

    .hero-author-tag {
        font-size: 0.70rem;
        color: #94a3b8;
        font-weight: 500;
        margin: 0 0 4px 0;
    }

    .hero-author-tag strong { color: #facc15; }

    /* Spaziature verticali ridotte */
    div[data-testid="stVerticalBlock"] > div {
        gap: 2px !important;
    }

    div[data-testid="stMarkdownContainer"] p,
    label[data-testid="stWidgetLabel"] p {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        font-size: 0.72rem !important;
        margin: 0 !important;
        line-height: 1 !important;
    }

    /* Stile Input generico */
    div[data-baseweb="input"] {
        background-color: rgba(15, 23, 42, 0.85) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 6px !important;
        min-height: 30px !important;
        height: 30px !important;
        padding: 0 !important;
    }

    div[data-baseweb="input"] input {
        color: #f8fafc !important;
        font-weight: 600 !important;
        font-size: 0.76rem !important;
        padding: 2px 6px !important;
    }

    /* Riga Ricerca: Campo Testo + Tasto Cerca */
    .search-row-mobile [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 5px !important;
        width: 100% !important;
        margin-bottom: 3px !important;
    }

    .search-row-mobile [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {
        flex: 1 1 76% !important;
        min-width: 0 !important;
        width: 76% !important;
    }

    .search-row-mobile [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 24% !important;
        min-width: 0 !important;
        width: 24% !important;
    }

    .search-btn-container div[data-testid="stButton"] button {
        background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 6px !important;
        font-weight: 900 !important;
        font-size: 0.80rem !important;
        min-height: 30px !important;
        height: 30px !important;
        width: 100% !important;
        padding: 0 !important;
    }

    /* RIGA PREZZI RIDOTTA AL 25% PER CASSETTA, CENTRATA E AFFIANCATA */
    .prices-row-quarter {
        width: 100% !important;
        margin: 2px 0 4px 0 !important;
    }

    .prices-row-quarter [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 8px !important;
        width: 100% !important;
    }

    .prices-row-quarter [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 0 0 25% !important;
        width: 25% !important;
        max-width: 25% !important;
        min-width: 0 !important;
        padding: 0 !important;
    }

    .prices-row-quarter div[data-baseweb="input"] input {
        text-align: center !important;
        font-size: 0.74rem !important;
        padding: 2px !important;
    }

    /* Radio buttons compressi */
    div[data-testid="stRadio"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 1px !important;
        margin: 2px 0 !important;
    }

    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 3px !important;
        width: 100% !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: rgba(30, 41, 59, 0.85) !important;
        padding: 3px 4px !important;
        border-radius: 5px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        margin: 0 !important;
        flex: 1 1 0% !important;
        min-width: 0 !important;
        text-align: center !important;
        justify-content: center !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] div {
        color: #f1f5f9 !important;
        font-size: 0.70rem !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }

    /* Checkbox Spedizione */
    div[data-testid="stCheckbox"] {
        background: rgba(30, 41, 59, 0.85) !important;
        padding: 3px 8px !important;
        border-radius: 6px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        min-height: 26px !important;
        margin: 2px 0 4px 0 !important;
    }

    div[data-testid="stCheckbox"] label p {
        font-size: 0.74rem !important;
        font-weight: 800 !important;
        color: #4ade80 !important;
    }

    /* Card Prodotto */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, rgba(17, 24, 39, 0.95) 0%, rgba(30, 41, 59, 0.92) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        border-radius: 8px !important;
        padding: 6px !important;
        margin-bottom: 6px !important;
    }

    .product-img-wrapper-full {
        width: 100%;
        height: 140px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
        border-radius: 6px;
        overflow: hidden;
        padding: 2px;
        margin-bottom: 4px;
    }

    .product-img-wrapper-full img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }

    .buy-btn-action {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #ffd814;
        color: #0f1111 !important;
        font-size: 0.76rem !important;
        font-weight: 800 !important;
        text-decoration: none !important;
        padding: 2px 4px;
        border-radius: 6px;
        border: 1px solid #fcd200;
        width: 100% !important;
        min-height: 28px;
        height: 28px;
    }

    div[data-testid="stButton"] button[key^="fav_"] {
        background: #1d4ed8 !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 6px !important;
        min-height: 28px !important;
        height: 28px !important;
        padding: 0 !important;
        font-size: 0.85rem !important;
    }

    .deal-title {
        font-size: 0.78rem !important;
        font-weight: 800 !important;
        line-height: 1.15 !important;
        color: #38bdf8 !important;
        margin-bottom: 3px !important;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .price-delivery-split-row {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 4px !important;
        margin: 2px 0 4px 0 !important;
    }

    .deal-price-final {
        font-size: 1.05rem !important;
        font-weight: 900 !important;
        color: #38bdf8 !important;
    }

    .deal-price-old {
        font-size: 0.70rem !important;
        color: #94a3b8 !important;
        text-decoration: line-through;
        margin-left: 2px;
    }

    .deal-badge {
        background-color: #ef4444;
        color: white;
        font-size: 0.65rem;
        font-weight: 800;
        padding: 1px 3px;
        border-radius: 3px;
    }

    .shipping-badge-prime {
        background: #00a8e8;
        color: #fff;
        font-size: 0.65rem;
        font-weight: 900;
        padding: 1px 4px;
        border-radius: 3px;
    }

    .shipping-badge-free {
        background: rgba(15, 23, 42, 0.9);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.5);
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 0.65rem;
        font-weight: 700;
    }

    .shipping-badge-paid {
        background: rgba(30, 41, 59, 0.9);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.4);
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 0.65rem;
        font-weight: 700;
    }

    .feedback-container {
        background: #ffffff;
        border-radius: 6px;
        padding: 4px 6px;
        color: #0f1111;
        margin-top: 3px;
    }

    .feedback-title {
        font-size: 0.72rem;
        font-weight: 700;
        margin-bottom: 1px;
    }

    .feedback-stars-row {
        display: flex;
        align-items: center;
        gap: 2px;
    }

    .feedback-stars { color: #ff6e00; font-size: 0.75rem; }
    .feedback-score-text { font-size: 0.68rem; font-weight: 600; }
    .feedback-subcount { font-size: 0.62rem; color: #565959; margin-bottom: 2px; }

    .fb-row {
        display: flex;
        align-items: center;
        gap: 2px;
        margin-bottom: 1px;
    }

    .fb-label { width: 22px; color: #007185; font-size: 0.60rem; }
    .fb-bar-bg { flex: 1; height: 6px; background-color: #eee; border-radius: 2px; overflow: hidden; }
    .fb-bar-fill { height: 100%; background-color: #ff6e00; }
    .fb-pct { width: 18px; text-align: right; color: #007185; font-size: 0.60rem; }

    .social-share-row-mobile {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 5px !important;
        margin-top: 4px !important;
    }

    .share-icon-btn {
        width: 22px;
        height: 22px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;
    }

    .share-icon-btn svg { width: 12px; height: 12px; }
    .btn-wa { background-color: #25D366; }
    .btn-fb { background-color: #1877F2; }
    .btn-gmail { background-color: #EA4335; }
    .btn-ig { background: linear-gradient(45deg, #f09433 0%, #dc2743 50%, #bc1888 100%); }
    .btn-tg { background-color: #229ED9; }
    .btn-copy { background-color: #475569; }
</style>
""", unsafe_allow_html=True)

OPZIONI_SCONTO = {
    "Tutti": (0, 100),
    "0-20%": (0, 20),
    "20-50%": (20, 50),
    ">50%": (50, 100)
}

if "preferiti_asin" not in st.session_state:
    salvati = ottieni_tutti_preferiti()
    st.session_state.preferiti_asin = {p["asin"]: p for p in salvati}

if "offerte" not in st.session_state:
    st.session_state.offerte = []

def reset_elenco_prodotti():
    st.session_state.offerte = []

st.markdown("""
<div style="text-align: center;">
    <div class="hero-title-main">Scala dei Turchi</div>
    <div class="hero-subtitle-box">
        <span>Offerte Amazon</span>
        <span class="ai-badge">AI</span>
    </div>
    <div class="hero-author-tag">Realizzato da <strong>Davide Marziano</strong></div>
</div>
""", unsafe_allow_html=True)

tab_cerca, tab_preferiti = st.tabs([
    "🔍 Cerca Prodotto", 
    f"⭐ Preferiti ({len(st.session_state.preferiti_asin)})"
])

def render_product_card(p, tab_key="main"):
    with st.container(border=True):
        col_left, col_center, col_fb = st.columns([1.1, 1.4, 1.2])
        is_fav = p["asin"] in st.session_state.preferiti_asin
        star_icon = "⭐" if is_fav else "☆"

        with col_left:
            st.markdown(
                f"<div class='product-img-wrapper-full'><img src='{p.get('immagine_url', '')}' alt='p'></div>",
                unsafe_allow_html=True
            )

        with col_center:
            titolo = p.get('titolo', 'Prodotto Amazon')
            link = p.get('link_affiliato', '')
            st.markdown(f"<div class='deal-title'>{titolo}</div>", unsafe_allow_html=True)
            
            badge_html = f"<span class='deal-badge'>{p['sconto']}</span>" if p.get('sconto') else ""
            old_price_html = f"<span class='deal-price-old'>€{p['prezzo_iniziale']:.2f}</span>" if p.get('prezzo_iniziale', 0.0) > p.get('prezzo_finale', 0.0) else ""
            prices_sub_html = f"<div class='price-subgroup-left'>{badge_html}<span class='deal-price-final'>€{p['prezzo_finale']:.2f}</span>{old_price_html}</div>"

            if p.get("is_prime"):
                ship_html = "<span class='shipping-badge-prime'>prime</span>"
            elif p.get("is_sped_gratis"):
                ship_html = "<span class='shipping-badge-free'>🚚 Gratis</span>"
            elif p.get("costo_spedizione", 0.0) > 0:
                ship_html = f"<span class='shipping-badge-paid'>📦 +€{p['costo_spedizione']:.2f}</span>"
            else:
                ship_html = "<span class='shipping-badge-free'>🚚 Standard</span>"

            st.markdown(f"<div class='price-delivery-split-row'>{prices_sub_html}{ship_html}</div>", unsafe_allow_html=True)

            c_star_sub, c_buy_sub = st.columns([0.28, 0.72])
            with c_star_sub:
                if st.button(star_icon, key=f"fav_{tab_key}_{p['asin']}"):
                    if is_fav:
                        rimuovi_preferito(p["asin"])
                        st.session_state.preferiti_asin.pop(p["asin"], None)
                    else:
                        aggiungi_preferito(p)
                        st.session_state.preferiti_asin[p["asin"]] = p
                    st.rerun()
            with c_buy_sub:
                st.markdown(f"<a href='{link}' target='_blank' class='buy-btn-action'>🛒 Acquista</a>", unsafe_allow_html=True)

        with col_fb:
            voto = p.get("voto_medio", 4.8)
            num_val = p.get("num_recensioni", 765)
            distrib = calcola_distribuzione_recensioni(voto, num_val)
            voto_str = f"{voto:.1f}".replace(".", ",")
            stelle_icon = "★" * int(voto) + "☆" * (5 - int(voto))
            
            bar_rows = []
            for s in ["5", "4", "3", "2", "1"]:
                pct = distrib.get(s, 0)
                bar_rows.append(f"<div class='fb-row'><span class='fb-label'>{s}★</span><div class='fb-bar-bg'><div class='fb-bar-fill' style='width: {pct}%;'></div></div><span class='fb-pct'>{pct}%</span></div>")

            st.markdown(
                f"<div class='feedback-container'><div class='feedback-stars-row'><span class='feedback-stars'>{stelle_icon}</span><span class='feedback-score-text'>{voto_str}</span><span class='feedback-subcount'>({num_val})</span></div>{''.join(bar_rows)}</div>",
                unsafe_allow_html=True
            )

        safe_title = titolo.replace("'", " ").replace('"', ' ').replace("\n", " ").strip()
        share_msg = f"🔥 Offerta: {safe_title}\n💰 Prezzo: €{p['prezzo_finale']:.2f}\n👉 {link}"
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_msg)}"
        fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(link)}"
        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Offerta&body={urllib.parse.quote(share_msg)}"
        ig_url = "https://www.instagram.com/"
        tg_url = f"https://t.me/share/url?url={urllib.parse.quote(link)}&text={urllib.parse.quote(share_msg)}"

        svg_wa = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.842-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>'
        svg_fb = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>'
        svg_gmail = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.272H1.636A1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"/></svg>'
        svg_ig = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'
        svg_tg = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18.847-1.12 5.075-1.597 7.214-.202.906-.596 1.209-.974 1.239-.822.065-1.446-.533-2.242-1.055-1.246-.816-1.95-1.324-3.161-2.122-1.4-.923-.493-1.432.305-2.261.209-.217 3.843-3.521 3.914-3.823.009-.038.017-.18-.067-.255-.084-.075-.208-.05-.298-.029-.127.029-2.155 1.371-6.082 4.022-.575.396-1.096.589-1.562.579-.515-.011-1.506-.291-2.244-.531-.905-.295-1.624-.45-1.562-.951.032-.261.393-.529 1.08-.804 4.234-1.844 7.059-3.06 8.475-3.649 4.037-1.68 4.876-1.972 5.424-1.982.121-.002.391.028.566.17.148.12.189.282.208.396.019.114.043.37.024.571z"/></svg>'
        svg_copy = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>'
        copy_action = f"navigator.clipboard.writeText('{link}').then(function(){{alert('Link copiato!');}});"

        st.markdown(
            f"<div class='social-share-row-mobile'><a href='{wa_url}' target='_blank' class='share-icon-btn btn-wa'>{svg_wa}</a><a href='{fb_url}' target='_blank' class='share-icon-btn btn-fb'>{svg_fb}</a><a href='{gmail_url}' target='_blank' class='share-icon-btn btn-gmail'>{svg_gmail}</a><a href='{ig_url}' target='_blank' class='share-icon-btn btn-ig'>{svg_ig}</a><a href='{tg_url}' target='_blank' class='share-icon-btn btn-tg'>{svg_tg}</a><button onclick=\"{copy_action}\" class='share-icon-btn btn-copy'>{svg_copy}</button></div>",
            unsafe_allow_html=True
        )

with tab_cerca:
    # 1. Riga Input Ricerca + Pulsante Cerca
    st.markdown('<div class="search-row-mobile">', unsafe_allow_html=True)
    col_input, col_submit = st.columns([0.76, 0.24])
    with col_input:
        keyword_val = st.text_input(
            "Cerca:",
            placeholder="Cosa cerchi?...",
            key="cerca_keyword_input",
            label_visibility="collapsed",
            on_change=reset_elenco_prodotti
        )
    with col_submit:
        st.markdown('<div class="search-btn-container">', unsafe_allow_html=True)
        btn_cerca_submit = st.button("🔍 Cerca", key="btn_cerca_submit", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. Riga Prezzo Min e Max ridotti al 25% ciascuno e affiancati
    st.markdown('<div class="prices-row-quarter">', unsafe_allow_html=True)
    col_pmin, col_pmax = st.columns(2)
    with col_pmin:
        p_min_str = st.text_input(
            "Min (€):",
            placeholder="Min €",
            key="cerca_input_pmin_str",
            label_visibility="collapsed",
            on_change=reset_elenco_prodotti
        )
    with col_pmax:
        p_max_str = st.text_input(
            "Max (€):",
            placeholder="Max €",
            key="cerca_input_pmax_str",
            label_visibility="collapsed",
            on_change=reset_elenco_prodotti
        )
    st.markdown('</div>', unsafe_allow_html=True)

    ranking_val = st.radio(
        "🏷️ Ordinamento:",
        list(SORT_MAPPINGS.keys()),
        index=0,
        horizontal=True,
        key="cerca_radio_sort",
        on_change=reset_elenco_prodotti
    )

    label_disc_val = st.radio(
        "🔥 Sconto:",
        list(OPZIONI_SCONTO.keys()),
        index=0,
        horizontal=True,
        key="cerca_radio_disc",
        on_change=reset_elenco_prodotti
    )
    min_disc, max_disc = OPZIONI_SCONTO[label_disc_val]

    solo_gratis = st.checkbox(
        "🚚 Spedizione gratuita / Prime",
        value=False,
        key="cerca_check_sped_gratis",
        on_change=reset_elenco_prodotti
    )

    if btn_cerca_submit:
        with st.spinner("Ricerca rapida in corso..."):
            val_min = None
            if p_min_str.strip():
                try:
                    val_min = float(p_min_str.replace(",", ".").strip())
                except ValueError:
                    val_min = None

            val_max = None
            if p_max_str.strip():
                try:
                    val_max = float(p_max_str.replace(",", ".").strip())
                except ValueError:
                    val_max = None

            if val_min and val_max and val_min > val_max:
                val_min, val_max = val_max, val_min

            risultati = ottieni_offerte_avanzate(
                categoria="",
                sottocategoria="",
                keyword=keyword_val.strip(),
                sort_type=ranking_val,
                solo_spedizione_gratuita=solo_gratis,
                min_price=val_min,
                max_price=val_max,
                min_discount=min_disc,
                max_discount=max_disc,
                item_count=10
            )
            st.session_state.offerte = risultati if risultati else []
            if not risultati:
                st.warning("Nessun prodotto trovato.")

    if st.session_state.offerte:
        st.write("")
        for idx in range(0, len(st.session_state.offerte), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(st.session_state.offerte[idx], tab_key=f"cerca_{idx}")
            if idx + 1 < len(st.session_state.offerte):
                with col_r:
                    render_product_card(st.session_state.offerte[idx + 1], tab_key=f"cerca_{idx + 1}")

with tab_preferiti:
    lista_preferiti = list(st.session_state.preferiti_asin.values())
    if not lista_preferiti:
        st.info("Nessun prodotto nei preferiti (☆).")
    else:
        st.markdown(f"**{len(lista_preferiti)}** prodotti salvati:")
        for idx in range(0, len(lista_preferiti), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(lista_preferiti[idx], tab_key=f"fav_{idx}")
            if idx + 1 < len(lista_preferiti):
                with col_r:
                    render_product_card(lista_preferiti[idx + 1], tab_key=f"fav_{idx + 1}")
