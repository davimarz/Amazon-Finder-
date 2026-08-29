def analizza_spedizione_html(item_tag):
    """
    Riconosce con precisione se un prodotto è Prime, ha consegna gratuita o a pagamento.
    Default rigoroso: se non ci sono prove certe di Prime/Gratuito, non è gratuito.
    """
    html_str = str(item_tag).lower()
    testo_completo = item_tag.get_text(" ", strip=True).lower()

    # 1. Riconoscimento badge Prime reale (non semplice menzione nel testo)
    is_prime = bool(
        "a-icon-prime" in html_str or
        "s-prime" in html_str or
        item_tag.find("i", class_=re.compile(r"a-icon-prime|s-prime", re.I)) or
        item_tag.find("span", {"aria-label": re.compile(r"^prime$", re.I)})
    )

    # 2. Riconoscimento costi di spedizione espliciti (es: "Consegna a 7,40 €", "+ 7,40 € di spedizione")
    costo_sped = 0.0
    match_costo = re.search(
        r'(?:consegna\s+a\s*€?\s*(\d+[.,]\d{2}))|'
        r'(?:consegna\s+a\s*(\d+[.,]\d{2})\s*€)|'
        r'(?:€\s*(\d+[.,]\d{2})\s*(?:di\s*)?spedizione)|'
        r'(?:(\d+[.,]\d{2})\s*€\s*(?:di\s*)?spedizione)|'
        r'(?:\+\s*€?\s*(\d+[.,]\d{2})\s*(?:di\s*)?spedizione)|'
        r'(?:spedizione\s*[:a]\s*€?\s*(\d+[.,]\d{2}))',
        testo_completo,
        re.I
    )

    if match_costo:
        val_str = next(v for v in match_costo.groups() if v is not None)
        try:
            val_num = float(val_str.replace(",", "."))
            if val_num > 0:
                costo_sped = val_num
        except ValueError:
            pass

    # Se è stato trovato un costo reale > 0 e l'articolo non è Prime, è a pagamento
    if costo_sped > 0 and not is_prime:
        return costo_sped, f"Consegna a €{costo_sped:.2f}", False, False

    # 3. Diciture esplicite di consegna senza costi
    frasi_gratuite = [
        "consegna senza costi aggiuntivi",
        "consegna gratuita",
        "spedizione gratuita",
        "senza costi aggiuntivi",
        "consegna gratis",
        "spedizione gratis"
    ]
    ha_dicitura_gratis = any(f in testo_completo for f in frasi_gratuite)

    if is_prime:
        return 0.0, "Prime (Spedizione gratuita)", True, True

    if ha_dicitura_gratis:
        return 0.0, "Spedizione gratuita", False, True

    # Default restrittivo: se non certificato gratuito, viene escluso dal filtro
    return costo_sped, "Spedizione standard", False, False
