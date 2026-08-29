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
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }

    div[data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.6) !important;
        padding: 6px 8px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        gap: 8px !important;
        margin-bottom: 16px !important;
    }

    button[data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        transition: all 0.2s ease !important;
    }

    button[data-baseweb="tab"]:hover {
        background: rgba(56, 189, 248, 0.15) !important;
        color: #f8fafc !important;
        border-color: rgba(56, 189, 248, 0.4) !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
        border-color: #38bdf8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
    }

    div[data-baseweb="tab-highlight"] {
        display: none !important;
    }

    .hero-title-main {
        font-size: clamp(2.2rem, 4.5vw, 3.4rem);
        font-weight: 900;
        letter-spacing: -1px;
        line-height: 1.1;
        margin: 0 0 6px 0;
        background: linear-gradient(90deg, #38bdf8 0%, #60a5fa 50%, #93c5fd 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 4px 20px rgba(56, 189, 248, 0.25);
    }

    .hero-subtitle-box {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: clamp(1.1rem, 2.5vw, 1.5rem);
        font-weight: 700;
        color: #f1f5f9;
        letter-spacing: 0.2px;
        margin-bottom: 8px;
    }

    .ai-badge {
        background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
        color: #ffffff;
        font-size: 0.75em;
        font-weight: 800;
        padding: 2px 8px;
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.25);
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
    }

    .hero-author-tag {
        font-size: clamp(0.85rem, 1.8vw, 0.98rem);
        color: #94a3b8;
        font-weight: 500;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }

    .hero-author-tag strong {
        color: #facc15;
        font-weight: 700;
    }

    div[data-testid="stMarkdownContainer"] p,
    label[data-testid="stWidgetLabel"] p {
        color: #e2e8f0 !important;
        font-weight: 700 !important;
        font-size: 0.84rem !important;
        letter-spacing: 0.2px;
        margin-bottom: 3px !important;
    }

    div[data-baseweb="input"] {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 8px !important;
        min-height: 36px !important;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 1px #38bdf8 !important;
    }

    div[data-baseweb="input"] input {
        color: #f8fafc !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        padding: 4px 8px !important;
    }

    div[data-testid="stCheckbox"] {
        background: rgba(30, 41, 59, 0.85) !important;
        padding: 6px 14px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        width: fit-content !important;
        min-height: 36px !important;
        display: flex !important;
        align-items: center !important;
        margin-top: 8px !important;
        margin-bottom: 6px !important;
        transition: border-color 0.15s ease, background 0.15s ease !important;
    }

    div[data-testid="stCheckbox"]:hover {
        border-color: #4ade80 !important;
        background: rgba(34, 197, 94, 0.10) !important;
    }

    div[data-testid="stCheckbox"] label p {
        font-family: Arial, sans-serif !important;
        font-size: 0.86rem !important;
        font-weight: 800 !important;
        color: #4ade80 !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }

    div[data-testid="stRadio"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 12px !important;
        margin-top: 4px !important;
        margin-bottom: 4px !important;
    }

    div[data-testid="stRadio"] > label {
        margin-bottom: 0px !important;
        font-weight: 800 !important;
        color: #38bdf8 !important;
        white-space: nowrap !important;
        font-size: 0.86rem !important;
    }

    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
        align-items: center !important;
    }
    
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: rgba(30, 41, 59, 0.85) !important;
        padding: 4px 10px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        cursor: pointer !important;
        margin: 0 !important;
        transition: all 0.15s ease !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] div {
        color: #f1f5f9 !important;
        font-size: 0.80rem !important;
        font-weight: 600 !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background: rgba(56, 189, 248, 0.20) !important;
        border-color: #38bdf8 !important;
    }

    .prices-single-row-container [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
        width: 100% !important;
    }

    .prices-single-row-container [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        width: 50% !important;
    }

    .top-single-row-container [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        width: 100% !important;
        margin-top: 4px !important;
        margin-bottom: 6px !important;
    }

    .top-single-row-container [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        width: 16.666% !important;
    }

    .top-single-row-container div[data-testid="stButton"] button {
        background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 6px !important;
        font-weight: 900 !important;
        font-size: clamp(0.72rem, 2vw, 0.84rem) !important;
        letter-spacing: 0.2px !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6) !important;
        padding: 2px 0 !important;
        min-height: 28px !important;
        height: 28px !important;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.4) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
        white-space: nowrap !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .top-single-row-container div[data-testid="stButton"] button p {
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: inherit !important;
    }

    .top-single-row-container div[data-testid="stButton"] button:hover {
        transform: translateY(-1px) !important;
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.5) !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, rgba(17, 24, 39, 0.95) 0%, rgba(30, 41, 59, 0.92) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.30) !important;
        padding: 12px 10px !important;
        margin-bottom: 8px !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #38bdf8 !important;
        box-shadow: 0 6px 20px rgba(56, 189, 248, 0.25) !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }

    .product-img-wrapper-full {
        width: 100%;
        height: 185px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
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

    div[data-testid="stButton"] button[key^="fav_"] {
        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 8px !important;
        padding: 0 !important;
        font-size: 1rem !important;
        color: #ffffff !important;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4) !important;
        min-height: 36px !important;
        height: 36px !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .buy-btn-action {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #ffd814;
        color: #0f1111 !important;
        font-size: 0.80rem !important;
        font-weight: 700 !important;
        text-decoration: none !important;
        padding: 4px 8px;
        border-radius: 8px;
        border: 1px solid #fcd200;
        text-align: center;
        width: 100% !important;
        min-height: 36px;
        box-shadow: 0 2px 6px rgba(213, 175, 0, 0.30);
        transition: background-color 0.15s ease;
        white-space: nowrap;
    }

    .buy-btn-action:hover {
        background-color: #f7ca00;
        color: #0f1111 !important;
    }

    .deal-title {
        font-size: 0.95rem !important;
        font-weight: 800 !important;
        line-height: 1.35 !important;
        color: #38bdf8 !important;
        margin-bottom: 8px !important;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .price-delivery-split-row {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        width: 100% !important;
        margin: 8px 0 12px 0 !important;
    }

    .price-subgroup-left {
        display: flex !important;
        align-items: baseline !important;
        gap: 6px !important;
        flex-wrap: wrap !important;
    }

    .delivery-subgroup-right {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 6px !important;
        margin-left: auto !important;
        flex-wrap: wrap !important;
        text-align: right !important;
    }

    .shipping-badge-prime {
        display: inline-flex;
        align-items: center;
        background: #00a8e8 !important;
        color: #ffffff !important;
        font-size: 0.76rem !important;
        font-weight: 900;
        padding: 3px 8px;
        border-radius: 5px;
        letter-spacing: 0.3px;
        white-space: nowrap;
    }

    .shipping-badge-free {
        display: inline-flex;
        align-items: center;
        background: rgba(15, 23, 42, 0.9) !important;
        color: #4ade80 !important;
        border: 1px solid rgba(34, 197, 94, 0.5) !important;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 0.76rem !important;
        font-weight: 700;
        white-space: nowrap;
    }

    .shipping-badge-paid {
        display: inline-flex;
        align-items: center;
        background: rgba(30, 41, 59, 0.9) !important;
        color: #f59e0b !important;
        border: 1px solid rgba(245, 158, 11, 0.4) !important;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 0.76rem !important;
        font-weight: 700;
        white-space: nowrap;
    }

    .deal-price-final {
        font-size: 1.4rem !important;
        font-weight: 900 !important;
        color: #38bdf8 !important;
        letter-spacing: -0.5px;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
    }

    .deal-price-old {
        font-size: 0.9rem !important;
        color: #94a3b8 !important;
        text-decoration: line-through;
        margin-left: 6px;
    }

    .deal-badge {
        background-color: #ef4444;
        color: white;
        font-size: 0.75rem;
        font-weight: 800;
        padding: 1px 5px;
        border-radius: 4px;
        margin-right: 4px;
    }

    .feedback-container {
        font-family: Arial, sans-serif;
        background: #ffffff;
        border-radius: 8px;
        padding: 8px;
        color: #0f1111;
        border: 1px solid #cbd5e1;
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
        box-shadow: 0 1px 3px rgba(0,0,0,0.30);
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

    .custom-deal-divider {
        height: 2px;
        background: linear-gradient(90deg, rgba(56, 189, 248, 0.1) 0%, rgba(56, 189, 248, 0.6) 50%, rgba(56, 189, 248, 0.1) 100%);
        border: none;
        margin: 16px 0 20px 0;
        border-radius: 2px;
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

OPZIONI_SCONTO = {
    "Tutti": (0, 100),
    "da 0 al 20%": (0, 20),
    "dal 20 al 50%": (20, 50),
    "oltre il 50%": (50, 100)
}

if "preferiti_asin" not in st.session_state:
    salvati = ottieni_tutti_preferiti()
    st.session_state.preferiti_asin = {p["asin"]: p for p in salvati}

if "offerte" not in st.session_state:
    st.session_state.offerte = []

if "last_target_items" not in st.session_state:
    st.session_state.last_target_items = 10

def reset_elenco_prodotti():
    st.session_state.offerte = []

st.markdown("""
<div style="text-align: center; padding-top: 10px; margin-bottom: 10px;">
    <div class="hero-title-main">Scala dei Turchi</div>
    <div class="hero-subtitle-box" style="justify-content: center;">
        <span>Offerte Amazon</span>
        <span class="ai-badge">AI</span>
    </div>
    <div class="hero-author-tag">
        Realizzato da <strong>Davide Marziano</strong>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# Schede
tab_cerca, tab_preferiti = st.tabs([
    "🔍 Cerca Prodotto", 
    f"⭐ Preferiti ({len(st.session_state.preferiti_asin)})"
])

def render_product_card(p, tab_key="main"):
    with st.container(border=True):
        col_left, col_center, col_fb, col_social = st.columns([1.2, 1.5, 1.35, 0.3])
        
        is_fav = p["asin"] in st.session_state.preferiti_asin
        star_icon = "⭐" if is_fav else "☆"

        with col_left:
            img_url = p.get('immagine_url', '')
            st.markdown(
                f"<div class='product-img-wrapper-full'>"
                f"<img src='{img_url}' alt='prodotto'>"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_center:
            titolo = p.get('titolo', 'Prodotto Amazon')
            link = p.get('link_affiliato', '')
            st.markdown(f"<div class='deal-title'>{titolo}</div>", unsafe_allow_html=True)
            
            badge_html = f"<span class='deal-badge'>{p['sconto']}</span>" if p.get('sconto') else ""
            old_price_html = f"<span class='deal-price-old'>da €{p['prezzo_iniziale']:.2f}</span>" if p.get('prezzo_iniziale', 0.0) > p.get('prezzo_finale', 0.0) else ""
            prices_sub_html = (
                f"<div class='price-subgroup-left'>"
                f"{badge_html}"
                f"<span class='deal-price-final'>€{p['prezzo_finale']:.2f}</span>"
                f"{old_price_html}"
                f"</div>"
            )

            if p.get("is_prime"):
                ship_html = "<span class='shipping-badge-prime'>prime</span>"
            elif p.get("is_sped_gratis"):
                ship_html = "<span class='shipping-badge-free'>🚚 Spedizione gratuita</span>"
            elif p.get("costo_spedizione", 0.0) > 0:
                ship_html = f"<span class='shipping-badge-paid'>📦 +€{p['costo_spedizione']:.2f} sped.</span>"
            else:
                ship_html = "<span class='shipping-badge-free'>🚚 Spedizione standard</span>"

            delivery_sub_html = f"<div class='delivery-subgroup-right'>{ship_html}</div>"

            st.markdown(
                f"<div class='price-delivery-split-row'>"
                f"{prices_sub_html}"
                f"{delivery_sub_html}"
                f"</div>",
                unsafe_allow_html=True
            )

            c_star_sub, c_buy_sub = st.columns([0.25, 0.75])
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
    keyword_val = st.text_input(
        "🔍 Scrivi cosa ti serve:",
        placeholder="Es. cuffie bluetooth, notebook...",
        key="cerca_keyword_input",
        on_change=reset_elenco_prodotti
    )

    col_prices_row, _ = st.columns([0.55, 0.45])
    with col_prices_row:
        st.markdown('<div class="prices-single-row-container">', unsafe_allow_html=True)
        col_pmin, col_pmax = st.columns(2)
        with col_pmin:
            p_min = st.number_input(
                "Prezzo Min (€):",
                min_value=0.0,
                value=None,
                step=1.0,
                placeholder="Min...",
                key="cerca_input_pmin",
                on_change=reset_elenco_prodotti
            )
        with col_pmax:
            p_max = st.number_input(
                "Prezzo Max (€):",
                min_value=0.0,
                value=None,
                step=1.0,
                placeholder="Max...",
                key="cerca_input_pmax",
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
        "🔥 Sconto minimo:",
        list(OPZIONI_SCONTO.keys()),
        index=0,
        horizontal=True,
        key="cerca_radio_disc",
        on_change=reset_elenco_prodotti
    )
    min_disc, max_disc = OPZIONI_SCONTO[label_disc_val]

    col_btn_wrap, _ = st.columns([0.65, 0.35])
    with col_btn_wrap:
        st.markdown('<div class="top-single-row-container">', unsafe_allow_html=True)
        t1, t2, t3, t4, t5, t6 = st.columns(6)
        with t1:
            btn_10 = st.button("Top 10", key="cerca_btn10", use_container_width=True)
        with t2:
            btn_20 = st.button("Top 20", key="cerca_btn20", use_container_width=True)
        with t3:
            btn_30 = st.button("Top 30", key="cerca_btn30", use_container_width=True)
        with t4:
            btn_50 = st.button("Top 50", key="cerca_btn50", use_container_width=True)
        with t5:
            btn_70 = st.button("Top 70", key="cerca_btn70", use_container_width=True)
        with t6:
            btn_100 = st.button("Top 100", key="cerca_btn100", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    solo_gratis = st.checkbox(
        "🚚 Spedizione gratuita",
        value=False,
        key="cerca_check_sped_gratis",
        on_change=reset_elenco_prodotti,
        help="Mostra solo prodotti con spedizione gratuita o Prime"
    )

    target_items = None
    if btn_10:
        target_items = 10
    elif btn_20:
        target_items = 20
    elif btn_30:
        target_items = 30
    elif btn_50:
        target_items = 50
    elif btn_70:
        target_items = 70
    elif btn_100:
        target_items = 100

    if target_items is not None:
        st.session_state.last_target_items = target_items
        with st.spinner(f"Estrazione dei Top {target_items} prodotti in corso..."):
            val_min = float(p_min) if (p_min is not None and p_min > 0) else None
            val_max = float(p_max) if (p_max is not None and p_max > 0) else None
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
                item_count=target_items
            )
            st.session_state.offerte = risultati if risultati else []
            if not risultati:
                st.warning("Nessun prodotto trovato con i filtri selezionati.")

    if st.session_state.offerte:
        st.divider()
        for idx in range(0, len(st.session_state.offerte), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(st.session_state.offerte[idx], tab_key=f"cerca_{idx}")
            if idx + 1 < len(st.session_state.offerte):
                with col_r:
                    render_product_card(st.session_state.offerte[idx + 1], tab_key=f"cerca_{idx + 1}")
            st.markdown("<hr class='custom-deal-divider'>", unsafe_allow_html=True)

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
            st.markdown("<hr class='custom-deal-divider'>", unsafe_allow_html=True)
