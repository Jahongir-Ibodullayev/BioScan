"""O'zbek xalq nomlari → ilmiy (lotin) nomlar lug'ati.

Foydalanuvchi "uzum" yozsa — iNat/GBIF Vitis vinifera ni qidiradi.
Bu lug'at eng keng tarqalgan 200+ UZ tur nomlarini qamrab oladi.
Topilmasa AI (Groq) fallback ishga tushadi.
"""
from __future__ import annotations

# slug → (ilmiy nom, kategoriya, ingliz nomi)
UZ_TO_LATIN: dict[str, tuple[str, str, str]] = {
    # ===== MEVALAR =====
    "uzum":         ("Vitis vinifera",      "plant",  "Grape"),
    "olma":         ("Malus domestica",     "plant",  "Apple"),
    "nok":          ("Pyrus communis",      "plant",  "Pear"),
    "anjir":        ("Ficus carica",        "plant",  "Fig"),
    "anor":         ("Punica granatum",     "plant",  "Pomegranate"),
    "behi":         ("Cydonia oblonga",     "plant",  "Quince"),
    "o'rik":        ("Prunus armeniaca",    "plant",  "Apricot"),
    "urik":         ("Prunus armeniaca",    "plant",  "Apricot"),
    "gilos":        ("Prunus avium",        "plant",  "Cherry"),
    "olxo'ri":      ("Prunus domestica",    "plant",  "Plum"),
    "olxori":       ("Prunus domestica",    "plant",  "Plum"),
    "shaftoli":     ("Prunus persica",      "plant",  "Peach"),
    "tut":          ("Morus alba",          "plant",  "Mulberry"),
    "yong'oq":      ("Juglans regia",       "plant",  "Walnut"),
    "yongoq":       ("Juglans regia",       "plant",  "Walnut"),
    "bodom":        ("Prunus dulcis",       "plant",  "Almond"),
    "pista":        ("Pistacia vera",       "plant",  "Pistachio"),
    "tarvuz":       ("Citrullus lanatus",   "plant",  "Watermelon"),
    "qovun":        ("Cucumis melo",        "plant",  "Melon"),
    "qulupnay":     ("Fragaria × ananassa", "plant",  "Strawberry"),
    "aloe":         ("Aloe vera",            "plant",  "Aloe"),
    "alo":          ("Aloe vera",            "plant",  "Aloe"),
    "malina":       ("Rubus idaeus",        "plant",  "Raspberry"),
    "gilos":        ("Prunus avium",        "plant",  "Cherry"),
    "na'matak":     ("Rosa canina",         "plant",  "Rosehip"),
    "namatak":      ("Rosa canina",         "plant",  "Rosehip"),
    "chakanda":     ("Hippophae rhamnoides","plant",  "Sea buckthorn"),
    "do'lana":      ("Crataegus",           "plant",  "Hawthorn"),
    "dolana":       ("Crataegus",           "plant",  "Hawthorn"),
    "zirk":         ("Berberis vulgaris",   "plant",  "Barberry"),

    # ===== SABZAVOTLAR =====
    "qovoq":        ("Cucurbita pepo",      "plant",  "Pumpkin"),
    "bodring":      ("Cucumis sativus",     "plant",  "Cucumber"),
    "pomidor":      ("Solanum lycopersicum","plant",  "Tomato"),
    "kartoshka":    ("Solanum tuberosum",   "plant",  "Potato"),
    "piyoz":        ("Allium cepa",         "plant",  "Onion"),
    "sarimsoq":     ("Allium sativum",      "plant",  "Garlic"),
    "sabzi":        ("Daucus carota",       "plant",  "Carrot"),
    "lavlagi":      ("Beta vulgaris",       "plant",  "Beet"),
    "qalampir":     ("Capsicum annuum",     "plant",  "Pepper"),
    "baqlajon":     ("Solanum melongena",   "plant",  "Eggplant"),
    "karam":        ("Brassica oleracea",   "plant",  "Cabbage"),
    "turp":         ("Raphanus sativus",    "plant",  "Radish"),
    "rediska":      ("Raphanus sativus",    "plant",  "Radish"),
    "ismaloq":      ("Spinacia oleracea",   "plant",  "Spinach"),
    "salat":        ("Lactuca sativa",      "plant",  "Lettuce"),
    "jag'-jag'":    ("Portulaca oleracea",  "plant",  "Purslane"),

    # ===== G'ALLA VA DUKKAKLILAR =====
    "bug'doy":      ("Triticum aestivum",   "plant",  "Wheat"),
    "bugdoy":       ("Triticum aestivum",   "plant",  "Wheat"),
    "guruch":       ("Oryza sativa",        "plant",  "Rice"),
    "sholi":        ("Oryza sativa",        "plant",  "Rice"),
    "makkajo'xori": ("Zea mays",            "plant",  "Corn"),
    "makkajuxori":  ("Zea mays",            "plant",  "Corn"),
    "arpa":         ("Hordeum vulgare",     "plant",  "Barley"),
    "suli":         ("Avena sativa",        "plant",  "Oats"),
    "no'xat":       ("Pisum sativum",       "plant",  "Pea"),
    "nuxat":        ("Pisum sativum",       "plant",  "Pea"),
    "loviya":       ("Phaseolus vulgaris",  "plant",  "Bean"),
    "mosh":         ("Vigna radiata",       "plant",  "Mung bean"),
    "kunjut":       ("Sesamum indicum",     "plant",  "Sesame"),
    "kungaboqar":   ("Helianthus annuus",   "plant",  "Sunflower"),
    "paxta":        ("Gossypium hirsutum",  "plant",  "Cotton"),
    "tamaki":       ("Nicotiana tabacum",   "plant",  "Tobacco"),

    # ===== DORIVOR GIYOHLAR =====
    "yantoq":       ("Alhagi pseudalhagi",  "plant",  "Camel thorn"),
    "isiriq":       ("Peganum harmala",     "plant",  "Syrian rue"),
    "hazorasfand":  ("Peganum harmala",     "plant",  "Syrian rue"),
    "shuvoq":       ("Artemisia",           "plant",  "Wormwood"),
    "yalpiz":       ("Mentha",              "plant",  "Mint"),
    "jambil":       ("Ziziphora",           "plant",  "Wild thyme"),
    "mavrak":       ("Salvia officinalis",  "plant",  "Sage"),
    "rayxon":       ("Ocimum basilicum",    "plant",  "Basil"),
    "kashnich":     ("Coriandrum sativum",  "plant",  "Coriander"),
    "kovrak":       ("Ferula",              "plant",  "Ferula"),
    "ukrop":        ("Anethum graveolens",  "plant",  "Dill"),
    "sedana":       ("Nigella sativa",      "plant",  "Black cumin"),
    "zira":         ("Cuminum cyminum",     "plant",  "Cumin"),
    "za'faron":     ("Crocus sativus",      "plant",  "Saffron"),
    "zafaron":      ("Crocus sativus",      "plant",  "Saffron"),
    "qoqi":         ("Taraxacum officinale","plant",  "Dandelion"),
    "qoqio't":      ("Taraxacum officinale","plant",  "Dandelion"),
    "qoqiot":       ("Taraxacum officinale","plant",  "Dandelion"),
    "qirqbo'g'im":  ("Equisetum arvense",   "plant",  "Horsetail"),
    "tuyatovon":    ("Tussilago farfara",   "plant",  "Coltsfoot"),

    # ===== GULLAR =====
    "atirgul":      ("Rosa × damascena",    "plant",  "Damask rose"),
    "lola":         ("Tulipa",              "plant",  "Tulip"),
    "chinnigul":    ("Dianthus",            "plant",  "Carnation"),
    "piyoligul":    ("Primula",             "plant",  "Primrose"),
    "chuchmoma":    ("Tulipa greigii",      "plant",  "Greig's tulip"),
    "boychechak":   ("Galanthus nivalis",   "plant",  "Snowdrop"),
    "lolaqizg'aldoq": ("Papaver rhoeas",    "plant",  "Poppy"),
    "zanjabil":     ("Zingiber officinale", "plant",  "Ginger"),

    # ===== DARAXTLAR =====
    "archa":        ("Juniperus",           "plant",  "Juniper"),
    "terak":        ("Populus",             "plant",  "Poplar"),
    "tol":          ("Salix",               "plant",  "Willow"),
    "chinor":       ("Platanus orientalis", "plant",  "Oriental plane"),
    "qayrag'och":   ("Ulmus",               "plant",  "Elm"),
    "qayragoch":    ("Ulmus",               "plant",  "Elm"),
    "eman":         ("Quercus",             "plant",  "Oak"),
    "qayin":        ("Betula",              "plant",  "Birch"),
    "qarag'ay":     ("Pinus",               "plant",  "Pine"),
    "saksovul":     ("Haloxylon",           "plant",  "Saxaul"),
    "jumrut":       ("Rhamnus cathartica",  "plant",  "Buckthorn"),

    # ===== YIRTQICHLAR =====
    "tulki":        ("Vulpes vulpes",       "animal", "Red fox"),
    "bo'ri":        ("Canis lupus",         "animal", "Wolf"),
    "buri":         ("Canis lupus",         "animal", "Wolf"),
    "shoqol":       ("Canis aureus",        "animal", "Golden jackal"),
    "ayiq":         ("Ursus arctos",        "animal", "Brown bear"),
    "qor qoploni":  ("Panthera uncia",      "animal", "Snow leopard"),
    "ilvirs":       ("Panthera uncia",      "animal", "Snow leopard"),
    "yo'lbars":     ("Panthera tigris",     "animal", "Tiger"),
    "yulbars":      ("Panthera tigris",     "animal", "Tiger"),
    "qoplon":       ("Panthera pardus",     "animal", "Leopard"),
    "karakal":      ("Caracal caracal",     "animal", "Caracal"),
    "silovsin":     ("Lynx lynx",           "animal", "Eurasian lynx"),

    # ===== KEMIRUVCHI VA MAYDA =====
    "quyon":        ("Lepus",               "animal", "Hare"),
    "sichqon":      ("Mus musculus",        "animal", "Mouse"),
    "kalamush":     ("Rattus",              "animal", "Rat"),
    "olmaxon":      ("Sciurus",             "animal", "Squirrel"),
    "yumronqoziq":  ("Spermophilus",        "animal", "Ground squirrel"),
    "tipratikan":   ("Erinaceus",           "animal", "Hedgehog"),
    "ko'rsichqon":  ("Ellobius",            "animal", "Mole rat"),
    "korsichqon":   ("Ellobius",            "animal", "Mole rat"),

    # ===== TUYOQLILAR =====
    "tog' qo'yi":   ("Ovis ammon",          "animal", "Argali"),
    "arxar":        ("Ovis ammon",          "animal", "Argali"),
    "jayran":       ("Gazella subgutturosa","animal", "Goitered gazelle"),
    "jayron":       ("Gazella subgutturosa","animal", "Goitered gazelle"),
    "saiga":        ("Saiga tatarica",      "animal", "Saiga"),
    "kiyik":        ("Cervus elaphus",      "animal", "Red deer"),
    "cho'chqa":     ("Sus scrofa",          "animal", "Wild boar"),
    "chochqa":      ("Sus scrofa",          "animal", "Wild boar"),
    "tuya":         ("Camelus",             "animal", "Camel"),

    # ===== UY HAYVONLARI =====
    "qo'y":         ("Ovis aries",          "animal", "Sheep"),
    "echki":        ("Capra hircus",        "animal", "Goat"),
    "sigir":        ("Bos taurus",          "animal", "Cow"),
    "ot":           ("Equus caballus",      "animal", "Horse"),
    "eshak":        ("Equus asinus",        "animal", "Donkey"),
    "it":           ("Canis lupus familiaris","animal","Dog"),
    "mushuk":       ("Felis catus",         "animal", "Cat"),

    # ===== QUSHLAR =====
    "burgut":       ("Aquila chrysaetos",   "bird",   "Golden eagle"),
    "lochin":       ("Falco peregrinus",    "bird",   "Peregrine falcon"),
    "qirg'iy":      ("Accipiter",           "bird",   "Hawk"),
    "qirgiy":       ("Accipiter",           "bird",   "Hawk"),
    "kaltak":       ("Falco tinnunculus",   "bird",   "Common kestrel"),
    "boyqush":      ("Strigiformes",        "bird",   "Owl"),
    "bulbul":       ("Luscinia megarhynchos","bird",  "Nightingale"),
    "chumchuq":     ("Passer domesticus",   "bird",   "House sparrow"),
    "kabutar":      ("Columba livia",       "bird",   "Rock dove"),
    "kaptar":       ("Columba",             "bird",   "Pigeon"),
    "qaldirg'och":  ("Hirundo rustica",     "bird",   "Barn swallow"),
    "qaldirgoch":   ("Hirundo rustica",     "bird",   "Barn swallow"),
    "laylak":       ("Ciconia ciconia",     "bird",   "White stork"),
    "tovuq":        ("Gallus gallus",       "bird",   "Chicken"),
    "o'rdak":       ("Anas platyrhynchos",  "bird",   "Mallard"),
    "urdak":        ("Anas platyrhynchos",  "bird",   "Mallard"),
    "g'oz":         ("Anser anser",         "bird",   "Greylag goose"),
    "goz":          ("Anser anser",         "bird",   "Greylag goose"),
    "kurka":        ("Meleagris gallopavo", "bird",   "Turkey"),
    "zag'izg'on":   ("Pica pica",           "bird",   "Eurasian magpie"),
    "zagizgon":     ("Pica pica",           "bird",   "Eurasian magpie"),
    "qarga":        ("Corvus",              "bird",   "Crow"),
    "chittak":      ("Parus major",         "bird",   "Great tit"),
    "tustovuq":     ("Phasianus colchicus", "bird",   "Pheasant"),

    # ===== SUDRALIB YURUVCHILAR =====
    "ilon":         ("Serpentes",           "reptile","Snake"),
    "gurza":        ("Macrovipera lebetina","reptile","Levant viper"),
    "efa":          ("Echis carinatus",     "reptile","Saw-scaled viper"),
    "kobra":        ("Naja oxiana",         "reptile","Central Asian cobra"),
    "qalqonbosh":   ("Agkistrodon",         "reptile","Pit viper"),
    "kaltakesak":   ("Lacertidae",          "reptile","Lizard"),
    "toshbaqa":     ("Testudo horsfieldii", "reptile","Russian tortoise"),

    # ===== HASHAROT VA O'RGIMCHAKSIMON =====
    "ari":          ("Apis mellifera",      "insect", "Western honey bee"),
    "chumoli":      ("Formicidae",          "insect", "Ant"),
    "kapalak":      ("Lepidoptera",         "insect", "Butterfly"),
    "pashsha":      ("Musca domestica",     "insect", "House fly"),
    "chivin":       ("Culicidae",           "insect", "Mosquito"),
    "qandala":      ("Pentatomidae",        "insect", "Stink bug"),
    "chigirtka":    ("Acrididae",           "insect", "Grasshopper"),
    "chayon":       ("Scorpiones",          "insect", "Scorpion"),
    "o'rgimchak":   ("Araneae",             "insect", "Spider"),
    "urgimchak":    ("Araneae",             "insect", "Spider"),

    # ===== SUV JONIVORLARI =====
    "baliq":        ("Actinopterygii",      "fish",   "Ray-finned fish"),
    "sazan":        ("Cyprinus carpio",     "fish",   "Common carp"),
    "cho'rtan":     ("Esox lucius",         "fish",   "Northern pike"),
    "chortan":      ("Esox lucius",         "fish",   "Northern pike"),
    "forel":        ("Salmo trutta",        "fish",   "Brown trout"),
    "qisqichbaqa":  ("Astacidae",           "animal", "Crayfish"),
    "qurbaqa":      ("Anura",               "animal", "Frog"),

    # ===== QO'ZIQORIN =====
    "qo'ziqorin":   ("Fungi",               "fungi",  "Fungus"),
    "qoziqorin":    ("Fungi",               "fungi",  "Fungus"),
    "shampinyon":   ("Agaricus bisporus",   "fungi",  "Button mushroom"),
    "bo'ri qulog'i":("Pleurotus",           "fungi",  "Oyster mushroom"),
}


