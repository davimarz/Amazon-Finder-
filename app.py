import streamlit as st
import time
import random
import urllib.parse
from amazon_api import ottieni_offerte_avanzate, ottieni_offerte_pagina_speciale, verifica_prezzo_reale_vetrina, SORT_MAPPINGS, calcola_distribuzione_recensioni
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
        background: transparent !important;
        gap: 8px !important;
    }

    button[data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        background: transparent !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 16px !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom-color: #38bdf8 !important;
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

    .vetrina-box-wrapper {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
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
        min-height: 38px !important;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 1px #38bdf8 !important;
    }

    div[data-baseweb="input"] input {
        color: #f8fafc !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
    }

    div[data-baseweb="select"] > div {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 8px !important;
        min-height: 38px !important;
        color: #f8fafc !important;
    }

    div[data-baseweb="select"] span {
        color: #f8fafc !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
    }

    div[data-testid="stCheckbox"] {
        background: rgba(30, 41, 59, 0.85) !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        width: fit-content !important;
        margin-top: 18px !important;
        min-height: 38px !important;
        display: flex !important;
        align-items: center !important;
        transition: border-color 0.15s ease, background 0.15s ease !important;
    }

    div[data-testid="stCheckbox"]:hover {
        border-
