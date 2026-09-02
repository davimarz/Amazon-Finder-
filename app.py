import streamlit as st
import smtplib
import sqlite3
import re
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse
from amazon_api import ottieni_offerte_avanzate, ottieni_vetrina_casuale, SORT_MAPPINGS, calcola_distribuzione_recensioni
from preferiti_db import ottieni_tutti_preferiti, aggiungi_preferito, rimuovi_preferito

st.set_page_config(
    page_title="Scaladeiturchi | Offerte Amazon AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

    div[data-baseweb="tab-list"] {
        background: rgba(255, 255, 255, 0.85) !important;
        padding: 2px 4px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(2, 132, 199, 0.25) !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
        display: flex !important;
        width: 100% !important;
    }

    button[data-baseweb="tab"] {
        flex: 1 1 0% !important;
        color: #0369a1 !important;
        font-weight: 800 !important;
        font-size: 0.74rem !important;
        background: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid rgba(2, 132, 199, 0.2) !important;
        border-radius: 6px !important;
        padding: 4px 5px !important;
        min-height: 28px !important;
        height: 28px !important;
        text-align: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
        border-color: #0284c7 !important;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35) !important;
    }

    div[data-baseweb="tab-highlight"] { display: none !important; }

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

    div[data-baseweb="tab-panel"] {
        background: rgba(255, 255, 255, 0.60) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 2px solid rgba(255, 255, 255, 0.85) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        margin-top: 2px !important;
        box-shadow: 0 6px 20px rgba(2, 132, 199, 0.12) !important;
    }

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
        font-size: 0.78rem !important;
        font-weight: 800 !important;
        line-height: 1.15 !important;
        color: #064e3b !important;
        margin: 0 !important;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

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

if "preferiti_asin" not in st.session_state:
    salvati = ottieni_tutti_preferiti()
    st.session_state.preferiti_asin = {p["asin"]: p for p in salvati}

if "offerte" not in st.session_state:
    st.session_state.offerte = []

if "offerte_vetrina" not in st.session_state:
    st.session_state.offerte_vetrina = []

if "has_searched" not in st.session_state:
    st.session_state.has_searched = False

if "item_count" not in st.session_state:
    st.session_state.item_count = 10

if "current_page" not in st.session_state:
    st.session_state.current_page = 1

if "scroll_to_top" not in st.session_state:
    st.session_state.scroll_to_top = False

def esegui_ricerca(increment=False):
    st.session_state.has_searched = True
    vecchi_risultati = st.session_state.get("offerte", [])
    
    if increment:
        target_count = st.session_state.get("item_count", 10) + 10
    else:
        target_count = 10
        st.session_state.item_count = 10
        st.session_state.current_page = 1

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
        item_count=target_count
    )

    if increment:
        # Se la ricerca ha trovato nuovi prodotti in più rispetto a prima
        if risultati and len(risultati) > len(vecchi_risultati):
            st.session_state.offerte = risultati
            st.session_state.item_count = len(risultati)
            num_pag_totali = max(1, (len(st.session_state.offerte) + 9) // 10)
            st.session_state.current_page = num_pag_totali
        else:
            # Non azzerare la lista: conserva i prodotti già estratti e informa l'utente
            st.session_state.offerte = vecchi_risultati
            st.warning("⚠️ Raggiunto il limite massimo di richieste o di prodotti disponibili per questa ricerca. I prodotti precedenti rimangono visibili.")
    else:
        st.session_state.offerte = risultati if risultati else []
        st.session_state.item_count = len(st.session_state.offerte) if st.session_state.offerte else 10

if not st.session_state.offerte_vetrina:
    partner_tag = st.secrets.get("amazon_api", {}).get("partner_tag", "eiapromo-21")
    st.session_state.offerte_vetrina = ottieni_vetrina_casuale(partner_tag, item_count=10)

st.markdown("""
<div id="top_page" style="position: absolute; top: 0; left: 0; height: 1px; width: 1px;"></div>
<div class="hero-container">
    <div class="hero-title-main">Scala dei Turchi</div>
    <div class="hero-subtitle-box">
        <span class="hero-subtitle-text">Offerte Amazon</span>
        <span class="ai-badge">AI</span>
    </div>
    <div class="hero-author-tag">Realizzato da <strong>Davide Marziano</strong></div>
</div>
""", unsafe_allow_html=True)

if st.session_state.get("scroll_to_top", False):
    st.session_state.scroll_to_top = False
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
        }, 100);
    </script>
    """, unsafe_allow_html=True)

tab_vetrina, tab_cerca, tab_preferiti, tab_contatti = st.tabs([
    "🔥 Offerte Vetrina",
    "🔍 Cerca Prodotto", 
    f"⭐ Preferiti ({len(st.session_state.preferiti_asin)})",
    "✉️ Contattaci per una richiesta o suggerimento"
])

IMG_FALLBACK_SVG = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 24 24' fill='none' stroke='%23059669' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><rect x='2' y='3' width='20' height='14' rx='2' ry='2'></rect><line x1='8' y1='21' x2='16' y2='21'></line><line x1='12' y1='17' x2='12' y2='21'></line></svg>"

def render_product_card(p, tab_key="main"):
    with st.container(border=True):
        col_left, col_center, col_fb = st.columns([1.1, 1.4, 1.2])
        is_fav = p["asin"] in st.session_state.preferiti_asin
        star_icon = "⭐" if is_fav else "☆"

        with col_left:
            img_url = p.get('immagine_url') or IMG_FALLBACK_SVG
            st.markdown(
                f"<div class='product-img-wrapper-full'><img src='{img_url}' referrerpolicy='no-referrer' loading='lazy' onerror=\"this.onerror=null;this.src='{IMG_FALLBACK_SVG}';\" alt='Prodotto'></div>",
                unsafe_allow_html=True
            )

        with col_center:
            titolo = p.get('titolo', 'Prodotto Amazon')
            link = p.get('link_affiliato', '')

            st.markdown('<div class="title-star-row">', unsafe_allow_html=True)
            c_titolo, c_star = st.columns([0.92, 0.08])
            with c_titolo:
                st.markdown(f"<div class='deal-title'>{titolo}</div>", unsafe_allow_html=True)
            with c_star:
                if st.button(star_icon, key=f"fav_{tab_key}_{p['asin']}", help="Aggiungi/Rimuovi dai Preferiti"):
                    if is_fav:
                        rimuovi_preferito(p["asin"])
                        st.session_state.preferiti_asin.pop(p["asin"], None)
                    else:
                        aggiungi_preferito(p)
                        st.session_state.preferiti_asin[p["asin"]] = p
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
            badge_html = f"<span class='deal-badge'>{p['sconto']}</span>" if p.get('sconto') else ""
            old_price_html = f"<span class='deal-price-old'>€{p['prezzo_iniziale']:.2f}</span>" if p.get('prezzo_iniziale', 0.0) > p.get('prezzo_finale', 0.0) else ""
            prices_sub_html = f"<div class='price-subgroup-left'>{badge_html}<span class='deal-price-final'>€{p['prezzo_finale']:.2f}</span>{old_price_html}</div>"

            costo_s = float(p.get("costo_spedizione", 0.0))
            if p.get("is_prime") or (p.get("is_sped_gratis") and costo_s == 0.0):
                ship_html = "<span class='shipping-badge-prime'>prime</span>"
            elif costo_s > 0.0:
                ship_html = f"<span class='shipping-badge-paid'>📦 +€{costo_s:.2f}</span>"
            else:
                ship_html = "<span class='shipping-badge-free'>🚚 Gratis</span>"

            st.markdown(f"<div class='price-delivery-split-row'>{prices_sub_html}{ship_html}</div>", unsafe_allow_html=True)
            st.markdown(f"<a href='{link}' target='_blank' class='buy-btn-action'>🛒 Acquista</a>", unsafe_allow_html=True)
            
            safe_title = titolo.replace("'", " ").replace('"', ' ').replace("\n", " ").strip()
            share_msg = f"🔥 Offerta: {safe_title}\n💰 Prezzo: €{p['prezzo_finale']:.2f}\n👉 {link}"
            
            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_msg)}"
            fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(link)}"
            ig_url = "https://www.instagram.com/"
            tg_url = f"https://t.me/share/url?url={urllib.parse.quote(link)}&text={urllib.parse.quote(share_msg)}"
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Offerta&body={urllib.parse.quote(share_msg)}"
            copy_action = f"navigator.clipboard.writeText('{link}').then(function(){{alert('Link copiato negli appunti!');}});"

            st.markdown(
                f"""
                <div class='social-share-row-mobile'>
                    <a href='{wa_url}' target='_blank' rel='noopener noreferrer' class='share-icon-btn btn-wa' title='WhatsApp'>{SVG_WA}</a>
                    <a href='{fb_url}' target='_blank' rel='noopener noreferrer' class='share-icon-btn btn-fb' title='Facebook'>{SVG_FB}</a>
                    <a href='{ig_url}' target='_blank' rel='noopener noreferrer' class='share-icon-btn btn-ig' title='Instagram'>{SVG_IG}</a>
                    <a href='{tg_url}' target='_blank' rel='noopener noreferrer' class='share-icon-btn btn-tg' title='Telegram'>{SVG_TG}</a>
                    <a href='{gmail_url}' target='_blank' rel='noopener noreferrer' class='share-icon-btn btn-gmail' title='Gmail'>{SVG_GMAIL}</a>
                    <button type='button' onclick=\"{copy_action}\" class='share-icon-btn btn-copy' title='Copia Link'>{SVG_COPY}</button>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_fb:
            voto = p.get("voto_medio", 4.5)
            num_val = p.get("num_recensioni", 0)
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

