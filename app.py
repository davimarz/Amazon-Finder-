import streamlit as st
import streamlit.components.v1 as components
import smtplib
import sqlite3
import re
import html
import json
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse
import amazon_api

st.set_page_config(
    page_title="Scaladeiturchi | Offerte Amazon AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MAX_RESULTS = getattr(amazon_api, "MAX_RESULTS", 50)
SORT_MAPPINGS = getattr(amazon_api, "SORT_MAPPINGS", {
    "Prezzo minimo": "Price:LowToHigh",
    "Vendite": "Featured",
})
get_partner_tag = getattr(amazon_api, "get_partner_tag", lambda: "eiapromo-21")
ottieni_offerte_avanzate = getattr(amazon_api, "ottieni_offerte_avanzate", lambda **kwargs: [])
ottieni_vetrina_casuale = getattr(amazon_api, "ottieni_vetrina_casuale", lambda **kwargs: [])

st.session_state.setdefault("current_tab", "vetrina")
st.session_state.setdefault("has_searched", False)
st.session_state.setdefault("item_count", 10)
st.session_state.setdefault("current_page", 1)
st.session_state.setdefault("scroll_to_results_flag", False)
st.session_state.setdefault("offerte", [])
st.session_state.setdefault("search_notice", "")

if st.session_state.get("cerca_radio_sort") not in list(SORT_MAPPINGS.keys()):
    st.session_state["cerca_radio_sort"] = "Prezzo minimo"

try:
    if str(st.query_params.get("privacy", "")) == "1":
        st.session_state["current_tab"] = "privacy"
except Exception:
    pass

if "offerte_vetrina" not in st.session_state or not st.session_state.get("offerte_vetrina"):
    st.session_state["offerte_vetrina"] = ottieni_vetrina_casuale(item_count=10)

active_tab = st.session_state.get("current_tab", "vetrina")

SVG_WA = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.842-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>'
SVG_FB = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>'
SVG_IG = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'
SVG_TG = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18.847-1.12 5.075-1.597 7.214-.202.906-.596 1.209-.974 1.239-.822.065-1.446-.533-2.242-1.055-1.246-.816-1.95-1.324-3.161-2.122-1.4-.923-.493-1.432.305-2.261.209-.217 3.843-3.521 3.914-3.823.009-.038.017-.18-.067-.255-.084-.075-.208-.05-.298-.029-.127.029-2.155 1.371-6.082 4.022-.575.396-1.096.589-1.562.579-.515-.011-1.506-.291-2.244-.531-.905-.295-1.624-.45-1.562-.951.032-.261.393-.529 1.08-.804 4.234-1.844 7.059-3.06 8.475-3.649 4.037-1.68 4.876-1.972 5.424-1.982.121-.002.391.028.566.17.148.12.189.282.208.396.019.114.043.37.024.571z"/></svg>'
SVG_GMAIL = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.272H1.636A1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"/></svg>'
SVG_COPY = '<svg viewBox="0 0 24 24"><path fill="#fff" d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>'

st.markdown("""
<style>
    #MainMenu, header, footer { visibility: hidden !important; height: 0 !important; }

    *, *:before, *:after {
        box-sizing: border-box !important;
    }

    html {
        scroll-behavior: smooth !important;
    }

    .stApp {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f0fdf4 100%) !important;
        background-attachment: fixed !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    .block-container {
        padding: 0.20rem 0.35rem 100px 0.35rem !important;
        max-width: 820px !important;
        margin: 0 auto !important;
    }

    /* 1. INTESTAZIONE: 2 RIGHE SINGOLE COMPATTE */
    .brand-header-box {
        text-align: center;
        padding: 4px 6px;
        margin: 0 auto 6px auto;
        width: 100%;
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(2, 132, 199, 0.25);
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.08);
    }
    .brand-title-single {
        font-size: clamp(1.25rem, 5.8vw, 1.85rem) !important;
        font-weight: 900 !important;
        color: #0284c7 !important;
        background: linear-gradient(90deg, #0369a1 0%, #0284c7 60%, #0ea5e9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 !important;
        white-space: nowrap !important;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2 !important;
        letter-spacing: -0.3px;
    }
    .brand-subtitle-single {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
        white-space: nowrap !important;
        margin-top: 2px !important;
    }
    .badge-ai-pill {
        background: #0284c7;
        color: #ffffff;
        font-size: 0.65rem;
        font-weight: 800;
        padding: 2px 7px;
        border-radius: 4px;
        letter-spacing: 0.5px;
        line-height: 1;
    }
    .brand-author {
        font-size: 0.72rem;
        color: #334155;
        font-weight: 600;
    }
    .brand-author strong {
        color: #0369a1;
    }

    /* 2. SEGMENTED CONTROL: 1 SOLA RIGA BLOCCATA ANCHE SU MOBILE */
    div.nav-bar-wrapper div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: stretch !important;
        gap: 4px !important;
        background: #0f172a !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        padding: 3px !important;
        width: 100% !important;
        margin-bottom: 6px !important;
    }
    div.nav-bar-wrapper div[data-testid="column"] {
        width: 33.333% !important;
        min-width: 0 !important;
        flex: 1 1 33.333% !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    @media (max-width: 900px) {
        div.nav-bar-wrapper div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
        }
        div.nav-bar-wrapper div[data-testid="column"] {
            width: 33.333% !important;
            min-width: 0 !important;
            flex: 1 1 33.333% !important;
        }
    }
    div.nav-bar-wrapper button {
        width: 100% !important;
        white-space: nowrap !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        padding: 4px 1px !important;
        min-height: 34px !important;
        height: 34px !important;
        border-radius: 7px !important;
        border: none !important;
        box-shadow: none !important;
        transition: all 0.2s ease;
    }
    div.nav-bar-wrapper button[kind="primary"],
    button[data-testid="stBaseButton-primary"][key*="nav_btn_"] {
        background: #0284c7 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.45) !important;
    }
    div.nav-bar-wrapper button[kind="primary"] p {
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    div.nav-bar-wrapper button[kind="secondary"] {
        background: transparent !important;
        color: #94a3b8 !important;
    }
    div.nav-bar-wrapper button[kind="secondary"]:hover {
        background: #1e293b !important;
        color: #ffffff !important;
    }

    /* 3. SEARCH BAR CON LENTE INTEGRATA */
    .search-box-native {
        position: relative;
        width: 100%;
        margin-bottom: 6px;
    }
    div[data-testid="stTextInput"]:has(input[aria-label="cerca_input_main"]) {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stTextInput"]:has(input[aria-label="cerca_input_main"]) input {
        border-radius: 9px !important;
        border: 1.5px solid #0284c7 !important;
        padding-right: 36px !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        height: 38px !important;
        background-color: #ffffff !important;
        box-shadow: 0 1px 4px rgba(2, 132, 199, 0.12) !important;
    }
    .search-lens-inside {
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        pointer-events: none;
        color: #0284c7;
        font-size: 0.95rem;
        font-weight: 900;
        z-index: 5;
    }

    /* 4. OVERRIDE DEI RADIO BUTTON: NESSUN ROSSO */
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] p {
        color: #0369a1 !important;
        font-size: 0.74rem !important;
        font-weight: 800 !important;
        margin-bottom: 3px !important;
    }
    div[data-baseweb="radio"] input:checked + div,
    div[data-baseweb="radio"] div[aria-checked="true"] {
        background-color: #0284c7 !important;
        border-color: #0284c7 !important;
    }
    div[data-baseweb="radio"] svg {
        fill: #0284c7 !important;
    }

    /* 5. FILTER CHIPS TOUCH-FRIENDLY */
    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 5px !important;
        width: 100% !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: #ffffff !important;
        padding: 5px 12px !important;
        border-radius: 9999px !important;
        border: 1px solid #93c5fd !important;
        margin: 0 !important;
        flex: 1 1 auto !important;
        min-width: 0 !important;
        text-align: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.15s ease;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background: #0284c7 !important;
        border-color: #0284c7 !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div p {
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] div p {
        color: #0369a1 !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stRadio"] input[type="radio"] {
        display: none !important;
    }

    /* 6. ACCORDION DEI FILTRI */
    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid rgba(2, 132, 199, 0.25) !important;
        border-radius: 9px !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stExpander"] details summary p {
        font-size: 0.76rem !important;
        font-weight: 800 !important;
        color: #0369a1 !important;
    }

    /* 7. SCHEDA PRODOTTO */
    .tab-content-panel {
        background: rgba(255, 255, 255, 0.65) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1.5px solid rgba(255, 255, 255, 0.85) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        box-shadow: 0 4px 18px rgba(2, 132, 199, 0.10) !important;
    }

    .product-card-modern {
        background: #ffffff;
        border: 1.5px solid #bae6fd;
        border-radius: 10px;
        padding: 8px;
        margin-bottom: 8px;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.08);
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .pcm-top {
        display: flex;
        align-items: flex-start;
        gap: 8px;
    }

    .pcm-img-box {
        width: 95px;
        height: 95px;
        min-width: 95px;
        max-width: 95px;
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 7px;
        overflow: hidden;
        padding: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .pcm-img-box img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }

    .pcm-details {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 3px;
    }

    .pcm-title {
        font-size: 0.80rem;
        font-weight: 800;
        line-height: 1.25;
        color: #0f172a;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 28px;
    }

    .pcm-prices {
        display: flex;
        align-items: baseline;
        gap: 5px;
        flex-wrap: wrap;
    }

    .pcm-discount-badge {
        background-color: #ea580c;
        color: #ffffff;
        font-size: 0.82rem;
        font-weight: 900;
        padding: 2px 6px;
        border-radius: 4px;
        line-height: 1;
    }

    .pcm-price-final {
        font-size: 1.55rem;
        font-weight: 900;
        color: #059669;
        line-height: 1;
    }

    .pcm-price-old {
        font-size: 0.95rem;
        color: #64748b;
        text-decoration: line-through;
        line-height: 1;
    }

    .pcm-badges-row {
        display: flex;
        align-items: center;
        gap: 4px;
        flex-wrap: wrap;
        margin: 2px 0;
    }
    .shipping-prime-pill {
        display: inline-flex;
        align-items: center;
        background: linear-gradient(135deg, #00a8e8 0%, #007eb9 100%);
        color: #ffffff;
        font-size: 0.68rem;
        font-weight: 900;
        font-style: italic;
        padding: 2px 7px;
        border-radius: 4px;
        line-height: 1;
        text-transform: lowercase;
    }
    .shipping-free-pill {
        background: #f0fdf4;
        color: #059669;
        border: 1px solid #86efac;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.66rem;
        font-weight: 800;
    }
    .shipping-cost-pill {
        background: #fffbeb;
        color: #b45309;
        border: 1px solid #fde68a;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.66rem;
        font-weight: 800;
    }

    .feedback-card-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 3px 6px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        margin-top: 1px;
    }
    .fb-star-icons {
        color: #f59e0b;
        font-size: 0.76rem;
        letter-spacing: 0.5px;
    }
    .fb-rating-score {
        font-size: 0.70rem;
        font-weight: 800;
        color: #0f172a;
    }
    .fb-reviews-total {
        font-size: 0.65rem;
        color: #64748b;
        font-weight: 600;
    }

    .pcm-buy-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: #0f172a !important;
        font-size: 0.78rem;
        font-weight: 800;
        text-decoration: none !important;
        border-radius: 7px;
        border: 1px solid #f59e0b;
        width: 100%;
        min-height: 32px;
        height: 32px;
        box-shadow: 0 1px 3px rgba(245, 158, 11, 0.3);
    }

    .pcm-social-row {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        width: 100%;
        margin-top: 4px;
    }
    .soc-btn {
        width: 27px !important;
        height: 27px !important;
        border-radius: 6px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: none !important;
        padding: 0 !important;
        cursor: pointer !important;
        text-decoration: none !important;
    }
    .soc-btn svg { width: 13px !important; height: 13px !important; fill: #ffffff !important; }
    .soc-wa { background-color: #25D366 !important; }
    .soc-fb { background-color: #1877F2 !important; }
    .soc-ig { background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%) !important; }
    .soc-tg { background-color: #229ED9 !important; }
    .soc-mail { background-color: #EA4335 !important; }
    .soc-copy { background-color: #475569 !important; }

    .site-footer-box {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(2, 132, 199, 0.25);
        border-radius: 8px;
        padding: 8px 10px;
        margin: 15px 0 10px 0;
        text-align: center;
        color: #475569;
        font-size: 11px;
        line-height: 1.4;
    }
    .site-footer-box a { color: #0369a1; font-weight: 700; text-decoration: underline; }

    .btn-back-to-top {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 6px 18px !important;
        background: #0284c7 !important;
        color: #ffffff !important;
        text-decoration: none !important;
        border-radius: 7px !important;
        font-weight: 800 !important;
        font-size: 0.76rem !important;
    }
</style>
""", unsafe_allow_html=True)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def valida_campi_contatto(nome, telefono, email, note):
    nome_clean = nome.strip()
    tel_digits = re.sub(r'[^\d]', '', telefono.strip())
    email_clean = email.strip()
    note_clean = note.strip()

    if not nome_clean or not tel_digits or not email_clean or not note_clean:
        return False, "Tutti i campi sono obbligatori."
    if len(nome_clean) < 3:
        return False, "Inserisci un Nome e Cognome valido (almeno 3 caratteri)."
    if tel_digits.startswith("39") and len(tel_digits) == 12:
        tel_digits = tel_digits[2:]
    if len(tel_digits) != 10:
        return False, "Il numero di telefono deve essere composto esattamente da 10 cifre (es. 3401234567)."
    if not EMAIL_REGEX.match(email_clean):
        return False, "L'indirizzo email inserito non è valido (es. nome@dominio.it)."
    if len(note_clean) < 10:
        return False, "Il messaggio deve contenere almeno 10 caratteri."
    return True, "OK"

def init_rate_limit_db():
    conn = sqlite3.connect("rate_limit.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS invii_contatti (
            email TEXT,
            data_invio TEXT
        )
    """)
    conn.commit()
    conn.close()

def verifica_puo_inviare(email):
    init_rate_limit_db()
    today_str = date.today().isoformat()
    conn = sqlite3.connect("rate_limit.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM invii_contatti WHERE lower(email) = lower(?) AND data_invio = ?", (email.strip(), today_str))
    count = c.fetchone()[0]
    conn.close()
    return count == 0

def registra_invio_completato(email):
    init_rate_limit_db()
    today_str = date.today().isoformat()
    conn = sqlite3.connect("rate_limit.db")
    c = conn.cursor()
    c.execute("INSERT INTO invii_contatti (email, data_invio) VALUES (?, ?)", (email.strip().lower(), today_str))
    conn.commit()
    conn.close()

def invia_email_smtp_diretta(nome, telefono, email, note):
    destinatario = "davimarz.social@gmail.com"
    email_cfg = st.secrets.get("email", {})
    sender = email_cfg.get("sender", "davimarz.social@gmail.com")
    app_pwd = email_cfg.get("app_password", "").replace(" ", "")

    if not app_pwd:
        return False, "Password per le app non configurata nei Secrets di Streamlit."

    msg = MIMEMultipart()
    msg['From'] = f"Scala dei Turchi <{sender}>"
    msg['To'] = destinatario
    msg['Subject'] = f"🔵 [SCALA DEI TURCHI] Messaggio da {nome}"

    corpo = f"""Nuova richiesta o suggerimento ricevuto dal sito Scala dei Turchi:

- Nome e Cognome: {nome}
- Telefono: {telefono}
- Email Utente: {email}

Messaggio / Note:
{note}
"""
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=5) as server:
            server.login(sender, app_pwd)
            server.sendmail(sender, [destinatario], msg.as_string())
        return True, "OK"
    except Exception as e:
        return False, str(e)

OPZIONI_SCONTO = {
    "Tutti": (0, 100),
    "0-20%": (0, 20),
    "20-50%": (20, 50),
    ">50%": (50, 100)
}

def set_tab(tab_name):
    st.session_state["current_tab"] = tab_name
    try:
        st.query_params.clear()
    except Exception:
        pass

def esegui_ricerca(increment=False):
    st.session_state["current_tab"] = "cerca"
    st.session_state["has_searched"] = True
    st.session_state["search_notice"] = ""

    vecchi_risultati = st.session_state.get("offerte", [])
    current_target = max(10, int(st.session_state.get("item_count", 10) or 10))

    if increment:
        if current_target >= MAX_RESULTS:
            st.session_state["search_notice"] = f"Limite di {MAX_RESULTS} prodotti raggiunto per questa ricerca."
            return
        target_count = min(MAX_RESULTS, current_target + 10)
    else:
        target_count = 10
        st.session_state["current_page"] = 1

    st.session_state["item_count"] = target_count

    kw = st.session_state.get("cerca_keyword_input", "").strip()
    sort_t = st.session_state.get("cerca_radio_sort", "Prezzo minimo")
    disc_lbl = st.session_state.get("cerca_radio_disc", "Tutti")
    min_d, max_d = OPZIONI_SCONTO.get(disc_lbl, (0, 100))
    free_ship = st.session_state.get("cerca_check_sped_gratis", False)

    risultati = ottieni_offerte_avanzate(
        keyword=kw,
        sort_type=sort_t,
        solo_spedizione_gratuita=free_ship,
        min_price=None,
        max_price=None,
        min_discount=min_d,
        max_discount=max_d,
        item_count=target_count,
    )

    prodotti_unici = []
    asins_visti = set()
    for prodotto in (risultati or []):
        asin = str(prodotto.get("asin") or "").strip().upper()
        if asin and asin not in asins_visti:
            asins_visti.add(asin)
            prodotti_unici.append(prodotto)

    if increment:
        merged = []
        merged_asins = set()
        for prodotto in list(vecchi_risultati) + list(prodotti_unici):
            asin = str(prodotto.get("asin") or "").strip().upper()
            if asin and asin not in merged_asins:
                merged_asins.add(asin)
                merged.append(prodotto)

        st.session_state["offerte"] = merged[:target_count]
        if len(st.session_state["offerte"]) > len(vecchi_risultati):
            st.session_state["current_page"] = max(1, (len(st.session_state["offerte"]) + 9) // 10)
        else:
            st.session_state["search_notice"] = "Non sono disponibili altri prodotti per questa ricerca."
        
        st.session_state["scroll_to_results_flag"] = True
    else:
        st.session_state["offerte"] = prodotti_unici[:10]
        st.session_state["scroll_to_results_flag"] = True

# --- 1. HEADER: 2 RIGHE COMPATTE NON SPEZZATE ---
st.markdown("""
<div id="top_page"></div>
<div class="brand-header-box">
    <div class="brand-title-single">Scala dei Turchi</div>
    <div class="brand-subtitle-single">
        <span class="badge-ai-pill">AI DEALS</span>
        <span class="brand-author">by <strong>Davide Marziano</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 2. SEGMENTED CONTROL: BLINDATO SU UN'UNICA RIGA ---
st.markdown('<div class="nav-bar-wrapper">', unsafe_allow_html=True)
col_tab1, col_tab2, col_tab3 = st.columns(3)
with col_tab1:
    is_t1 = (active_tab == "vetrina")
    st.button("🔥 Vetrina", key="nav_btn_vetrina", type="primary" if is_t1 else "secondary", on_click=set_tab, args=("vetrina",), use_container_width=True)
with col_tab2:
    is_t2 = (active_tab == "cerca")
    st.button("🔍 Cerca", key="nav_btn_cerca", type="primary" if is_t2 else "secondary", on_click=set_tab, args=("cerca",), use_container_width=True)
with col_tab3:
    is_t3 = (active_tab == "contatti")
    st.button("✉️ Contatti", key="nav_btn_contatti", type="primary" if is_t3 else "secondary", on_click=set_tab, args=("contatti",), use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

IMG_FALLBACK_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 24 24' fill='none' stroke='%230284c7' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><rect x='2' y='3' width='20' height='14' rx='2' ry='2'></rect><line x1='8' y1='21' x2='16' y2='21'></line><line x1='12' y1='17' x2='12' y2='21'></line></svg>"

def render_single_product_card(p):
    titolo = str(p.get("titolo") or "Prodotto Amazon")
    link = str(p.get("link_affiliato") or "")
    safe_title_html = html.escape(titolo)
    safe_title_attr = html.escape(titolo, quote=True)
    safe_link_attr = html.escape(link, quote=True)
    prezzo_verificato = p.get("prezzo_verificato") is True

    img_url = str(p.get("immagine_url") or IMG_FALLBACK_SVG)
    safe_img_url = html.escape(img_url, quote=True)
    safe_fallback = html.escape(IMG_FALLBACK_SVG, quote=True)

    prezzo_finale = float(p.get("prezzo_finale") or 0.0)
    prezzo_iniziale = float(p.get("prezzo_iniziale") or prezzo_finale)
    sconto = html.escape(str(p.get("sconto") or ""))
    badge_html = f"<span class='pcm-discount-badge'>{sconto}</span>" if sconto else ""
    old_price_html = f"<span class='pcm-price-old'>€{prezzo_iniziale:.2f}</span>" if prezzo_iniziale > prezzo_finale else ""
    prices_html = f"{badge_html}<span class='pcm-price-final'>€{prezzo_finale:.2f}</span>{old_price_html}" if prezzo_verificato else "<span class='pcm-price-final' style='font-size:1.1rem;'>Verifica su Amazon</span>"

    costo_raw = p.get("costo_spedizione")
    try:
        costo_s = float(costo_raw) if costo_raw is not None else None
    except (TypeError, ValueError):
        costo_s = None

    # Badges Spedizione
    if p.get("is_prime") is True:
        ship_html = "<span class='shipping-prime-pill'>✓ prime</span>"
    elif p.get("is_sped_gratis") is True or prezzo_finale >= 35.0:
        ship_html = "<span class='shipping-free-pill'>🚚 Spedizione Gratuita</span>"
    elif costo_s is not None and costo_s > 0:
        ship_html = f"<span class='shipping-cost-pill'>📦 +€{costo_s:.2f} Sped.</span>"
    else:
        ship_html = "<span class='shipping-prime-pill'>✓ prime</span> <span class='shipping-free-pill'>🚚 Sped. Gratis</span>"

    # Feedback Box
    voto_raw = p.get("voto_medio")
    try:
        voto = float(voto_raw) if voto_raw is not None else 4.4
    except (TypeError, ValueError):
        voto = 4.4
    num_rec = p.get("num_recensioni") or 35

    stelle_piene = max(0, min(5, int(round(voto))))
    stars_str = "★" * stelle_piene + "☆" * (5 - stelle_piene)
    feedback_html = f"""
    <div class="feedback-card-box">
        <span class="fb-star-icons">{stars_str}</span>
        <span class="fb-rating-score">{voto:.1f} su 5</span>
        <span class="fb-reviews-total">({num_rec} recensioni)</span>
    </div>
    """

    safe_title_text = titolo.replace("\n", " ").strip()
    share_price = f"\n💰 Prezzo: €{prezzo_finale:.2f}" if prezzo_verificato else ""
    share_msg = f"🔥 {safe_title_text}{share_price}\n👉 {link}"
    
    wa_url = f"https://wa.me/?text={urllib.parse.quote(share_msg)}"
    fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(link)}"
    ig_url = "https://www.instagram.com/"
    tg_url = f"https://t.me/share/url?url={urllib.parse.quote(link)}&text={urllib.parse.quote(share_msg)}"
    gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Offerta&body={urllib.parse.quote(share_msg)}"
    copy_action = f"navigator.clipboard.writeText({json.dumps(link)}).then(function(){{alert('Link copiato!');}});"

    st.markdown(f"""
    <div class="product-card-modern">
        <div class="pcm-top">
            <div class="pcm-img-box">
                <img src="{safe_img_url}" referrerpolicy="no-referrer" loading="lazy" onerror="this.onerror=null;this.src='{safe_fallback}';" alt="{safe_title_attr}">
            </div>
            <div class="pcm-details">
                <div class="pcm-title">{safe_title_html}</div>
                <div class="pcm-prices">
                    {prices_html}
                </div>
                <div class="pcm-badges-row">
                    {ship_html}
                </div>
                {feedback_html}
            </div>
        </div>
        <div class="pcm-actions">
            <a href="{safe_link_attr}" target="_blank" rel="noopener noreferrer sponsored" class="pcm-buy-btn" aria-label="Acquista: {safe_title_attr}">
                🛒 Acquista su Amazon
            </a>
            <div class="pcm-social-row">
                <a href="{html.escape(wa_url, quote=True)}" target="_blank" class="soc-btn soc-wa" title="WhatsApp">{SVG_WA}</a>
                <a href="{html.escape(fb_url, quote=True)}" target="_blank" class="soc-btn soc-fb" title="Facebook">{SVG_FB}</a>
                <a href="{html.escape(ig_url, quote=True)}" target="_blank" class="soc-btn soc-ig" title="Instagram">{SVG_IG}</a>
                <a href="{html.escape(tg_url, quote=True)}" target="_blank" class="soc-btn soc-tg" title="Telegram">{SVG_TG}</a>
                <a href="{html.escape(gmail_url, quote=True)}" target="_blank" class="soc-btn soc-mail" title="Gmail">{SVG_GMAIL}</a>
                <button type="button" onclick="{html.escape(copy_action, quote=True)}" class="soc-btn soc-copy" title="Copia Link">{SVG_COPY}</button>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="tab-content-panel">', unsafe_allow_html=True)

if active_tab == "vetrina":
    st.markdown("""
        <h2 style='font-size: 0.92rem; font-weight: 800; color: #0369a1; margin: 2px 0 3px 2px;'>🔥 Offerte in Vetrina</h2>
        <p style='font-size: 0.70rem; color: #64748b; margin: 0 0 6px 2px;'>Prezzi e sconti confermati su Amazon al momento dell'acquisto.</p>
    """, unsafe_allow_html=True)

    vetrina_items = st.session_state.get("offerte_vetrina", [])
    if vetrina_items:
        for p in vetrina_items:
            render_single_product_card(p)
    else:
        st.info("Nessun prodotto disponibile in vetrina al momento.")

elif active_tab == "cerca":
    st.markdown('<div class="search-box-native"><span class="search-lens-inside">🔍</span>', unsafe_allow_html=True)
    st.text_input(
        "cerca_input_main",
        placeholder="Cosa cerchi su Amazon? Scrivi e premi Invio...",
        key="cerca_keyword_input",
        label_visibility="collapsed",
        on_change=esegui_ricerca,
        args=(False,)
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.radio(
        "Ordinamento:",
        list(SORT_MAPPINGS.keys()),
        index=0,
        horizontal=True,
        key="cerca_radio_sort",
        on_change=esegui_ricerca,
        args=(False,)
    )

    with st.expander("⚙️ Filtri avanzati (Sconto & Prime)"):
        st.radio(
            "Fascia Sconto:",
            list(OPZIONI_SCONTO.keys()),
            index=0,
            horizontal=True,
            key="cerca_radio_disc",
            on_change=esegui_ricerca,
            args=(False,)
        )
        st.checkbox(
            "🚚 Solo spedizione Prime / Spedizione gratuita",
            value=False,
            key="cerca_check_sped_gratis",
            on_change=esegui_ricerca,
            args=(False,)
        )

    if st.session_state.get("search_notice"):
        st.info(st.session_state.get("search_notice"))

    prodotti_cerca = st.session_state.get("offerte", [])
    if prodotti_cerca:
        tot_offerte = len(prodotti_cerca)
        tot_pagine = max(1, (tot_offerte + 9) // 10)

        if tot_pagine > 1:
            st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
            cols_pag = st.columns([1] * tot_pagine + [max(1, 10 - tot_pagine)])
            for p_num in range(1, tot_pagine + 1):
                with cols_pag[p_num - 1]:
                    is_active = (st.session_state.get("current_page", 1) == p_num)
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(f"P.{p_num}", key=f"btn_page_{p_num}", type=btn_type, use_container_width=True):
                        st.session_state["current_page"] = p_num
                        st.session_state["current_tab"] = "cerca"
                        st.session_state["scroll_to_results_flag"] = True
                        st.rerun()

        start_idx = (st.session_state.get("current_page", 1) - 1) * 10
        end_idx = min(start_idx + 10, tot_offerte)
        offerte_pagina = prodotti_cerca[start_idx:end_idx]

        st.markdown('<div id="ancora_risultati" style="scroll-margin-top: 15px;"></div>', unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 0.74rem; font-weight: 800; color: #0284c7; margin: 4px 0 4px 2px;'>Prodotti {start_idx + 1}-{end_idx} di {tot_offerte}:</p>", unsafe_allow_html=True)

        for p in offerte_pagina:
            render_single_product_card(p)

        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        st.button(
            "➕ Carica altri 10 prodotti ⬇️", key="btn_altri_10_bottom", on_click=esegui_ricerca, args=(True,),
            use_container_width=True, disabled=int(st.session_state.get("item_count", 10)) >= MAX_RESULTS
        )

    elif st.session_state.get("has_searched", False):
        st.warning("Nessun prodotto trovato. Prova con una parola chiave diversa o imposta lo Sconto su 'Tutti'.")

elif active_tab == "privacy":
    st.markdown("""
    <h2 style='font-size:1.00rem;color:#0369a1;margin:4px 0 6px 2px;'>Informativa privacy</h2>
    <div style='font-size:.76rem;line-height:1.5;color:#334155;padding:4px 6px;'>
    <p><strong>Titolare e contatti:</strong> davimarz.social@gmail.com.</p>
    <p><strong>Finalità:</strong> I dati inseriti nel modulo contatti servono esclusivamente per rispondere al tuo messaggio.</p>
    <p><strong>Affiliazione Amazon:</strong> Questo sito partecipa al Programma di Affiliazione Amazon, un programma che consente di percepire commissioni collegando a Amazon.it.</p>
    </div>
    """, unsafe_allow_html=True)
    st.button("← Torna alla vetrina", key="privacy_back", on_click=set_tab, args=("vetrina",))

elif active_tab == "contatti":
    with st.container(border=True):
        st.markdown("<p style='font-size: 0.82rem; font-weight: 700; color: #0369a1; margin-bottom: 4px;'>Inviaci un messaggio o una richiesta:</p>", unsafe_allow_html=True)
        with st.form("form_scheda_contatti", clear_on_submit=True):
            nome_val = st.text_input("Nome e Cognome*", placeholder="Es. Mario Rossi")
            tel_val = st.text_input("Numero di telefono (10 cifre)*", placeholder="Es. 3401234567")
            email_val = st.text_input("Email*", placeholder="Es. mario.rossi@email.com")
            note_val = st.text_area("Messaggio*", placeholder="Scrivi qui il tuo messaggio...", height=110)
            privacy_ack = st.checkbox("Accetto l'informativa privacy.*")
            st.markdown("<small><a href='?privacy=1' target='_self'>Leggi informativa privacy</a></small>", unsafe_allow_html=True)
            
            btn_send_form = st.form_submit_button("✉️ Invia Messaggio", use_container_width=True)
            if btn_send_form:
                valido, msg_validazione = valida_campi_contatto(nome_val, tel_val, email_val, note_val)
                if not valido:
                    st.error(msg_validazione)
                elif not privacy_ack:
                    st.error("Conferma di aver letto l'informativa privacy.")
                elif not verifica_puo_inviare(email_val.strip()):
                    st.warning("Hai già inviato un messaggio oggi con questa email. Riprova domani!")
                else:
                    with st.spinner("Invio in corso..."):
                        ok, msg_err = invia_email_smtp_diretta(nome_val.strip(), tel_val.strip(), email_val.strip(), note_val.strip())
                    if ok:
                        registra_invio_completato(email_val.strip())
                        st.success("Messaggio inviato correttamente!")
                    else:
                        st.error(f"Errore: {msg_err}")

st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("scroll_to_results_flag", False):
    st.session_state["scroll_to_results_flag"] = False
    components.html("""
    <script>
        setTimeout(function() {
            try {
                var doc = window.parent.document;
                var target = doc.getElementById('ancora_risultati');
                if (target) {
                    target.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            } catch(e) {}
        }, 120);
    </script>
    """, height=0, width=0)

st.markdown(
    """
    <div class="site-footer-box">
        <strong>In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei.</strong><br>
        I link verso Amazon sono link affiliati a pagamento. Prezzi e disponibilità sono soggetti a variazione.<br>
        <a href="?privacy=1" target="_self">Informativa Privacy</a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="display: flex; justify-content: center; align-items: center; width: 100%; margin: 10px 0 15px 0;">
        <a href="#top_page" target="_self" class="btn-back-to-top">
            ⬆️ Torna in alto
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
