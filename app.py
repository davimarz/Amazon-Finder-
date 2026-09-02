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

from amazon_api import (
    MAX_RESULTS,
    SORT_MAPPINGS,
    get_partner_tag,
    ottieni_offerte_avanzate,
    ottieni_vetrina_casuale,
)

st.set_page_config(
    page_title="Scaladeiturchi | Offerte Amazon AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- INIZIALIZZAZIONE STATO -----------------
st.session_state.setdefault("current_tab", "vetrina")
st.session_state.setdefault("has_searched", False)
st.session_state.setdefault("item_count", 10)
st.session_state.setdefault("current_page", 1)
st.session_state.setdefault("scroll_to_top_flag", False)
st.session_state.setdefault("offerte", [])
st.session_state.setdefault("search_notice", "")

try:
    if str(st.query_params.get("privacy", "")) == "1":
        st.session_state["current_tab"] = "privacy"
except Exception:
    pass

amazon_configured = bool(get_partner_tag())
if amazon_configured and ("offerte_vetrina" not in st.session_state or not st.session_state.get("offerte_vetrina")):
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
        padding: 0.20rem 0.35rem 0.80rem 0.35rem !important;
        max-width: 100% !important;
    }

    .nav-bar-container [data-testid="stHorizontalBlock"] {
        background: rgba(255, 255, 255, 0.85) !important;
        padding: 2px 4px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(2, 132, 199, 0.25) !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
        display: flex !important;
        width: 100% !important;
    }

    .nav-bar-container button {
        flex: 1 1 0% !important;
        color: #0369a1 !important;
        font-weight: 800 !important;
        font-size: 0.76rem !important;
        background: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid rgba(2, 132, 199, 0.2) !important;
        border-radius: 6px !important;
        padding: 4px 5px !important;
        min-height: 28px !important;
        height: 28px !important;
        text-align: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
        box-shadow: none !important;
    }

    .nav-bar-container button:hover {
        background: rgba(224, 242, 254, 0.9) !important;
        border-color: #0284c7 !important;
    }

    .nav-bar-container button[kind="primary"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
        border-color: #0284c7 !important;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35) !important;
    }

    .nav-bar-container button[kind="primary"] p {
        color: #ffffff !important;
        font-weight: 900 !important;
    }

    .tab-content-panel {
        background: rgba(255, 255, 255, 0.60) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 2px solid rgba(255, 255, 255, 0.85) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        margin-top: 2px !important;
        box-shadow: 0 6px 20px rgba(2, 132, 199, 0.12) !important;
    }

    .hero-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        margin: 0 auto 2px auto;
        text-align: center;
    }

    .hero-title-main {
        font-size: clamp(2.2rem, 7.8vw, 3.2rem);
        font-weight: 900;
        line-height: 0.95;
        width: 100%;
        text-align: center;
        letter-spacing: -0.5px;
        margin: 0;
        background: linear-gradient(90deg, #0369a1 0%, #0284c7 50%, #1d4ed8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle-box {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
        margin: 0 0 2px 0;
    }

    .hero-subtitle-text {
        font-size: clamp(1.4rem, 5.0vw, 1.9rem);
        font-weight: 800;
        color: #0f172a;
        font-variant: small-caps;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        line-height: 1;
        margin: 0;
    }

    .ai-badge {
        background: #0284c7;
        color: #ffffff;
        font-size: 0.72em;
        font-weight: 900;
        padding: 2px 6px;
        border-radius: 5px;
        line-height: 1;
        margin: 0;
    }

    .hero-author-tag {
        font-size: 0.70rem;
        color: #334155;
        font-weight: 600;
        margin: 0 0 4px 0;
        line-height: 1;
    }

    .hero-author-tag strong { color: #0369a1; }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        background: linear-gradient(150deg, #ffffff 0%, #f0fdf4 50%, #dcfce7 100%) !important;
        border: 2px solid #059669 !important;
        border-radius: 10px !important;
        padding: 5px 6px !important;
        margin-bottom: 6px !important;
        box-shadow: 0 3px 12px rgba(5, 150, 105, 0.18) !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
        gap: 0px !important;
        row-gap: 0px !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] > div {
        margin: 0px !important;
        padding: 0px !important;
        gap: 0px !important;
    }

    div[data-testid="stTextInput"], div[data-testid="stTextArea"] {
        margin: 0px 0px 3px 0px !important;
        padding: 0px !important;
    }

    div[data-baseweb="input"] {
        background-color: #ffffff !important;
        border: 1.5px solid #10b981 !important;
        border-radius: 5px !important;
        min-height: 28px !important;
        height: 28px !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: 0 1px 3px rgba(5, 150, 105, 0.12) !important;
    }

    div[data-baseweb="textarea"] {
        background-color: #ffffff !important;
        border: 1.5px solid #10b981 !important;
        border-radius: 5px !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: 0 1px 3px rgba(5, 150, 105, 0.12) !important;
    }

    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="textarea"]:focus-within {
        border-color: #047857 !important;
    }

    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
        color: #064e3b !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        padding: 4px 8px !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stTextInput"]) div[data-testid="stElementContainer"]:nth-of-type(2) button {
        background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        border: 1px solid #0284c7 !important;
        border-radius: 5px !important;
        font-weight: 900 !important;
        font-size: 0.78rem !important;
        min-height: 28px !important;
        height: 28px !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 0 2px 0 !important;
        box-shadow: 0 1px 3px rgba(2, 132, 199, 0.3) !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stTextInput"]) div[data-testid="stElementContainer"]:nth-of-type(2) button p {
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 0.78rem !important;
        line-height: 1 !important;
        margin: 0 !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stTextInput"]) div[data-testid="stElementContainer"]:nth-of-type(3) button {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        color: #ffffff !important;
        border: 1px solid #10b981 !important;
        border-radius: 5px !important;
        font-weight: 900 !important;
        font-size: 0.78rem !important;
        min-height: 28px !important;
        height: 28px !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: 0 1px 3px rgba(5, 150, 105, 0.25) !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stTextInput"]) div[data-testid="stElementContainer"]:nth-of-type(3) button p {
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 0.78rem !important;
        line-height: 1 !important;
        margin: 0 !important;
    }

    div[data-testid="stRadio"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 1px !important;
        margin: 1px 0 2px 0 !important;
    }

    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] p {
        color: #064e3b !important;
        font-size: 0.74rem !important;
        font-weight: 800 !important;
        margin-bottom: 2px !important;
    }

    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 3px !important;
        width: 100% !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: #ffffff !important;
        padding: 2px 4px !important;
        border-radius: 5px !important;
        border: 1px solid #a7f3d0 !important;
        margin: 0 !important;
        flex: 1 1 0% !important;
        min-width: 0 !important;
        text-align: center !important;
        justify-content: center !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] div {
        color: #064e3b !important;
        font-size: 0.68rem !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
    }

    div[data-testid="stCheckbox"] {
        background: #ffffff !important;
        padding: 3px 6px !important;
        border-radius: 5px !important;
        border: 1px solid #a7f3d0 !important;
        min-height: 24px !important;
        margin: 3px 0 1px 0 !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }

    div[data-testid="stCheckbox"] label p {
        font-size: 0.72rem !important;
        font-weight: 800 !important;
        color: #065f46 !important;
    }

    .product-img-wrapper-full {
        width: 100%;
        height: 135px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
        border: 1px solid #86efac;
        border-radius: 6px;
        overflow: hidden;
        padding: 3px;
        margin-bottom: 4px;
    }

    .product-img-wrapper-full img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        display: block;
    }

    .deal-title {
        font-size: 0.82rem !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        color: #064e3b !important;
        margin: 0 0 6px 0 !important;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 32px;
        width: 100% !important;
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
        margin-top: 3px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    }

    .price-delivery-split-row {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 6px !important;
        margin: 4px 0 6px 0 !important;
    }

    .price-subgroup-left {
        display: flex !important;
        align-items: baseline !important;
        gap: 4px !important;
        flex-wrap: wrap !important;
    }

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
        margin-left: 4px;
        line-height: 1 !important;
    }

    .deal-badge {
        background-color: #ef4444;
        color: white;
        font-size: 1.30rem !important;
        font-weight: 800 !important;
        padding: 2px 6px !important;
        border-radius: 4px;
        line-height: 1 !important;
        display: inline-block !important;
    }

    .shipping-badge-prime {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: linear-gradient(135deg, #00a8e8 0%, #007eb9 100%) !important;
        color: #ffffff !important;
        font-size: 0.70rem !important;
        font-weight: 900 !important;
        font-style: italic !important;
        letter-spacing: 0.5px !important;
        padding: 2px 7px !important;
        border-radius: 4px !important;
        box-shadow: 0 1px 3px rgba(0, 168, 232, 0.35) !important;
        line-height: 1 !important;
        text-transform: lowercase !important;
    }

    .shipping-badge-prime::before {
        content: "✓ " !important;
        font-style: normal !important;
        font-weight: 900 !important;
        color: #ff9900 !important;
        margin-right: 2px !important;
    }

    .shipping-badge-free {
        background: rgba(255, 255, 255, 0.95);
        color: #065f46;
        border: 1px solid #6ee7b7;
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 800;
    }

    .shipping-badge-paid {
        background: rgba(255, 255, 255, 0.95);
        color: #92400e;
        border: 1px solid #fde68a;
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 800;
    }

    .shipping-badge-unknown {
        background: rgba(255, 255, 255, 0.95);
        color: #475569;
        border: 1px solid #cbd5e1;
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 800;
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
    .fb-bar-bg { flex: 1; height: 6px; background-color: #f1f5f9; border-radius: 2px; overflow: hidden; }
    .fb-bar-fill { height: 100%; background-color: #ff6e00; }
    .fb-pct { width: 18px; text-align: right; color: #007185; font-size: 0.60rem; }

    .social-share-row-mobile {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 5px !important;
        margin-top: 5px !important;
        width: 100% !important;
        flex-wrap: wrap !important;
    }

    .share-icon-btn {
        width: 26px !important;
        height: 26px !important;
        min-width: 26px !important;
        max-width: 26px !important;
        flex-shrink: 0 !important;
        border-radius: 5px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        text-decoration: none !important;
        cursor: pointer !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.15) !important;
    }

    .share-icon-btn svg {
        width: 13px !important;
        height: 13px !important;
        fill: #ffffff !important;
        pointer-events: none !important;
    }

    .btn-wa { background-color: #25D366 !important; }
    .btn-fb { background-color: #1877F2 !important; }
    .btn-ig { background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%) !important; }
    .btn-tg { background-color: #229ED9 !important; }
    .btn-gmail { background-color: #EA4335 !important; }
    .btn-copy { background-color: #475569 !important; }

    .btn-back-to-top {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        padding: 8px 24px !important;
        background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        text-decoration: none !important;
        border-radius: 8px !important;
        font-weight: 800 !important;
        font-size: 0.82rem !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35) !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
    }

    .btn-back-to-top:hover {
        background: linear-gradient(135deg, #0369a1 0%, #1e40af 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(2, 132, 199, 0.45) !important;
        color: #ffffff !important;
    }

    .price-unverified {
        font-size: 1.05rem;
        font-weight: 900;
        color: #065f46;
        line-height: 1.15;
        padding: 4px 0;
    }

    .price-source-note, .affiliate-note {
        font-size: 0.62rem;
        color: #475569;
        margin-top: 2px;
        line-height: 1.25;
    }

    .site-footer-box {
        background: rgba(255,255,255,.82);
        border: 1px solid rgba(2,132,199,.25);
        border-radius: 8px;
        padding: 8px 10px;
        margin: 4px 0 10px 0;
        text-align: center;
        color: #334155;
        font-size: .68rem;
        line-height: 1.45;
    }

    .site-footer-box a { color: #0369a1; font-weight: 800; text-decoration: underline; }
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
    msg['Subject'] = f"🔴 [SCALA DEI TURCHI - SITO] Messaggio da {nome}"

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
        if len(prodotti_unici) > len(vecchi_risultati):
            st.session_state["offerte"] = prodotti_unici
            st.session_state["current_page"] = max(1, (len(prodotti_unici) + 9) // 10)
        else:
            st.session_state["offerte"] = vecchi_risultati
            st.session_state["search_notice"] = "Non sono disponibili altri prodotti verificabili per questa ricerca."
    else:
        st.session_state["offerte"] = prodotti_unici

    st.session_state["scroll_to_top_flag"] = True

st.markdown("""
<div id="top_page" style="position: absolute; top: 0; left: 0; height: 1px; width: 1px;"></div>
<div class="hero-container">
    <h1 class="hero-title-main">Scala dei Turchi</h1>
    <div class="hero-subtitle-box">
        <span class="hero-subtitle-text">Offerte Amazon</span>
        <span class="ai-badge">AI</span>
    </div>
    <div class="hero-author-tag">Realizzato da <strong>Davide Marziano</strong></div>
</div>
""", unsafe_allow_html=True)

if not amazon_configured:
    st.error("Configurazione Amazon incompleta: inserisci partner_tag nei Secrets di Streamlit.")

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
        }, 50);
    </script>
    """, unsafe_allow_html=True)

# BARRA DI NAVIGAZIONE A 3 SCHEDE
st.markdown('<div class="nav-bar-container">', unsafe_allow_html=True)
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

IMG_FALLBACK_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 24 24' fill='none' stroke='%23059669' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><rect x='2' y='3' width='20' height='14' rx='2' ry='2'></rect><line x1='8' y1='21' x2='16' y2='21'></line><line x1='12' y1='17' x2='12' y2='21'></line></svg>"

def render_product_card(p, tab_key="main"):
    del tab_key
    with st.container(border=True):
        col_left, col_center, col_fb = st.columns([1.1, 1.4, 1.2])

        titolo = str(p.get("titolo") or "Prodotto Amazon")
        link = str(p.get("link_affiliato") or "")
        safe_title_html = html.escape(titolo)
        safe_title_attr = html.escape(titolo, quote=True)
        safe_link_attr = html.escape(link, quote=True)
        prezzo_verificato = p.get("prezzo_verificato") is True

        with col_left:
            img_url = str(p.get("immagine_url") or IMG_FALLBACK_SVG)
            safe_img_url = html.escape(img_url, quote=True)
            safe_fallback = html.escape(IMG_FALLBACK_SVG, quote=True)
            st.markdown(
                f'<div class="product-img-wrapper-full"><img src="{safe_img_url}" referrerpolicy="no-referrer" loading="lazy" onerror="this.onerror=null;this.src=\'{safe_fallback}\';" alt="{safe_title_attr}"></div>',
                unsafe_allow_html=True,
            )

        with col_center:
            st.markdown(f"<div class='deal-title'>{safe_title_html}</div>", unsafe_allow_html=True)

            if prezzo_verificato:
                prezzo_finale = float(p.get("prezzo_finale") or 0.0)
                prezzo_iniziale = float(p.get("prezzo_iniziale") or prezzo_finale)
                prezzo_finale_display = str(p.get("prezzo_finale_display") or "").strip()
                prezzo_iniziale_display = str(p.get("prezzo_iniziale_display") or "").strip()
                if not prezzo_finale_display:
                    prezzo_finale_display = f"€{prezzo_finale:.2f}"
                if prezzo_iniziale > prezzo_finale and not prezzo_iniziale_display:
                    prezzo_iniziale_display = f"€{prezzo_iniziale:.2f}"
                sconto = html.escape(str(p.get("sconto") or ""))
                badge_html = f"<span class='deal-badge'>{sconto}</span>" if sconto else ""
                old_price_html = (
                    f"<span class='deal-price-old'>{html.escape(prezzo_iniziale_display)}</span>"
                    if prezzo_iniziale > prezzo_finale and prezzo_iniziale_display else ""
                )
                prices_sub_html = (
                    f"<div class='price-subgroup-left'>{badge_html}"
                    f"<span class='deal-price-final'>{html.escape(prezzo_finale_display)}</span>{old_price_html}</div>"
                )

                costo_raw = p.get("costo_spedizione")
                try:
                    costo_s = float(costo_raw) if costo_raw is not None else None
                except (TypeError, ValueError):
                    costo_s = None
                if p.get("is_prime") is True:
                    ship_html = "<span class='shipping-badge-prime'>prime</span>"
                elif p.get("is_sped_gratis") is True:
                    ship_html = "<span class='shipping-badge-free'>🚚 Gratis</span>"
                elif costo_s is not None and costo_s > 0:
                    ship_html = f"<span class='shipping-badge-paid'>📦 +€{costo_s:.2f}</span>"
                else:
                    ship_html = "<span class='shipping-badge-unknown'>🚚 Verifica</span>"

                st.markdown(
                    f"<div class='price-delivery-split-row'>{prices_sub_html}{ship_html}</div>"
                    "<div class='price-source-note'>Prezzo verificato con Amazon Creators API. Prezzi e disponibilità possono variare.</div>",
                    unsafe_allow_html=True,
                )
                share_price = f"\n💰 Prezzo rilevato: {prezzo_finale_display}"
                buy_label = "🛒 Acquista su Amazon"
            else:
                st.markdown(
                    "<div class='price-unverified'>Vedi prezzo su Amazon</div>"
                    "<div class='price-source-note'>Prezzo, sconto e disponibilità confermati direttamente su Amazon.</div>",
                    unsafe_allow_html=True,
                )
                share_price = ""
                buy_label = "🛒 Vedi su Amazon"

            if link:
                st.markdown(
                    f"<a href='{safe_link_attr}' target='_blank' rel='noopener noreferrer sponsored' class='buy-btn-action' aria-label='{html.escape(buy_label, quote=True)}: {safe_title_attr}'>{buy_label}</a>"
                    "<div class='affiliate-note'>(link a pagamento)</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<span class='buy-btn-action' style='opacity:.55;cursor:not-allowed;'>🛒 Link non disponibile</span>",
                    unsafe_allow_html=True,
                )

            safe_title_text = titolo.replace("\n", " ").strip()
            share_msg = f"🔥 {safe_title_text}{share_price}\n👉 {link}"
            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_msg)}"
            fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(link)}"
            ig_url = "https://www.instagram.com/"
            tg_url = f"https://t.me/share/url?url={urllib.parse.quote(link)}&text={urllib.parse.quote(share_msg)}"
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Offerta&body={urllib.parse.quote(share_msg)}"
            copy_action = f"navigator.clipboard.writeText({json.dumps(link)}).then(function(){{alert('Link copiato negli appunti!');}});"

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
            )

        with col_fb:
            voto_raw = p.get("voto_medio")
            num_raw = p.get("num_recensioni")
            try:
                voto = float(voto_raw) if voto_raw is not None else None
            except (TypeError, ValueError):
                voto = None
            try:
                num_val = int(num_raw) if num_raw is not None else None
            except (TypeError, ValueError):
                num_val = None

            if voto is not None and 0 < voto <= 5:
                voto_str = f"{voto:.1f}".replace(".", ",")
                stelle_piene = max(0, min(5, int(round(voto))))
                stelle_icon = "★" * stelle_piene + "☆" * (5 - stelle_piene)
                count_html = f"<span class='feedback-subcount'>({num_val})</span>" if num_val is not None else ""
                feedback_html = (
                    "<div class='feedback-container'><div class='feedback-stars-row'>"
                    f"<span class='feedback-stars'>{stelle_icon}</span>"
                    f"<span class='feedback-score-text'>{voto_str}</span>{count_html}</div></div>"
                )
            else:
                feedback_html = (
                    "<div class='feedback-container'><div class='feedback-stars-row'>"
                    "<span class='feedback-score-text'>Recensioni: verifica su Amazon</span></div></div>"
                )
            st.markdown(feedback_html, unsafe_allow_html=True)


# RENDER DEL CONTENUTO DELLE SCHEDE
st.markdown('<div class="tab-content-panel">', unsafe_allow_html=True)

if active_tab == "vetrina":
    st.markdown("""
        <h2 style='font-size: 0.95rem; font-weight: 800; color: #064e3b; margin: 4px 0 2px 2px;'>🔥 Offerte Vetrina Amazon</h2>
        <p style='font-size: 0.74rem; font-weight: 600; color: #334155; margin: 0 0 10px 2px; font-style: italic;'>*Prezzi e disponibilità possono variare su Amazon in base a variante, taglia, colore e momento dell'acquisto.*</p>
    """, unsafe_allow_html=True)

    vetrina_items = st.session_state.get("offerte_vetrina", [])
    if vetrina_items:
        for idx in range(0, len(vetrina_items), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(vetrina_items[idx], tab_key=f"vetrina_{idx}")
            if idx + 1 < len(vetrina_items):
                with col_r:
                    render_product_card(vetrina_items[idx + 1], tab_key=f"vetrina_{idx + 1}")
    else:
        st.info("Nessun prodotto disponibile in vetrina al momento.")

elif active_tab == "cerca":
    if st.session_state.get("cerca_radio_sort") == "Numero di vendite":
        st.session_state["cerca_radio_sort"] = "Popolarità"

    with st.container(border=True):
        st.text_input(
            "Cerca:",
            placeholder="Cosa cerchi? (es. cuffie, smartphone, macchina caffe)...",
            key="cerca_keyword_input",
            label_visibility="collapsed",
            on_change=esegui_ricerca,
            args=(False,)
        )
        st.button("🔍 Cerca", key="btn_cerca_submit", on_click=esegui_ricerca, args=(False,), use_container_width=True)
        st.button(
            "➕ Altri 10", key="btn_altri_10_top", on_click=esegui_ricerca, args=(True,),
            use_container_width=True, disabled=int(st.session_state.get("item_count", 10)) >= MAX_RESULTS
        )

    with st.container(border=True):
        st.radio(
            "🏷️ Ordinamento:",
            list(SORT_MAPPINGS.keys()),
            index=0,
            horizontal=True,
            key="cerca_radio_sort"
        )

        st.radio(
            "🔥 Sconto:",
            list(OPZIONI_SCONTO.keys()),
            index=0,
            horizontal=True,
            key="cerca_radio_disc"
        )

        st.checkbox(
            "🚚 Spedizione gratuita / Prime",
            value=False,
            key="cerca_check_sped_gratis"
        )

    if st.session_state.get("search_notice"):
        st.info(st.session_state.get("search_notice"))

    prodotti_cerca = st.session_state.get("offerte", [])
    if prodotti_cerca:
        tot_offerte = len(prodotti_cerca)
        tot_pagine = max(1, (tot_offerte + 9) // 10)

        if tot_pagine > 1:
            st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
            cols_pag = st.columns([1] * tot_pagine + [max(1, 10 - tot_pagine)])
            for p_num in range(1, tot_pagine + 1):
                with cols_pag[p_num - 1]:
                    is_active = (st.session_state.get("current_page", 1) == p_num)
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(f"Pagina {p_num}", key=f"btn_page_{p_num}", type=btn_type, use_container_width=True):
                        st.session_state["current_page"] = p_num
                        st.session_state["current_tab"] = "cerca"
                        st.session_state["scroll_to_top_flag"] = True
                        st.rerun()

        start_idx = (st.session_state.get("current_page", 1) - 1) * 10
        end_idx = min(start_idx + 10, tot_offerte)
        offerte_pagina = prodotti_cerca[start_idx:end_idx]

        st.markdown(f"<p style='font-size: 0.72rem; font-weight: 700; color: #0369a1; margin: 4px 0 2px 2px;'>Visualizzati {start_idx + 1}-{end_idx} di {tot_offerte} prodotti (Pagina {st.session_state.get('current_page', 1)} di {tot_pagine}):</p>", unsafe_allow_html=True)

        for idx in range(0, len(offerte_pagina), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(offerte_pagina[idx], tab_key=f"cerca_p{st.session_state.get('current_page', 1)}_{idx}")
            if idx + 1 < len(offerte_pagina):
                with col_r:
                    render_product_card(offerte_pagina[idx + 1], tab_key=f"cerca_p{st.session_state.get('current_page', 1)}_{idx + 1}")

        st.markdown("<div style='margin-top: 10px; margin-bottom: 5px;'></div>", unsafe_allow_html=True)
        st.button(
            "➕ Altri 10", key="btn_altri_10_bottom", on_click=esegui_ricerca, args=(True,),
            use_container_width=True, disabled=int(st.session_state.get("item_count", 10)) >= MAX_RESULTS
        )

    elif st.session_state.get("has_searched", False):
        st.warning("Nessun prodotto trovato con i filtri selezionati. Prova a inserire un termine diverso o a impostare lo Sconto su 'Tutti'.")

elif active_tab == "privacy":
    st.markdown("""
    <h2 style='font-size:1.05rem;color:#064e3b;margin:4px 0 8px 2px;'>Informativa privacy</h2>
    <div style='font-size:.78rem;line-height:1.55;color:#334155;padding:4px 6px;'>
    <p><strong>Titolare e contatti.</strong> I dati inviati tramite il modulo di contatto sono gestiti dal responsabile del sito Scala dei Turchi. Per richieste relative ai dati personali puoi utilizzare l'indirizzo <strong>davimarz.social@gmail.com</strong>.</p>
    <p><strong>Dati trattati.</strong> Il modulo raccoglie nome e cognome, numero di telefono, indirizzo email e contenuto del messaggio esclusivamente per ricevere e gestire la richiesta inviata.</p>
    <p><strong>Finalità e conservazione.</strong> I dati vengono utilizzati per rispondere alla richiesta e conservati solo per il tempo necessario alla sua gestione e agli eventuali obblighi applicabili. Non vengono utilizzati per profilazione pubblicitaria.</p>
    <p><strong>Destinatari.</strong> I dati possono transitare attraverso i servizi tecnici necessari all'hosting e all'invio email. Non vengono venduti.</p>
    <p><strong>Diritti.</strong> Puoi chiedere informazioni, accesso, rettifica o cancellazione dei dati scrivendo all'indirizzo sopra indicato.</p>
    <p><strong>Affiliazione Amazon.</strong> I pulsanti verso Amazon possono contenere link a pagamento con il tracking ID del Programma di Affiliazione Amazon.</p>
    </div>
    """, unsafe_allow_html=True)
    st.button("← Torna alla vetrina", key="privacy_back", on_click=set_tab, args=("vetrina",))

elif active_tab == "contatti":
    with st.container(border=True):
        st.markdown("<p style='font-size: 0.82rem; font-weight: 700; color: #064e3b; margin-bottom: 6px;'>Inviaci un messaggio, una richiesta di prodotto o un suggerimento (Tutti i campi sono obbligatori):</p>", unsafe_allow_html=True)
        with st.form("form_scheda_contatti", clear_on_submit=True):
            nome_val = st.text_input("Nome e Cognome*", placeholder="Es. Mario Rossi")
            tel_val = st.text_input("Numero di telefono (10 cifre)*", placeholder="Es. 3401234567")
            email_val = st.text_input("Email*", placeholder="Es. mario.rossi@email.com")
            note_val = st.text_area("Note / Suggerimento / Richiesta*", placeholder="Scrivi qui il tuo messaggio (minimo 10 caratteri)...", height=120)
            privacy_ack = st.checkbox("Ho letto l'informativa privacy relativa al modulo di contatto.*")
            st.markdown("<small><a href='?privacy=1' target='_self'>Leggi l'informativa privacy completa</a></small>", unsafe_allow_html=True)
            
            btn_send_form = st.form_submit_button("✉️ Invia Messaggio", use_container_width=True)
            if btn_send_form:
                valido, msg_validazione = valida_campi_contatto(nome_val, tel_val, email_val, note_val)
                if not valido:
                    st.error(msg_validazione)
                elif not privacy_ack:
                    st.error("Per inviare il messaggio devi confermare di aver letto l'informativa privacy.")
                elif not verifica_puo_inviare(email_val.strip()):
                    st.warning("Hai già inviato una richiesta oggi con questa email. È consentito un solo messaggio al giorno per utente. Riprova domani!")
                else:
                    with st.spinner("Invio messaggio in corso..."):
                        ok, msg_err = invia_email_smtp_diretta(nome_val.strip(), tel_val.strip(), email_val.strip(), note_val.strip())
                    if ok:
                        registra_invio_completato(email_val.strip())
                        st.success("Messaggio inviato con successo a davimarz.social@gmail.com! Il nostro team lo prenderà in carico.")
                    else:
                        st.error(f"Errore di invio: {msg_err}")

st.markdown('</div>', unsafe_allow_html=True)

# ----------------- FOOTER / TRASPARENZA AFFILIAZIONE -----------------
st.markdown(
    """
    <div class="site-footer-box">
        <strong>In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei.</strong><br>
        I link verso Amazon presenti nelle schede prodotto possono essere link a pagamento.
        Prezzi e disponibilità fanno fede su Amazon al momento dell'acquisto.<br>
        <a href="?privacy=1" target="_self">Informativa privacy</a>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- PULSANTE TORNA ALL'INIZIO -----------------
st.markdown(
    """
    <div style="display: flex; justify-content: center; align-items: center; width: 100%; margin: 15px 0 20px 0;">
        <a href="#top_page" target="_self" onclick="(function(){
            try {
                const stContainer = window.parent.document.querySelector('[data-testid=\\'stAppViewContainer\\']') || window.parent.document.querySelector('section.main') || document.querySelector('[data-testid=\\'stAppViewContainer\\']');
                if(stContainer) { stContainer.scrollTo({top: 0, behavior: 'smooth'}); }
            } catch(e) {}
            try {
                const el = window.parent.document.getElementById('top_page') || document.getElementById('top_page');
                if(el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }
            } catch(e) {}
            try { window.scrollTo({top: 0, behavior: 'smooth'}); } catch(e) {}
        })" class="btn-back-to-top">
            ⬆️ Torna all'inizio
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