def resolve_latin(latin: str) -> dict | None:
    """Reverse: Latin (Peganum harmala) → UZ name (Isiriq). Case-insensitive partial."""
    if not latin:
        return None
    q = latin.strip().lower()
    # Exact match first
    for uz_name, (lat, cat, en) in UZ_TO_LATIN.items():
        if lat.lower() == q:
            return {"uz": uz_name.title(), "latin": lat, "category": cat, "english": en}
    # Genus-only match (Artemisia vs Artemisia vulgaris)
    q_genus = q.split()[0] if q else ""
    for uz_name, (lat, cat, en) in UZ_TO_LATIN.items():
        lat_genus = lat.split()[0] if lat else ""
        if q_genus and lat_genus.lower() == q_genus:
            return {"uz": uz_name.title(), "latin": lat, "category": cat, "english": en}
    return None


def resolve_uz(term: str) -> dict | None:
    """O'zbek xalq nomini ilmiy nomga aylantiradi. Topilmasa None qaytaradi."""
    if not term:
        return None
    key = term.strip().lower()
    # Exact match
    if key in UZ_TO_LATIN:
        latin, cat, en = UZ_TO_LATIN[key]
        return {"original": term, "latin": latin, "category": cat, "english": en}
    # Prefix match (1-so'zli)
    for k, v in UZ_TO_LATIN.items():
        if k.startswith(key) and len(key) >= 4:
            return {"original": term, "latin": v[0], "category": v[1], "english": v[2]}
    return None


def looks_uzbek(term: str) -> bool:
    """Agar term o'zbek xalq nomi bo'lishi mumkin bo'lsa True.
    Kichik harf, no lotin binomial, qisqa — ehtimoliy UZ."""
    t = term.strip().lower()
    if not t or len(t) > 30:
        return False
    # Contains Latin marker (Panthera uncia → 2 words, capital)
    if " " in term and term[0].isupper() and term.split()[0][0].isupper():
        return False
    return True
