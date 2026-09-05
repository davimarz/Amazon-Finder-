import streamlit as st
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
    "Popolarità": "Featured",
    "Recensioni": "AvgCustomerReviews",
})
get_partner_tag = getattr(amazon_api, "get_partner_tag", lambda: "eiapromo-21")
ottieni_offerte_avanzate = getattr(amazon_api, "ottieni_offerte_avanzate", lambda **kwargs: [])
ottieni_vetrina_casuale = getattr(amazon_api, "ottieni_vetrina_casuale", lambda **kwargs: [])

st.session_state.setdefault("current_tab", "vetrina")
st.session_state.setdefault("has_searched", False)
st.session_state.setdefault("item_count", 10)
st.session_state.setdefault("current_page", 1)
st.session_state.setdefault("scroll_to_top_flag", False)
st.session_state.setdefault("scroll_to_results_flag", False)
st.session_state.setdefault("offerte", [])
st.session_state.setdefault("search_notice", "")

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
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 50%, #e0f2fe 100%) !important;
        background-attachment: fixed !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    .block-container {
        padding: 0.20rem 0.35rem 95px 0.35rem !important;
        max-width: 100% !important;
    }

    /* --- INTESTAZIONE COMPATTA IN 2 RIGHE SOTTO I 200PX --- */
    .hero-container-single {
        text-align: center;
        margin: 2px 0 6px 0;
        padding: 2px 0;
        width: 100%;
    }
    .hero-title-single {
        font-size: clamp(1.45rem, 5.5vw, 2.1rem) !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        margin: 0 !important;
        white-space: nowrap !important;
        overflow: hidden;
        text-overflow: ellipsis;
        background: linear-gradient(90deg, #0369a1 0%, #0284c7 50%, #1d4ed8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle-single {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        font-size: 0.72rem;
        color: #334155;
        margin-top: 2px;
        white-space: nowrap !important;
    }
    .ai-badge-chip {
        background: #0284c7;
        color: #ffffff;
        font-size: 0.65rem;
        font-weight: 800;
        padding: 1px 6px;
        border-radius: 4px;
        letter-spacing: 0.5px;
        line-height: 1.2;
    }

    /* --- SEGMENTED CONTROL: 3 PULSANTI FORZATI SU UN'UNICA RIGA (BLU/CIANO NAVY) --- */
    .nav-bar-container {
        width: 100% !important;
        margin-bottom: 6px !important;
    }
    .nav-bar-container [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: stretch !important;
        gap: 3px !important;
        background: #0f172a !important;
        border: 1px solid #334155 !important;
        border-radius: 9px !important;
        padding: 3px !important;
        width: 100% !important;
    }
    .nav-bar-container [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        width: 33.333% !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .nav-bar-container [data-testid="column"] > div {
        width: 100% !important;
    }
    .nav-bar-container button {
        width: 100% !important;
        white-space: nowrap !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        padding: 4px 1px !important;
        min-height: 32px !important;
        height: 32px !important;
        border-radius: 7px !important;
        border: none !important;
        background: transparent !important;
        color: #94a3b8 !important;
        box-shadow: none !important;
        transition: all 0.2s ease;
    }
    .nav-bar-container button:hover {
        background: #1e293b !important;
        color: #ffffff !important;
    }
    .nav-bar-container button[kind="primary"] {
        color: #ffffff !important;
        background: #0284c7 !important;
        box-shadow: 0 1px 5px rgba(2, 132, 199, 0.45) !important;
    }
    .nav-bar-container button[kind="primary"] p {
        color: #ffffff !important;
        font-weight: 800 !important;
    }

    /* --- SEARCH BAR CON LENTE INTEGRATA --- */
    .search-box-native {
        position: relative;
        width: 100%;
        margin-bottom: 5px;
    }
    div[data-testid="stTextInput"]:has(input[aria-label="cerca_input_main"]) {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stTextInput"]:has(input[aria-label="cerca_input_main"]) input {
        border-radius: 8px !important;
        border: 1.5px solid #0284c7 !important;
        padding-right: 36px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        height: 36px !important;
        background-color: #ffffff !important;
        box-shadow: 0 1px 4px rgba(2, 132, 199, 0.15) !important;
    }
    .search-lens-inside {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        pointer-events: none;
        color: #0284c7;
        font-size: 0.85rem;
        font-weight: 900;
        z-index: 5;
    }

    /* --- FILTER CHIPS TOUCH-FRIENDLY (ORIZZONTALI BLU/NAVY) --- */
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] p {
        color: #0369a1 !important;
        font-size: 0.72rem !important;
        font-weight: 800 !important;
        margin-bottom: 2px !important;
    }
    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 4px !important;
        width: 100% !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: #ffffff !important;
        padding: 4px 10px !important;
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
        font-size: 0.70rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stRadio"] input[type="radio"] {
        display: none !important;
    }

    /* --- ACCORDION FILTRI SECONDARI --- */
    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid rgba(2, 132, 199, 0.25) !important;
        border-radius: 8px !important;
        margin-bottom: 6px !important;
    }
    div[data-testid="stExpander"] details summary p {
        font-size: 0.74rem !important;
        font-weight: 800 !important;
        color: #0369a1 !important;
    }

    /* --- SCHEDE PRODOTTO & CONTENITORE --- */
    .tab-content-panel {
        background: rgba(255, 255, 255, 0.65) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1.5px solid rgba(255, 255, 255, 0.85) !important;
        border-radius: 10px !important;
        padding: 5px !important;
        box-shadow: 0 4px 16px rgba(2, 132, 199, 0.10) !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(150deg, #ffffff 0%, #f0fdf4 50%, #dcfce7 100%) !important;
        border: 1.5px solid #059669 !important;
        border-radius: 8px !important;
        padding: 4px 5px !important;
        margin-bottom: 5px !important;
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.12) !important;
    }

    .product-img-wrapper-full {
        width: 100%;
        height: 125px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
        border: 1px solid #86efac;
        border-radius: 6px;
        overflow: hidden;
        padding: 2px;
        margin-bottom: 2px;
    }

    .product-img-wrapper-full img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        display: block;
    }

    .deal-title {
        font-size: 0.80rem !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
        color: #064e3b !important;
        margin: 0 0 4px 0 !important;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 28px;
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
        border-radius: 6px;
        border: 1px solid #fcd200;
        width: 100% !important;
        min-height: 26px;
        height: 26px;
        margin-top: 3px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    }

    .price-delivery-split-row {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 4px !important;
        margin: 2px 0 4px 0 !important;
    }

    .price-subgroup-left {
        display: flex !important;
        align-items: baseline !important;
        gap: 3px !important;
        flex-wrap: wrap !important;
    }

    .deal-price-final {
        font-size: 1.90rem !important;
        font-weight: 900 !important;
        color: #065f46 !important;
        line-height: 1 !important;
    }

    .deal-price-old {
        font-size: 1.25rem !important;
        color: #4b5563 !important;
        text-decoration: line-through;
        margin-left: 2px;
        line-height: 1 !important;
    }

    .deal-badge {
        background-color: #ef4444;
        color: white;
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        padding: 2px 5px !important;
        border-radius: 4px;
        line-height: 1 !important;
    }

    .shipping-badge-prime {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: linear-gradient(135deg, #00a8e8 0%, #007eb9 100%) !important;
        color: #ffffff !important;
        font-size: 0.68rem !important;
        font-weight: 900 !important;
        font-style: italic !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        line-height: 1 !important;
        text-transform: lowercase !important;
    }

    .shipping-badge-free {
        background: rgba(255, 255, 255, 0.95);
        color: #065f46;
        border: 1px solid #6ee7b7;
        padding: 2px 4px;
        border-radius: 4px;
        font-size: 0.66rem;
        font-weight: 800;
    }

    .social-share-row-mobile {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 4px !important;
        margin-top: 4px !important;
        width: 100% !important;
    }

    .share-icon-btn {
        width: 24px !important;
        height: 24px !important;
        border-radius: 4px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: none !important;
        padding: 0 !important;
        cursor: pointer !important;
    }

    .share-icon-btn svg { width: 12px !important; height: 12px !important; fill: #ffffff !important; }
    .btn-wa { background-color: #25D366 !important; }
    .btn-fb { background-color: #1877F2 !important; }
    .btn-ig { background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%) !important; }
    .btn-tg { background-color: #229ED9 !important; }
    .btn-gmail { background-color: #EA4335 !important; }
    .btn-copy { background-color: #475569 !important; }

    .price-source-note, .affiliate-note {
        font-size: 0.58rem;
        color: #475569;
        margin-top: 2px;
        line-height: 1.2;
    }

    /* --- DISCLAIMER FOOTER NON INVASIVO (SCROLLABILE) --- */
    .site-footer-box {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid rgba(2, 132, 199, 0.25);
        border-radius: 8px;
        padding: 8px 10px;
        margin: 15px 0 10px 0;
        text-align: center;
        color: #475569;
        font-size: 11px;
        line-height: 1.35;
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
        border-radius: 6px !important;
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
        return False, "Tutti i campi sono obbligatori."[cite: 3]
    if len(nome_clean) < 3:
        return False, "Inserisci un Nome e Cognome valido (almeno 3 caratteri)."[cite: 3]
    if tel_digits.startswith("39") and len(tel_digits) == 12:
        tel_digits = tel_digits[2:][cite: 3]
    if len(tel_digits) != 10:
        return False, "Il numero di telefono deve essere composto esattamente da 10 cifre (es. 3401234567)."[cite: 3]
    if not EMAIL_REGEX.match(email_clean):
        return False, "L'indirizzo email inserito non è valido (es. nome@dominio.it)."[cite: 3]
    if len(note_clean) < 10:
        return False, "Il messaggio deve contenere almeno 10 caratteri."[cite: 3]
    return True, "OK"[cite: 3]

def init_rate_limit_db():
    conn = sqlite3.connect("rate_limit.db")[cite: 3]
    c = conn.cursor()[cite: 3]
    c.execute("""
        CREATE TABLE IF NOT EXISTS invii_contatti (
            email TEXT,
            data_invio TEXT
        )
    """)[cite: 3]
    conn.commit()[cite: 3]
    conn.close()[cite: 3]

def verifica_puo_inviare(email):
    init_rate_limit_db()[cite: 3]
    today_str = date.today().isoformat()[cite: 3]
    conn = sqlite3.connect("rate_limit.db")[cite: 3]
    c = conn.cursor()[cite: 3]
    c.execute("SELECT COUNT(*) FROM invii_contatti WHERE lower(email) = lower(?) AND data_invio = ?", (email.strip(), today_str))[cite: 3]
    count = c.fetchone()[0][cite: 3]
    conn.close()[cite: 3]
    return count == 0[cite: 3]

def registra_invio_completato(email):
    init_rate_limit_db()[cite: 3]
    today_str = date.today().isoformat()[cite: 3]
    conn = sqlite3.connect("rate_limit.db")[cite: 3]
    c = conn.cursor()[cite: 3]
    c.execute("INSERT INTO invii_contatti (email, data_invio) VALUES (?, ?)", (email.strip().lower(), today_str))[cite: 3]
    conn.commit()[cite: 3]
    conn.close()[cite: 3]

def invia_email_smtp_diretta(nome, telefono, email, note):
    destinatario = "davimarz.social@gmail.com"[cite: 3]
    email_cfg = st.secrets.get("email", {})[cite: 3]
    sender = email_cfg.get("sender", "davimarz.social@gmail.com")[cite: 3]
    app_pwd = email_cfg.get("app_password", "").replace(" ", "")[cite: 3]

    if not app_pwd:
        return False, "Password per le app non configurata nei Secrets di Streamlit."[cite: 3]

    msg = MIMEMultipart()[cite: 3]
    msg['From'] = f"Scala dei Turchi <{sender}>"[cite: 3]
    msg['To'] = destinatario[cite: 3]
    msg['Subject'] = f"🔴 [SCALA DEI TURCHI - SITO] Messaggio da {nome}"[cite: 3]

    corpo = f"""Nuova richiesta o suggerimento ricevuto dal sito Scala dei Turchi:

- Nome e Cognome: {nome}
- Telefono: {telefono}
- Email Utente: {email}

Messaggio / Note:
{note}
"""[cite: 3]
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))[cite: 3]

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=5) as server:[cite: 3]
            server.login(sender, app_pwd)[cite: 3]
            server.sendmail(sender, [destinatario], msg.as_string())[cite: 3]
        return True, "OK"[cite: 3]
    except Exception as e:
        return False, str(e)[cite: 3]

OPZIONI_SCONTO = {
    "Tutti": (0, 100),
    "0-20%": (0, 20),
    "20-50%": (20, 50),
    ">50%": (50, 100)
}[cite: 3]

def set_tab(tab_name):
    st.session_state["current_tab"] = tab_name[cite: 3]
    try:
        st.query_params.clear()[cite: 3]
    except Exception:
        pass[cite: 3]

def esegui_ricerca(increment=False):
    st.session_state["current_tab"] = "cerca"[cite: 3]
    st.session_state["has_searched"] = True[cite: 3]
    st.session_state["search_notice"] = ""[cite: 3]

    vecchi_risultati = st.session_state.get("offerte", [])[cite: 3]
    current_target = max(10, int(st.session_state.get("item_count", 10) or 10))[cite: 3]

    if increment:
        if current_target >= MAX_RESULTS:[cite: 3]
            st.session_state["search_notice"] = f"Limite di {MAX_RESULTS} prodotti raggiunto per questa ricerca."[cite: 3]
            return
        target_count = min(MAX_RESULTS, current_target + 10)[cite: 3]
    else:
        target_count = 10[cite: 3]
        st.session_state["current_page"] = 1[cite: 3]

    st.session_state["item_count"] = target_count[cite: 3]

    kw = st.session_state.get("cerca_keyword_input", "").strip()[cite: 3]
    sort_t = st.session_state.get("cerca_radio_sort", "Prezzo minimo")[cite: 3]
    disc_lbl = st.session_state.get("cerca_radio_disc", "Tutti")[cite: 3]
    min_d, max_d = OPZIONI_SCONTO.get(disc_lbl, (0, 100))[cite: 3]
    free_ship = st.session_state.get("cerca_check_sped_gratis", False)[cite: 3]

    risultati = ottieni_offerte_avanzate(
        keyword=kw,
        sort_type=sort_t,
        solo_spedizione_gratuita=free_ship,
        min_price=None,
        max_price=None,
        min_discount=min_d,
        max_discount=max_d,
        item_count=target_count,
    )[cite: 3]

    prodotti_unici = [][cite: 3]
    asins_visti = set()[cite: 3]
    for prodotto in (risultati or []):[cite: 3]
        asin = str(prodotto.get("asin") or "").strip().upper()[cite: 3]
        if asin and asin not in asins_visti:[cite: 3]
            asins_visti.add(asin)[cite: 3]
            prodotti_unici.append(prodotto)[cite: 3]

    if increment:
        merged = [][cite: 3]
        merged_asins = set()[cite: 3]
        for prodotto in list(vecchi_risultati) + list(prodotti_unici):[cite: 3]
            asin = str(prodotto.get("asin") or "").strip().upper()[cite: 3]
            if asin and asin not in merged_asins:[cite: 3]
                merged_asins.add(asin)[cite: 3]
                merged.append(prodotto)[cite: 3]

        st.session_state["offerte"] = merged[:target_count][cite: 3]
        if len(st.session_state["offerte"]) > len(vecchi_risultati):[cite: 3]
            st.session_state["current_page"] = max(1, (len(st.session_state["offerte"]) + 9) // 10)[cite: 3]
        else:
            st.session_state["search_notice"] = "Non sono disponibili altri prodotti per questa ricerca."[cite: 3]
        
        # Quando si incrementano i prodotti, lo scroll torna alla testata dell'elenco prodotti
        st.session_state["scroll_to_results_flag"] = True
        st.session_state["scroll_to_top_flag"] = False
    else:
        st.session_state["offerte"] = prodotti_unici[:10][cite: 3]
        st.session_state["scroll_to_results_flag"] = True

# --- HEADER: 2 RIGHE COMPATTE SU UN UNICO RIGO CIASCUNA ---
st.markdown("""
<div id="top_page"></div>
<div class="hero-container-single">
    <h1 class="hero-title-single">Scala dei Turchi</h1>
    <div class="hero-subtitle-single">
        <span class="ai-badge-chip">AI DEALS</span>
        <span>by <strong>Davide Marziano</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# GESTIONE SCROLL DINAMICO
if st.session_state.get("scroll_to_top_flag", False):
    st.session_state["scroll_to_top_flag"] = False
    st.markdown("""
    <script>
        setTimeout(function() {
            try {
                const stContainer = window.parent.document.querySelector('[data-testid="stAppViewContainer"]') || window.parent.document.querySelector('section.main') || document.querySelector('[data-testid="stAppViewContainer"]');
                if (stContainer) { stContainer.scrollTo({top: 0, behavior: 'smooth'}); }
            } catch(e) {}
            try {
                const el = window.parent.document.getElementById('top_page') || document.getElementById('top_page');
                if (el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }
            } catch(e) {}
            try { window.scrollTo({top: 0, behavior: 'smooth'}); } catch(e) {}
        }, 60);
    </script>
    """, unsafe_allow_html=True)

if st.session_state.get("scroll_to_results_flag", False):
    st.session_state["scroll_to_results_flag"] = False
    st.markdown("""
    <script>
        setTimeout(function() {
            try {
                const el = window.parent.document.getElementById('ancora_risultati') || document.getElementById('ancora_risultati');
                if (el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }
            } catch(e) {}
        }, 100);
    </script>
    """, unsafe_allow_html=True)

# --- SEGMENTED CONTROL: FORZATURA SU UNICO RIGO ---
st.markdown('<div class="nav-bar-container">', unsafe_allow_html=True)
col_tab1, col_tab2, col_tab3 = st.columns(3)[cite: 3]
with col_tab1:
    is_t1 = (active_tab == "vetrina")[cite: 3]
    st.button("🔥 Vetrina", key="nav_btn_vetrina", type="primary" if is_t1 else "secondary", on_click=set_tab, args=("vetrina",), use_container_width=True)[cite: 3]
with col_tab2:
    is_t2 = (active_tab == "cerca")[cite: 3]
    st.button("🔍 Cerca", key="nav_btn_cerca", type="primary" if is_t2 else "secondary", on_click=set_tab, args=("cerca",), use_container_width=True)[cite: 3]
with col_tab3:
    is_t3 = (active_tab == "contatti")[cite: 3]
    st.button("✉️ Contatti", key="nav_btn_contatti", type="primary" if is_t3 else "secondary", on_click=set_tab, args=("contatti",), use_container_width=True)[cite: 3]
st.markdown('</div>', unsafe_allow_html=True)[cite: 3]

IMG_FALLBACK_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 24 24' fill='none' stroke='%23059669' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><rect x='2' y='3' width='20' height='14' rx='2' ry='2'></rect><line x1='8' y1='21' x2='16' y2='21'></line><line x1='12' y1='17' x2='12' y2='21'></line></svg>"[cite: 3]

def render_product_card(p, tab_key="main"):
    del tab_key[cite: 3]
    with st.container(border=True):[cite: 3]
        col_left, col_center, col_fb = st.columns([1.1, 1.4, 1.2])[cite: 3]

        titolo = str(p.get("titolo") or "Prodotto Amazon")[cite: 3]
        link = str(p.get("link_affiliato") or "")[cite: 3]
        safe_title_html = html.escape(titolo)[cite: 3]
        safe_title_attr = html.escape(titolo, quote=True)[cite: 3]
        safe_link_attr = html.escape(link, quote=True)[cite: 3]
        prezzo_verificato = p.get("prezzo_verificato") is True[cite: 3]

        with col_left:[cite: 3]
            img_url = str(p.get("immagine_url") or IMG_FALLBACK_SVG)[cite: 3]
            safe_img_url = html.escape(img_url, quote=True)[cite: 3]
            safe_fallback = html.escape(IMG_FALLBACK_SVG, quote=True)[cite: 3]
            st.markdown(
                f'<div class="product-img-wrapper-full"><img src="{safe_img_url}" referrerpolicy="no-referrer" loading="lazy" onerror="this.onerror=null;this.src=\'{safe_fallback}\';" alt="{safe_title_attr}"></div>',
                unsafe_allow_html=True,
            )[cite: 3]

        with col_center:[cite: 3]
            st.markdown(f"<div class='deal-title'>{safe_title_html}</div>", unsafe_allow_html=True)[cite: 3]

            if prezzo_verificato:[cite: 3]
                prezzo_finale = float(p.get("prezzo_finale") or 0.0)[cite: 3]
                prezzo_iniziale = float(p.get("prezzo_iniziale") or prezzo_finale)[cite: 3]
                sconto = html.escape(str(p.get("sconto") or ""))[cite: 3]
                badge_html = f"<span class='deal-badge'>{sconto}</span>" if sconto else ""[cite: 3]
                old_price_html = (
                    f"<span class='deal-price-old'>€{prezzo_iniziale:.2f}</span>"
                    if prezzo_iniziale > prezzo_finale else ""
                )[cite: 3]
                prices_sub_html = (
                    f"<div class='price-subgroup-left'>{badge_html}"
                    f"<span class='deal-price-final'>€{prezzo_finale:.2f}</span>{old_price_html}</div>"
                )[cite: 3]

                costo_raw = p.get("costo_spedizione")[cite: 3]
                try:
                    costo_s = float(costo_raw) if costo_raw is not None else None[cite: 3]
                except (TypeError, ValueError):
                    costo_s = None[cite: 3]
                if p.get("is_prime") is True:[cite: 3]
                    ship_html = "<span class='shipping-badge-prime'>prime</span>"[cite: 3]
                elif p.get("is_sped_gratis") is True:[cite: 3]
                    ship_html = "<span class='shipping-badge-free'>🚚 Gratis</span>"[cite: 3]
                elif costo_s is not None and costo_s > 0:[cite: 3]
                    ship_html = f"<span class='shipping-badge-paid'>📦 +€{costo_s:.2f}</span>"[cite: 3]
                else:
                    ship_html = "<span class='shipping-badge-unknown'>🚚 Verifica</span>"[cite: 3]

                st.markdown(
                    f"<div class='price-delivery-split-row'>{prices_sub_html}{ship_html}</div>"
                    "<div class='price-source-note'>Prezzi e disponibilità possono variare.</div>",
                    unsafe_allow_html=True,
                )
                buy_label = "🛒 Acquista su Amazon"[cite: 3]
            else:
                st.markdown(
                    "<div class='price-unverified'>Vedi prezzo su Amazon</div>"
                    "<div class='price-source-note'>Prezzo verificato su Amazon.</div>",
                    unsafe_allow_html=True,
                )
                buy_label = "🛒 Vedi su Amazon"[cite: 3]

            if link:[cite: 3]
                st.markdown(
                    f"<a href='{safe_link_attr}' target='_blank' rel='noopener noreferrer sponsored' class='buy-btn-action' aria-label='{html.escape(buy_label, quote=True)}: {safe_title_attr}'>{buy_label}</a>"
                    "<div class='affiliate-note'>(link affiliato)</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<span class='buy-btn-action' style='opacity:.55;cursor:not-allowed;'>🛒 Link non disponibile</span>",
                    unsafe_allow_html=True,
                )[cite: 3]

            safe_title_text = titolo.replace("\n", " ").strip()[cite: 3]
            share_price = f"\n💰 Prezzo rilevato: €{float(p.get('prezzo_finale', 0.0)):.2f}" if prezzo_verificato else ""[cite: 3]
            share_msg = f"🔥 {safe_title_text}{share_price}\n👉 {link}"[cite: 3]
            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_msg)}"[cite: 3]
            fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(link)}"[cite: 3]
            ig_url = "https://www.instagram.com/"[cite: 3]
            tg_url = f"https://t.me/share/url?url={urllib.parse.quote(link)}&text={urllib.parse.quote(share_msg)}"[cite: 3]
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Offerta&body={urllib.parse.quote(share_msg)}"[cite: 3]
            copy_action = f"navigator.clipboard.writeText({json.dumps(link)}).then(function(){{alert('Link copiato!');}});"

            st.markdown(
                f"""
                <div class='social-share-row-mobile'>
                    <a href='{html.escape(wa_url, quote=True)}' target='_blank' rel='noopener noreferrer' class='share-icon-btn btn-wa' title='WhatsApp'>{SVG_WA}</a>
                    <a href='{html.escape(fb_url, quote=True)}' target='_blank' rel='noopener noreferrer sponsored' class='share-icon-btn btn-fb' title='Facebook'>{SVG_FB}</a>
                    <a href='{html.escape(ig_url, quote=True)}' target='_blank' rel='noopener noreferrer' class='share-icon-btn btn-ig' title='Instagram'>{SVG_IG}</a>
                    <a href='{html.escape(tg_url, quote=True)}' target='_blank' rel='noopener noreferrer sponsored' class='share-icon-btn btn-tg' title='Telegram'>{SVG_TG}</a>
                    <a href='{html.escape(gmail_url, quote=True)}' target='_blank' rel='noopener noreferrer' class='share-icon-btn btn-gmail' title='Gmail'>{SVG_GMAIL}</a>
                    <button type='button' onclick="{html.escape(copy_action, quote=True)}" class='share-icon-btn btn-copy' title='Copia Link'>{SVG_COPY}</button>
                </div>
                """,
                unsafe_allow_html=True,
            )[cite: 3]

        with col_fb:[cite: 3]
            voto_raw = p.get("voto_medio")[cite: 3]
            num_raw = p.get("num_recensioni")[cite: 3]
            try:
                voto = float(voto_raw) if voto_raw is not None else None[cite: 3]
            except (TypeError, ValueError):
                voto = None[cite: 3]
            try:
                num_val = int(num_raw) if num_raw is not None else None[cite: 3]
            except (TypeError, ValueError):
                num_val = None[cite: 3]

            if voto is not None and 0 < voto <= 5:[cite: 3]
                voto_str = f"{voto:.1f}".replace(".", ",")[cite: 3]
                stelle_piene = max(0, min(5, int(round(voto))))[cite: 3]
                stelle_icon = "★" * stelle_piene + "☆" * (5 - stelle_piene)[cite: 3]
                count_html = f"<span class='feedback-subcount'>({num_val})</span>" if num_val is not None else ""[cite: 3]
                feedback_html = (
                    "<div class='feedback-container'><div class='feedback-stars-row'>"
                    f"<span class='feedback-stars'>{stelle_icon}</span>"
                    f"<span class='feedback-score-text'>{voto_str}</span>{count_html}</div></div>"
                )[cite: 3]
            else:
                feedback_html = (
                    "<div class='feedback-container'><div class='feedback-stars-row'>"
                    "<span class='feedback-score-text'>Recensioni su Amazon</span></div></div>"
                )
            st.markdown(feedback_html, unsafe_allow_html=True)[cite: 3]

st.markdown('<div class="tab-content-panel">', unsafe_allow_html=True)[cite: 3]

if active_tab == "vetrina":[cite: 3]
    st.markdown("""
        <h2 style='font-size: 0.90rem; font-weight: 800; color: #064e3b; margin: 2px 0 2px 2px;'>🔥 Offerte in Vetrina</h2>
        <p style='font-size: 0.70rem; color: #475569; margin: 0 0 6px 2px;'>Prezzi e sconti confermati su Amazon al momento dell'acquisto.</p>
    """, unsafe_allow_html=True)

    vetrina_items = st.session_state.get("offerte_vetrina", [])[cite: 3]
    if vetrina_items:[cite: 3]
        for idx in range(0, len(vetrina_items), 2):[cite: 3]
            col_l, col_r = st.columns(2)[cite: 3]
            with col_l:[cite: 3]
                render_product_card(vetrina_items[idx], tab_key=f"vetrina_{idx}")[cite: 3]
            if idx + 1 < len(vetrina_items):[cite: 3]
                with col_r:[cite: 3]
                    render_product_card(vetrina_items[idx + 1], tab_key=f"vetrina_{idx + 1}")[cite: 3]
    else:
        st.info("Nessun prodotto disponibile in vetrina al momento.")[cite: 3]

elif active_tab == "cerca":[cite: 3]
    if st.session_state.get("cerca_radio_sort") == "Numero di vendite":[cite: 3]
        st.session_state["cerca_radio_sort"] = "Popolarità"[cite: 3]

    # --- BARRA DI RICERCA CON LENTE INTEGRATA ---
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

    # --- FILTER CHIPS: ORDINAMENTO RAPIDO ---
    st.radio(
        "Ordinamento:",
        list(SORT_MAPPINGS.keys()),
        index=0,
        horizontal=True,
        key="cerca_radio_sort",
        on_change=esegui_ricerca,
        args=(False,)
    )

    # --- ACCORDION FILTRI SECONDARI ---
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
            "🚚 Spedizione Prime / Consegna gratuita",
            value=False,
            key="cerca_check_sped_gratis",
            on_change=esegui_ricerca,
            args=(False,)
        )

    if st.session_state.get("search_notice"):[cite: 3]
        st.info(st.session_state.get("search_notice"))[cite: 3]

    prodotti_cerca = st.session_state.get("offerte", [])[cite: 3]
    if prodotti_cerca:[cite: 3]
        tot_offerte = len(prodotti_cerca)[cite: 3]
        tot_pagine = max(1, (tot_offerte + 9) // 10)[cite: 3]

        if tot_pagine > 1:[cite: 3]
            st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
            cols_pag = st.columns([1] * tot_pagine + [max(1, 10 - tot_pagine)])[cite: 3]
            for p_num in range(1, tot_pagine + 1):[cite: 3]
                with cols_pag[p_num - 1]:[cite: 3]
                    is_active = (st.session_state.get("current_page", 1) == p_num)[cite: 3]
                    btn_type = "primary" if is_active else "secondary"[cite: 3]
                    if st.button(f"P.{p_num}", key=f"btn_page_{p_num}", type=btn_type, use_container_width=True):
                        st.session_state["current_page"] = p_num[cite: 3]
                        st.session_state["current_tab"] = "cerca"[cite: 3]
                        st.session_state["scroll_to_results_flag"] = True
                        st.rerun()[cite: 3]

        start_idx = (st.session_state.get("current_page", 1) - 1) * 10[cite: 3]
        end_idx = min(start_idx + 10, tot_offerte)[cite: 3]
        offerte_pagina = prodotti_cerca[start_idx:end_idx][cite: 3]

        # ANCORA DI DESTINAZIONE DELLO SCROLL
        st.markdown('<div id="ancora_risultati" style="scroll-margin-top: 15px;"></div>', unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 0.72rem; font-weight: 800; color: #0369a1; margin: 4px 0 3px 2px;'>Prodotti {start_idx + 1}-{end_idx} di {tot_offerte}:</p>", unsafe_allow_html=True)

        for idx in range(0, len(offerte_pagina), 2):[cite: 3]
            col_l, col_r = st.columns(2)[cite: 3]
            with col_l:[cite: 3]
                render_product_card(offerte_pagina[idx], tab_key=f"cerca_p{st.session_state.get('current_page', 1)}_{idx}")[cite: 3]
            if idx + 1 < len(offerte_pagina):[cite: 3]
                with col_r:[cite: 3]
                    render_product_card(offerte_pagina[idx + 1], tab_key=f"cerca_p{st.session_state.get('current_page', 1)}_{idx + 1}")[cite: 3]

        # PULSANTE + ALTRI 10 ESCLUSIVAMENTE IN FONDO
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.button(
            "➕ Carica altri 10 prodotti ⬇️", key="btn_altri_10_bottom", on_click=esegui_ricerca, args=(True,),
            use_container_width=True, disabled=int(st.session_state.get("item_count", 10)) >= MAX_RESULTS[cite: 3]
        )

    elif st.session_state.get("has_searched", False):[cite: 3]
        st.warning("Nessun prodotto trovato. Prova con una parola chiave più generica o imposta lo Sconto su 'Tutti'.")

elif active_tab == "privacy":[cite: 3]
    st.markdown("""
    <h2 style='font-size:1.00rem;color:#064e3b;margin:4px 0 6px 2px;'>Informativa privacy</h2>
    <div style='font-size:.76rem;line-height:1.5;color:#334155;padding:4px 6px;'>
    <p><strong>Titolare e contatti:</strong> davimarz.social@gmail.com.</p>
    <p><strong>Finalità:</strong> I dati inseriti nel modulo contatti servono solo per rispondere al tuo messaggio e non vengono ceduti a terzi.</p>
    <p><strong>Affiliazione Amazon:</strong> Questo sito partecipa al Programma di Affiliazione Amazon, un programma pubblicitario che consente di percepire commissioni pubblicitarie collegando a Amazon.it.</p>
    </div>
    """, unsafe_allow_html=True)
    st.button("← Torna alla vetrina", key="privacy_back", on_click=set_tab, args=("vetrina",))[cite: 3]

elif active_tab == "contatti":[cite: 3]
    with st.container(border=True):[cite: 3]
        st.markdown("<p style='font-size: 0.80rem; font-weight: 700; color: #064e3b; margin-bottom: 4px;'>Inviaci un messaggio o una richiesta (Campi obbligatori):</p>", unsafe_allow_html=True)
        with st.form("form_scheda_contatti", clear_on_submit=True):[cite: 3]
            nome_val = st.text_input("Nome e Cognome*", placeholder="Es. Mario Rossi")[cite: 3]
            tel_val = st.text_input("Numero di telefono (10 cifre)*", placeholder="Es. 3401234567")[cite: 3]
            email_val = st.text_input("Email*", placeholder="Es. mario.rossi@email.com")[cite: 3]
            note_val = st.text_area("Messaggio*", placeholder="Scrivi qui il tuo messaggio...", height=110)
            privacy_ack = st.checkbox("Accetto l'informativa privacy.*")
            st.markdown("<small><a href='?privacy=1' target='_self'>Leggi privacy</a></small>", unsafe_allow_html=True)
            
            btn_send_form = st.form_submit_button("✉️ Invia Messaggio", use_container_width=True)[cite: 3]
            if btn_send_form:[cite: 3]
                valido, msg_validazione = valida_campi_contatto(nome_val, tel_val, email_val, note_val)[cite: 3]
                if not valido:[cite: 3]
                    st.error(msg_validazione)[cite: 3]
                elif not privacy_ack:[cite: 3]
                    st.error("Conferma di aver letto l'informativa privacy.")
                elif not verifica_puo_inviare(email_val.strip()):[cite: 3]
                    st.warning("Hai già inviato un messaggio oggi con questa email. Riprova domani!")[cite: 3]
                else:
                    with st.spinner("Invio in corso..."):
                        ok, msg_err = invia_email_smtp_diretta(nome_val.strip(), tel_val.strip(), email_val.strip(), note_val.strip())[cite: 3]
                    if ok:[cite: 3]
                        registra_invio_completato(email_val.strip())[cite: 3]
                        st.success("Messaggio inviato correttamente!")
                    else:
                        st.error(f"Errore: {msg_err}")[cite: 3]

st.markdown('</div>', unsafe_allow_html=True)[cite: 3]

# --- DISCLAIMER FOOTER NON SOVRAPPOSTO (SCROLLABILE) ---
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