with tab_vetrina:
    st.markdown("""
        <p style='font-size: 0.85rem; font-weight: 800; color: #064e3b; margin: 4px 0 2px 2px;'>🔥 Offerte Vetrina Amazon Da Non Perdere:</p>
        <p style='font-size: 0.74rem; font-weight: 600; color: #334155; margin: 0 0 10px 2px; font-style: italic;'>*I prodotti che vengono visualizzati in questa pagina hanno un prezzo che poi andrà a variare in base alle misure, colori, taglie.*</p>
    """, unsafe_allow_html=True)

    if st.session_state.offerte_vetrina:
        for idx in range(0, len(st.session_state.offerte_vetrina), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(st.session_state.offerte_vetrina[idx], tab_key=f"vetrina_{idx}")
            if idx + 1 < len(st.session_state.offerte_vetrina):
                with col_r:
                    render_product_card(st.session_state.offerte_vetrina[idx + 1], tab_key=f"vetrina_{idx + 1}")
    else:
        st.info("Nessun prodotto disponibile in vetrina al momento.")

with tab_cerca:
    with st.container(border=True):
        search_kw = st.text_input(
            "Cerca:",
            placeholder="Cosa cerchi? (es. cuffie, smartphone, macchina caffe)...",
            key="cerca_keyword_input",
            label_visibility="collapsed"
        )
        btn_cerca_submit = st.button("🔍 Cerca", key="btn_cerca_submit", use_container_width=True)
        btn_altri_10 = st.button("➕ Altri 10", key="btn_altri_10_top", use_container_width=True)

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

    if btn_cerca_submit:
        with st.spinner("Ricerca prodotti su Amazon in corso..."):
            esegui_ricerca(increment=False)
        st.rerun()

    if btn_altri_10:
        with st.spinner("Caricamento altri prodotti in corso..."):
            esegui_ricerca(increment=True)
        st.session_state.scroll_to_top = True
        st.rerun()

    if st.session_state.offerte:
        tot_offerte = len(st.session_state.offerte)
        tot_pagine = max(1, (tot_offerte + 9) // 10)

        if tot_pagine > 1:
            st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
            cols_pag = st.columns([1] * tot_pagine + [max(1, 10 - tot_pagine)])
            for p_num in range(1, tot_pagine + 1):
                with cols_pag[p_num - 1]:
                    is_active = (st.session_state.current_page == p_num)
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(f"Pagina {p_num}", key=f"btn_page_{p_num}", type=btn_type, use_container_width=True):
                        st.session_state.current_page = p_num
                        st.session_state.scroll_to_top = True
                        st.rerun()

        start_idx = (st.session_state.current_page - 1) * 10
        end_idx = min(start_idx + 10, tot_offerte)
        offerte_pagina = st.session_state.offerte[start_idx:end_idx]

        st.markdown(f"<p style='font-size: 0.72rem; font-weight: 700; color: #0369a1; margin: 4px 0 2px 2px;'>Visualizzati {start_idx + 1}-{end_idx} di {tot_offerte} prodotti (Pagina {st.session_state.current_page} di {tot_pagine}):</p>", unsafe_allow_html=True)

        for idx in range(0, len(offerte_pagina), 2):
            col_l, col_r = st.columns(2)
            with col_l:
                render_product_card(offerte_pagina[idx], tab_key=f"cerca_p{st.session_state.current_page}_{idx}")
            if idx + 1 < len(offerte_pagina):
                with col_r:
                    render_product_card(offerte_pagina[idx + 1], tab_key=f"cerca_p{st.session_state.current_page}_{idx + 1}")

        st.markdown("<div style='margin-top: 10px; margin-bottom: 5px;'></div>", unsafe_allow_html=True)
        btn_altri_10_bottom = st.button("➕ Altri 10", key="btn_altri_10_bottom", use_container_width=True)
        if btn_altri_10_bottom:
            with st.spinner("Caricamento altri prodotti in corso..."):
                esegui_ricerca(increment=True)
            st.session_state.scroll_to_top = True
            st.rerun()

    elif st.session_state.has_searched:
        st.warning("Nessun prodotto trovato con i filtri selezionati. Prova a inserire un termine diverso o a impostare lo Sconto su 'Tutti'.")

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

with tab_contatti:
    with st.container(border=True):
        st.markdown("<p style='font-size: 0.82rem; font-weight: 700; color: #064e3b; margin-bottom: 6px;'>Inviaci un messaggio, una richiesta di prodotto o un suggerimento (Tutti i campi sono obbligatori):</p>", unsafe_allow_html=True)
        with st.form("form_scheda_contatti", clear_on_submit=True):
            nome_val = st.text_input("Nome e Cognome*", placeholder="Es. Mario Rossi")
            tel_val = st.text_input("Numero di telefono (10 cifre)*", placeholder="Es. 3401234567")
            email_val = st.text_input("Email*", placeholder="Es. mario.rossi@email.com")
            note_val = st.text_area("Note / Suggerimento / Richiesta*", placeholder="Scrivi qui il tuo messaggio (minimo 10 caratteri)...", height=120)
            
            btn_send_form = st.form_submit_button("✉️ Invia Messaggio", use_container_width=True)
            if btn_send_form:
                valido, msg_validazione = valida_campi_contatto(nome_val, tel_val, email_val, note_val)
                if not valido:
                    st.error(msg_validazione)
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
