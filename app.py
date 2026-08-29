import streamlit as st
import urllib.parse
from amazon_api import ottieni_offerte_avanzate, SORT_MAPPINGS, calcola_distribuzione_recensioni
from preferiti_db import ottieni_tutti_preferiti, aggiungi_preferito, rimuovi_preferito

st.set_page_config(
    page_title="Scaladeiturchi | Offerte Amazon AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    #MainMenu, header, footer { visibility: hidden !important; height: 0 !important; }

    *, *:before, *:after {
        box-sizing: border-box !important;
    }

    /* Sfondo Celeste Chiaro App */
    .stApp {
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 50%, #e0f2fe 100%) !important;
        background-attachment: fixed !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    .block-container {
        padding: 0.30rem 0.35rem 0.80rem 0.35rem !important;
        max-width: 100% !important;
    }

    /* Tabs Compatti */
    div[data-baseweb="tab-list"] {
        background: rgba(255, 255, 255, 0.75) !important;
        padding: 2px 4px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(2, 132, 199, 0.25) !important;
        gap: 4px !important;
        margin-bottom: 3px !important;
        display: flex !important;
        width: 100% !important;
    }

    button[data-baseweb="tab"] {
        flex: 1 1 0% !important;
        color: #0369a1 !important;
        font-weight: 800 !important;
        font-size: 0.80rem !important;
        background: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid rgba(2, 132, 199, 0.2) !important;
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
        border-color: #0284c7 !important;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35) !important;
    }

    div[data-baseweb="tab-highlight"] { display: none !important; }

    /* Header */
    .hero-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        max-width: 480px;
        margin: 0 auto;
        text-align: center;
    }

    .hero-title-main {
        font-size: clamp(2.2rem, 7.8vw, 3.2rem);
        font-weight: 900;
        line-height: 1.05;
        width: 100%;
        text-align: center;
        letter-spacing: -0.5px;
        margin: 0;
        background: linear-gradient(90deg, #0369a1 0%, #0284c7 50%, #1d4ed8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle-box {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        margin: 3px 0 1px 0;
    }

    .hero-subtitle-text {
        font-size: clamp(1.4rem, 5.0vw, 1.9rem);
        font-weight: 800;
        color: #0f172a;
        font-variant: small-caps;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        flex-grow: 1;
        text-align: center;
    }

    .ai-badge {
        background: #0284c7;
        color: #ffffff;
        font-size: 0.80em;
        font-weight: 900;
        padding: 2px 7px;
        border-radius: 6px;
        margin-left: 6px;
    }

    .hero-author-tag {
        font-size: 0.70rem;
        color: #334155;
        font-weight: 600;
        margin: 1px 0 6px 0;
    }

    .hero-author-tag strong { color: #0369a1; }

    /* Spaziature verticali minime */
    div[data-testid="stVerticalBlock"] > div {
        gap: 1px !important;
    }

    div[data-testid="stMarkdownContainer"] p,
    label[data-testid="stWidgetLabel"] p {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 0.70rem !important;
        margin: 0 !important;
        line-height: 1 !important;
    }

    /* RIGA ULTRA-COMPRESSA: INPUT + CERCA + PIU 10 */
    .search-row-ultra-compressed [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 2px !important;
        width: 100% !important;
        margin-bottom: 2px !important;
    }

    .search-row-ultra-compressed [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {
        flex: 1 1 56% !important;
        min-width: 0 !important;
    }

    .search-row-ultra-compressed [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 22% !important;
        min-width: 0 !important;
    }

    .search-row-ultra-compressed [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
        flex: 1 1 22% !important;
        min-width: 0 !important;
    }

    div[data-baseweb="input"] {
        background-color: #ffffff !important;
        border: 1px solid #7dd3fc !important;
        border-radius: 5px !important;
        min-height: 28px !important;
        height: 28px !important;
        padding: 0 !important;
        box-shadow: 0 1px 2px rgba(2, 132, 199, 0.08) !important;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: #0284c7 !important;
    }

    div[data-baseweb="input"] input {
        color: #0f172a !important;
        font-weight: 600 !important;
        font-size: 0.74rem !important;
        padding: 1px 4px !important;
    }

    /* Tasto Cerca compresso */
    .btn-search-compact div[data-testid="stButton"] button {
        background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        border: 1px solid #0284c7 !important;
        border-radius: 5px !important;
        font-weight: 900 !important;
        font-size: 0.74rem !important;
        min-height: 28px !important;
        height: 28px !important;
        width: 100% !important;
        padding: 0 2px !important;
        white-space: nowrap !important;
    }

    /* Tasto +10 compresso adiacente */
    .btn-more-compact div[data-testid="stButton"] button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 5px !important;
        font-weight: 900 !important;
        font-size: 0.74rem !important;
        min-height: 28px !important;
        height: 28px !important;
        width: 100% !important;
        padding: 0 2px !important;
        white-space: nowrap !important;
    }

    /* Radio filtri inline */
    div[data-testid="stRadio"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 1px !important;
        margin: 1px 0 !important;
    }

    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
        width: 100% !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: rgba(255, 255, 255, 0.85) !important;
        padding: 2px 3px !important;
        border-radius: 4px !important;
        border: 1px solid #bae6fd !important;
        margin: 0 !important;
        flex: 1 1 0% !important;
        min-width: 0 !important;
        text-align: center !important;
        justify-content: center !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] div {
        color: #0f172a !important;
        font-size: 0.68rem !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }

    /* Checkbox */
    div[data-testid="stCheckbox"] {
        background: rgba(255, 255, 255, 0.85) !important;
        padding: 2px 6px !important;
        border-radius: 5px !important;
        border: 1px solid #bae6fd !important;
        min-height: 24px !important;
        margin: 1px 0 3px 0 !important;
    }

    div[data-testid="stCheckbox"] label p {
        font-size: 0.72rem !important;
        font-weight: 800 !important;
        color: #059669 !important;
    }

    /* Riquadro Scheda Prodotto */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #dcfce7 !important;
        background: linear-gradient(160deg, #ecfdf5 0%, #d1fae5 50%, #bbf7d0 100%) !important;
        border: 2px solid #34d399 !important;
        border-radius: 12px !important;
        padding: 8px !important;
        margin-bottom: 8px !important;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.16), 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    }

    .product-img-wrapper-full {
        width: 100%;
        height: 130px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
        border: 1px solid #86efac;
        border-radius: 6px;
        overflow: hidden;
        padding: 2px;
        margin-bottom: 3px;
    }

    .product-img-wrapper-full img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }

    /* Riga Titolo + Stellina Preferiti */
    .title-star-row [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: flex-start !important;
        gap: 3px !important;
        width: 100% !important;
        margin-bottom: 2px !important;
    }

    .title-star-row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {
        flex: 1 1 92% !important;
        min-width: 0 !important;
    }

    .title-star-row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
        flex: 0 0 8% !important;
        min-width: 0 !important;
        display: flex !important;
        justify-content: flex-end !important;
    }

    .deal-title {
        font-size: 0.76rem !important;
        font-weight: 800 !important;
        line-height: 1.15 !important;
        color: #064e3b !important;
        margin: 0 !important;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    /* Stellina Preferiti */
    div[data-testid="stButton"] button[key^="fav_"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        border: 1px solid #047857 !important;
        border-radius: 3px !important;
        min-height: 12px !important;
        height: 12px !important;
        width: 12px !important;
        min-width: 12px !important;
        max-width: 12px !important;
        padding: 0 !important;
        font-size: 0.50rem !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 1px 2px rgba(5, 150, 105, 0.3) !important;
        margin-left: auto !important;
    }

    div[data-testid="stButton"] button[key^="fav_"] p {
        font-size: 0.50rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stButton"] button[key^="fav_"]:hover {
        background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
        border-color: #065f46 !important;
    }

    .buy-btn-action {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #ffd814;
        color: #0f1111 !important;
        font-size: 0.74rem !important;
        font-weight: 800 !important;
        text-decoration: none !important;
        padding: 2px 4px;
        border-radius: 5px;
        border: 1px solid #fcd200;
        width: 100% !important;
        min-height: 26px;
        height: 26px;
        margin-top: 3px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    }

    .price-delivery-split-row {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 4px !important;
        margin: 3px 0 5px 0 !important;
    }

    .price-subgroup-left {
        display: flex !important;
        align-items: baseline !important;
        gap: 3px !important;
        flex-wrap: wrap !important;
    }

    /* Prezzi e Sconti Grandi */
    .deal-price-final {
        font-size: 2.10rem !important;
        font-weight: 900 !important;
        color: #065f46 !important;
        line-height: 1 !important;
    }

    .deal-price-old {
        font-size: 1.40rem !important;
        color: #4b5563 !important;
        text-decoration: line-through;
        margin-left: 3px;
        line-height: 1 !important;
    }

    .deal-badge {
        background-color: #ef4444;
        color: white;
        font-size: 1.30rem !important;
        font-weight: 800 !important;
        padding: 2px 5px !important;
        border-radius: 4px;
        line-height: 1 !important;
        display: inline-block !important;
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
        background: rgba(255, 255, 255, 0.95);
        color: #065f46;
        border: 1px solid #6ee7b7;
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 0.65rem;
        font-weight: 700;
    }

    .shipping-badge-paid {
        background: rgba(255, 255, 255, 0.95);
        color: #92400e;
        border: 1px solid #fde68a;
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
        border: 1px solid #a7f3d0;
    }

    .feedback-title {
        font-size: 0.70rem;
        font-weight: 700;
        margin-bottom: 1px;
    }

    .feedback-stars-row {
        display: flex;
        align-items: center;
        gap: 2px;
    }

    .feedback-stars { color: #ff6e00; font-size: 0.72rem; }
    .feedback-score-text { font-size: 0.66rem; font-weight: 600; }
    .feedback-subcount { font-size: 0.60rem; color: #565959; margin-bottom: 2px; }

    .fb-row {
        display: flex;
        align-items: center;
        gap: 2px;
        margin-bottom: 1px;
    }

    .fb-label { width: 22px; color: #007185; font-size: 0.58rem; }
    .fb-bar-bg { flex: 1; height: 5px; background-color: #f1f5f9; border-radius: 2px; overflow: hidden; }
    .fb-bar-fill { height: 100%; background-color: #ff6e00; }
    .fb-pct { width: 18px; text-align: right; color: #007185; font-size: 0.58rem; }

    .social-share-row-mobile {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 4px !important;
        margin-top: 3px !important;
    }

    .share-icon-btn {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;
    }

    .share-icon-btn svg { width: 11px; height: 11px; }
    .btn-wa { background-color: #25D366; }
    .btn-fb { background-color: #1877F2; }
    .btn-gmail { background-color: #EA4335; }
    .btn-ig { background: linear-gradient(45deg, #f09433 0%, #dc2743 50%, #bc1888 100%); }
    .btn-tg { background-color: #229ED9; }
    .btn-copy { background-color: #475569; }
</style>
""", unsafe_allow_html=True)

OPZIONI_SCONTO = {
    "0-20%": (0, 20),
    "20-50%": (20, 50),
    ">50%": (50, 100)
}

if "preferiti_asin" not in st.session_state:
    salvati = ottieni_tutti_preferiti()
    st.session_state.preferiti_asin = {p["asin"]: p for p in salvati}

if "offerte" not in st.session_state:
    st.session_state.offerte = []

if "has_searched" not in st.session_state:
    st.session_state.has_searched = False

if "item_count" not in st.session_state:
    st.session_state.item_count = 10

def trigger
