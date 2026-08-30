def ottieni_vetrina_casuale(partner_tag, item_count=10):
    categorie_popolari = [
        "bestseller informatica",
        "bestseller casa",
        "bestseller sport",
        "bestseller elettronica",
        "bestseller bellezza",
        "bestseller cucina",
        "offerte lampo",
        "libri bestseller"
    ]
    # Sceglie 2 o 3 categorie a caso per ogni caricamento
    cat_scelte = random.sample(categorie_popolari, min(3, len(categorie_popolari)))
    
    tutti_prodotti = []
    asins_visti = set()
    
    for cat in cat_scelte:
        risultati = ottieni_offerte_avanzate(
            keyword=cat,
            sort_type="Recensioni",
            solo_spedizione_gratuita=False,
            item_count=5
        )
        for p in risultati:
            if p["asin"] not in asins_visti:
                asins_visti.add(p["asin"])
                tutti_prodotti.append(p)
                
    # Mescola casualmente per garantire varietà e prende il numero richiesto
    random.shuffle(tutti_prodotti)
    if not tutti_prodotti:
        # Fallback se le ricerche mirate non rispondono
        return ottieni_offerte_avanzate(keyword="top", sort_type="Recensioni", item_count=item_count)
        
    return tutti_prodotti[:item_count]
