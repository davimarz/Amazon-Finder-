from __future__ import annotations

import html
import logging
import re
import smtplib
import urllib.parse
from email.message import EmailMessage

import streamlit as st

import amazon_api


st.set_page_config(
    page_title="Scala dei Turchi | Offerte Amazon",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LOGGER = logging.getLogger("amazon_affiliate_app")

MAX_RESULTS = amazon_api.MAX_RESULTS
SORT_MAPPINGS = amazon_api.SORT_MAPPINGS

st.session_state.setdefault("current_tab", "vetrina")
st.session_state.setdefault("has_searched", False)
st.session_state.setdefault("item_count", 10)
st.session_state.setdefault("current_page", 1)
st.session_state.setdefault("offerte", [])
st.session_state.setdefault("search_notice", "")
st.session_state.setdefault(
    "last_search",
    {"keyword": "", "sort": "Rilevanza", "prime_only": False},
)
st.session_state.setdefault("contact_sent_session", False)

try:
    if str(st.query_params.get("privacy", "")) == "1":
        st.session_state["current_tab"] = "privacy"
except Exception:
    pass


CSS = """
<style>
#MainMenu, footer {visibility:hidden;}
header {background:transparent;}

.stApp {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 55%, #f0fdf4 100%);
    color: #0f172a;
}

.block-container {
    max-width: 900px;
    padding-top: .5rem;
    padding-bottom: 4rem;
}

.brand-box {
    background: rgba(255,255,255,.92);
    border: 1px solid #bae6fd;
    border-radius: 14px;
    padding: 10px 14px;
    margin-bottom: 8px;
    text-align: center;
    box-shadow: 0 4px 18px rgba(2,132,199,.08);
}

.brand-title {
    margin: 0;
    font-size: clamp(1.45rem, 5vw, 2rem);
    font-weight: 900;
    color: #0369a1;
    line-height: 1.1;
}

.brand-subtitle {
    margin-top: 4px;
    font-size: .78rem;
    color: #475569;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,.94);
    border-color: #dbeafe !important;
    border-radius: 13px !important;
    box-shadow: 0 3px 14px rgba(15,23,42,.05);
}

.product-title {
    font-size: .93rem;
    font-weight: 800;
    line-height: 1.3;
    color: #0f172a;
    margin: 0 0 8px 0;
}

.price-row {
    display:flex;
    align-items:baseline;
    flex-wrap:wrap;
    gap:7px;
    margin: 4px 0 7px 0;
}

.price-now {
    font-size: 1.65rem;
    font-weight: 900;
    color: #047857;
}

.price-old {
    font-size: .95rem;
    color: #64748b;
    text-decoration: line-through;
}

.discount {
    background:#ea580c;
    color:white;
    font-weight:900;
    font-size:.78rem;
    border-radius:5px;
    padding:3px 7px;
}

.price-note {
    font-size:.69rem;
    color:#64748b;
    margin-top:2px;
}

.share-row {
    display:flex;
    gap:6px;
    flex-wrap:wrap;
    margin-top:8px;
}

.share-chip {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    min-height:28px;
    padding:4px 9px;
    border-radius:7px;
    background:#f8fafc;
    border:1px solid #cbd5e1;
    color:#334155 !important;
    text-decoration:none !important;
    font-size:.70rem;
    font-weight:700;
}

.site-footer {
    margin-top:18px;
    padding:10px 12px;
    border-radius:10px;
    background:rgba(255,255,255,.90);
    border:1px solid #bae6fd;
    color:#475569;
    text-align:center;
    font-size:.72rem;
    line-height:1.45;
}

.site-footer a {
    color:#0369a1;
    font-weight:800;
}

@media (max-width: 600px) {
    .block-container {padding-left:.55rem; padding-right:.55rem;}
    .price-now {font-size:1.4rem;}
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


def set_tab(tab_name: str) -> None:
    st.session_state["current_tab"] = tab_name
    try:
        st.query_params.clear()
    except Exception:
        pass


def _perform_search(target_count: int) -> None:
    cfg = st.session_state["last_search"]
    target_count = max(10, min(int(target_count), MAX_RESULTS))

    with st.spinner("Ricerca prodotti su Amazon..."):
        results = amazon_api.ottieni_offerte_avanzate(
            keyword=cfg["keyword"],
            sort_type=cfg["sort"],
            solo_spedizione_gratuita=cfg["prime_only"],
            item_count=target_count,
        )

    st.session_state["offerte"] = list(results or [])
    st.session_state["item_count"] = target_count
    st.session_state["has_searched"] = True

    if not results:
        st.session_state["search_notice"] = (
            "Nessun prodotto trovato. Prova una ricerca più generica."
        )
    elif len(results) < target_count:
        st.session_state["search_notice"] = (
            f"Amazon ha restituito {len(results)} prodotti disponibili "
            "per questi criteri."
        )
    else:
        st.session_state["search_notice"] = ""


def _load_more() -> None:
    current_target = int(st.session_state.get("item_count", 10) or 10)
    if current_target >= MAX_RESULTS:
        st.session_state["search_notice"] = (
            f"Limite di {MAX_RESULTS} prodotti raggiunto."
        )
        return

    new_target = min(MAX_RESULTS, current_target + 10)
    previous_count = len(st.session_state.get("offerte", []))
    _perform_search(new_target)

    new_count = len(st.session_state.get("offerte", []))
    if new_count > previous_count:
        st.session_state["current_page"] = max(1, (new_count + 9) // 10)
    elif new_count <= previous_count:
        st.session_state["search_notice"] = (
            "Non risultano altri prodotti disponibili per questa ricerca."
        )


def _format_eur(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _share_links(title: str, link: str, price: float | None) -> str:
    message = title.strip()
    if price is not None and price > 0:
        message += f"\nPrezzo: €{_format_eur(price)}"
    message += f"\n{link}"

    wa = f"https://wa.me/?text={urllib.parse.quote(message)}"
    tg = (
        "https://t.me/share/url?"
        f"url={urllib.parse.quote(link)}&text={urllib.parse.quote(message)}"
    )
    fb = (
        "https://www.facebook.com/sharer/sharer.php?"
        f"u={urllib.parse.quote(link)}"
    )
    mail = (
        "mailto:?subject="
        f"{urllib.parse.quote('Offerta Amazon')}"
        "&body="
        f"{urllib.parse.quote(message)}"
    )

    return (
        "<div class='share-row'>"
        f"<a class='share-chip' href='{html.escape(wa, quote=True)}' "
        "target='_blank' rel='noopener noreferrer'>WhatsApp</a>"
        f"<a class='share-chip' href='{html.escape(tg, quote=True)}' "
        "target='_blank' rel='noopener noreferrer'>Telegram</a>"
        f"<a class='share-chip' href='{html.escape(fb, quote=True)}' "
        "target='_blank' rel='noopener noreferrer'>Facebook</a>"
        f"<a class='share-chip' href='{html.escape(mail, quote=True)}'>Email</a>"
        "</div>"
    )


def render_product_card(product: dict) -> None:
    title = str(product.get("titolo") or "Prodotto Amazon")
    image_url = str(product.get("immagine_url") or "")
    link = str(product.get("link_affiliato") or "")
    verified = product.get("prezzo_verificato") is True

    final_price_raw = product.get("prezzo_finale")
    old_price_raw = product.get("prezzo_iniziale")

    try:
        final_price = (
            float(final_price_raw)
            if final_price_raw is not None
            else None
        )
    except (TypeError, ValueError):
        final_price = None

    try:
        old_price = (
            float(old_price_raw)
            if old_price_raw is not None
            else None
        )
    except (TypeError, ValueError):
        old_price = None

    with st.container(border=True):
        image_col, info_col = st.columns([1.05, 2.95], vertical_alignment="center")

        with image_col:
            if image_url:
                st.image(image_url, use_container_width=True)
            else:
                st.markdown(
                    "<div style='height:130px;display:flex;align-items:center;"
                    "justify-content:center;color:#94a3b8;'>Immagine non disponibile</div>",
                    unsafe_allow_html=True,
                )

        with info_col:
            st.markdown(
                f"<div class='product-title'>{html.escape(title)}</div>",
                unsafe_allow_html=True,
            )

            if verified and final_price is not None and final_price > 0:
                discount = html.escape(str(product.get("sconto") or ""))
                discount_html = (
                    f"<span class='discount'>{discount}</span>"
                    if discount
                    else ""
                )

                old_html = ""
                if (
                    old_price is not None
                    and old_price > final_price
                ):
                    old_html = (
                        f"<span class='price-old'>€{_format_eur(old_price)}</span>"
                    )

                st.markdown(
                    "<div class='price-row'>"
                    f"{discount_html}"
                    f"<span class='price-now'>€{_format_eur(final_price)}</span>"
                    f"{old_html}"
                    "</div>",
                    unsafe_allow_html=True,
                )

                basis_label = str(product.get("saving_basis_label") or "").strip()
                note = "Prezzo Buy Box verificato tramite Amazon Creators API."
                if basis_label and old_price is not None and old_price > final_price:
                    note += f" Prezzo di riferimento: {html.escape(basis_label)}."
                st.markdown(
                    f"<div class='price-note'>{note}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Prezzo non disponibile via API. Verificalo su Amazon.")

            if product.get("is_prime_exclusive") is True:
                st.caption("Offerta Prime esclusiva indicata da Amazon.")

            if link:
                st.link_button(
                    "🛒 Vedi su Amazon",
                    link,
                    type="primary",
                    use_container_width=True,
                )
                st.caption("Link affiliato a pagamento.")
                st.markdown(
                    _share_links(title, link, final_price if verified else None),
                    unsafe_allow_html=True,
                )


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_contact(
    name: str,
    phone: str,
    email: str,
    message: str,
) -> tuple[bool, str]:
    name = name.strip()
    phone_digits = re.sub(r"\D", "", phone)
    email = email.strip()
    message = message.strip()

    if not name or not phone_digits or not email or not message:
        return False, "Compila tutti i campi obbligatori."

    if len(name) < 3:
        return False, "Inserisci un nome valido."

    if not 8 <= len(phone_digits) <= 15:
        return False, "Inserisci un numero di telefono valido."

    if not EMAIL_REGEX.fullmatch(email):
        return False, "Inserisci un indirizzo email valido."

    if len(message) < 10:
        return False, "Il messaggio deve contenere almeno 10 caratteri."

    return True, ""


def send_contact_email(
    name: str,
    phone: str,
    user_email: str,
    message: str,
) -> tuple[bool, str]:
    email_cfg = st.secrets.get("email", {})
    sender = str(email_cfg.get("sender", "")).strip()
    app_password = str(email_cfg.get("app_password", "")).replace(" ", "")
    recipient = str(email_cfg.get("recipient") or sender).strip()

    if not sender or not app_password or not recipient:
        LOGGER.error("Configurazione email incompleta nei Secrets.")
        return False, "Servizio email non configurato."

    mail = EmailMessage()
    mail["From"] = f"Scala dei Turchi <{sender}>"
    mail["To"] = recipient
    mail["Reply-To"] = user_email
    mail["Subject"] = f"[Scala dei Turchi] Messaggio da {name}"
    mail.set_content(
        "Nuovo messaggio dal sito:\n\n"
        f"Nome: {name}\n"
        f"Telefono: {phone}\n"
        f"Email: {user_email}\n\n"
        f"Messaggio:\n{message}\n"
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as server:
            server.login(sender, app_password)
            server.send_message(mail)
        return True, ""
    except Exception as exc:
        LOGGER.error("Invio email fallito: %s", type(exc).__name__)
        return False, "Invio non riuscito. Riprova più tardi."


st.markdown(
    """
    <div class="brand-box">
        <h1 class="brand-title">Scala dei Turchi</h1>
        <div class="brand-subtitle">Offerte Amazon selezionate tramite Creators API</div>
    </div>
    """,
    unsafe_allow_html=True,
)

active_tab = st.session_state.get("current_tab", "vetrina")
nav1, nav2, nav3 = st.columns(3)

with nav1:
    st.button(
        "🔥 Vetrina",
        type="primary" if active_tab == "vetrina" else "secondary",
        on_click=set_tab,
        args=("vetrina",),
        use_container_width=True,
    )
with nav2:
    st.button(
        "🔍 Cerca",
        type="primary" if active_tab == "cerca" else "secondary",
        on_click=set_tab,
        args=("cerca",),
        use_container_width=True,
    )
with nav3:
    st.button(
        "✉️ Contatti",
        type="primary" if active_tab == "contatti" else "secondary",
        on_click=set_tab,
        args=("contatti",),
        use_container_width=True,
    )

partner_tag = amazon_api.get_partner_tag()

if not partner_tag:
    st.error(
        "Configurazione Amazon incompleta: aggiungi partner_tag e credenziali "
        "Creators API nei Secrets di Streamlit."
    )

active_tab = st.session_state.get("current_tab", "vetrina")

if active_tab == "vetrina":
    st.subheader("Offerte in vetrina")

    if partner_tag:
        with st.spinner("Aggiornamento vetrina..."):
            showcase = amazon_api.ottieni_vetrina_casuale(item_count=10)

        if showcase:
            for product in showcase:
                render_product_card(product)
        else:
            st.info("Nessun prodotto disponibile in vetrina al momento.")

elif active_tab == "cerca":
    st.subheader("Cerca su Amazon")

    previous = st.session_state.get("last_search", {})

    with st.form("search_form", border=False):
        keyword = st.text_input(
            "Prodotto",
            value=str(previous.get("keyword") or ""),
            placeholder="Es. cuffie bluetooth, robot aspirapolvere, smartwatch...",
        )

        sort_choice = st.radio(
            "Ordina per",
            list(SORT_MAPPINGS.keys()),
            index=max(
                0,
                list(SORT_MAPPINGS.keys()).index(
                    previous.get("sort", "Rilevanza")
                )
                if previous.get("sort", "Rilevanza") in SORT_MAPPINGS
                else 0,
            ),
            horizontal=True,
        )

        prime_only = st.checkbox(
            "Mostra solo risultati compatibili con il filtro Prime di Amazon",
            value=bool(previous.get("prime_only", False)),
        )

        submitted = st.form_submit_button(
            "🔍 Cerca",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        st.session_state["last_search"] = {
            "keyword": keyword.strip(),
            "sort": sort_choice,
            "prime_only": bool(prime_only),
        }
        st.session_state["current_page"] = 1
        st.session_state["item_count"] = 10
        _perform_search(10)

    if st.session_state.get("search_notice"):
        st.info(st.session_state["search_notice"])

    results = st.session_state.get("offerte", [])

    if results:
        total = len(results)
        pages = max(1, (total + 9) // 10)
        current_page = min(
            max(1, int(st.session_state.get("current_page", 1))),
            pages,
        )
        st.session_state["current_page"] = current_page

        if pages > 1:
            page_cols = st.columns(pages)
            for page_number, col in enumerate(page_cols, start=1):
                with col:
                    if st.button(
                        f"{page_number}",
                        type="primary" if page_number == current_page else "secondary",
                        key=f"page_{page_number}",
                        use_container_width=True,
                    ):
                        st.session_state["current_page"] = page_number
                        st.rerun()

        start = (current_page - 1) * 10
        end = min(start + 10, total)
        st.caption(f"Prodotti {start + 1}-{end} di {total}")

        for product in results[start:end]:
            render_product_card(product)

        st.button(
            "➕ Altri 10 prodotti",
            on_click=_load_more,
            use_container_width=True,
            disabled=int(st.session_state.get("item_count", 10)) >= MAX_RESULTS,
        )

    elif st.session_state.get("has_searched"):
        st.warning("Nessun prodotto trovato.")

elif active_tab == "privacy":
    st.subheader("Informativa privacy")
    st.markdown(
        """
        I dati inseriti nel modulo contatti vengono utilizzati esclusivamente
        per rispondere alla richiesta inviata. Il sito partecipa al Programma
        di Affiliazione Amazon e contiene link affiliati.

        Le credenziali tecniche del sito sono conservate nei Secrets di
        Streamlit e non devono essere pubblicate nel repository GitHub.
        """
    )
    st.button(
        "← Torna alla vetrina",
        on_click=set_tab,
        args=("vetrina",),
    )

elif active_tab == "contatti":
    st.subheader("Contatti")

    if st.session_state.get("contact_sent_session"):
        st.success("Messaggio già inviato in questa sessione.")

    with st.form("contact_form", clear_on_submit=True):
        name = st.text_input("Nome e cognome*")
        phone = st.text_input("Telefono*")
        user_email = st.text_input("Email*")
        message = st.text_area("Messaggio*", height=120)
        privacy_ack = st.checkbox("Ho letto l'informativa privacy.*")
        st.markdown(
            "<small><a href='?privacy=1' target='_self'>Leggi informativa privacy</a></small>",
            unsafe_allow_html=True,
        )

        send = st.form_submit_button(
            "✉️ Invia messaggio",
            use_container_width=True,
            disabled=bool(st.session_state.get("contact_sent_session")),
        )

    if send:
        valid, validation_message = validate_contact(
            name,
            phone,
            user_email,
            message,
        )

        if not valid:
            st.error(validation_message)
        elif not privacy_ack:
            st.error("Conferma di aver letto l'informativa privacy.")
        else:
            with st.spinner("Invio in corso..."):
                ok, error_message = send_contact_email(
                    name.strip(),
                    phone.strip(),
                    user_email.strip(),
                    message.strip(),
                )

            if ok:
                st.session_state["contact_sent_session"] = True
                st.success("Messaggio inviato correttamente.")
            else:
                st.error(error_message)

st.markdown(
    """
    <div class="site-footer">
        <strong>In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei.</strong><br>
        I link verso Amazon sono link affiliati a pagamento.
        Prezzi e disponibilità possono variare su Amazon.<br>
        <a href="?privacy=1" target="_self">Informativa privacy</a>
    </div>
    """,
    unsafe_allow_html=True,
)
