"""Le verrou de zone : les projets que l'article 1 d'une zone interdit à un particulier sans exception possible, écrits
dans le code et vérifiés dans le règlement (27/09/2026). Au 3e passage du banc, le modèle a lu une condition de l'article
Ncu 2 comme une autorisation et répondu « la maison neuve est possible dans la zone Ncu » (V29) : sur ces cas-là, le
verdict ne se laisse plus au modèle. Chaque entrée garde la phrase exacte du règlement qui la fonde ; elle est ajoutée
aux règles citées si le modèle l'oublie."""
from .donnees import chapitre

ZONES_STRICTES = {"N", "Ncu", "Ner", "IIAU"}  # « tous les types d'occupation du sol sont interdits, sauf… » (article 1)
HABITABLES_N = {"Nh", "Nh*", "Nhi*", "Nhd"}  # N 1 et N 2 : les seuls secteurs de la zone N où l'on peut habiter
# chapitre : l'article et la phrase exacte qui interdisent d'y construire une maison
INTERDIT_NEUF = {
    "Ncu": ("Ncu 1", "Toutes constructions qui ne seraient pas justifiées par la sécurité, l’équipement sanitaire, un "
                     "service public ou la confortation de l’existant"),
    "Ner": ("Ner 1", "Toutes constructions qui ne seraient pas justifiées par la sécurité, l’équipement sanitaire, les "
                     "services publics ou la confortation de l’existant"),
    "UG": ("UG 1", "les constructions destinées à l’habitation, sauf pour l’extension et la démolition des constructions "
                   "existantes sous les conditions fixées à l’article UG 2"),
    "UY": ("UY 1", "Sont interdits en zone UY et secteurs UY*, UYi, UYt : - les constructions destinées à l’habitation"),
    "IIAU": ("IIAU 1", "Tous les types d'occupation ou d'utilisation des sols sont interdits, sauf : - les aménagements "
                       "destinés au passage de réseaux"),
    "N": ("N 1", "Tous les types d'occupation ou d'utilisation des sols sont interdits"),
}
# N 2 b) : dans toute la zone N sauf Nf, Nh, Nh* et Nhi*, les annexes ne sont admises que pour une construction de 1995
ANNEXES_N = ("N 2", "l'extension, aménagement, les annexes des constructions existantes à la date d'approbation de la "
                    "révision du P.O.S. de mars 1995")


def verrou(projet, zone):
    """Ce que le code impose avant la rédaction : les verdicts permis, l'article et sa phrase exacte, et pourquoi.
    None quand l'article 1 laisse la question ouverte."""
    chap, z = chapitre(zone), (zone or "").strip()
    if projet == "maison neuve" and chap in INTERDIT_NEUF and not (chap == "N" and z in HABITABLES_N):
        art, phrase = INTERDIT_NEUF[chap]
        pourquoi = f"une maison neuve n'entre dans aucune exception de l'article {art} en {z}"
        if chap == "UG":
            pourquoi += " (seuls des logements de fonction liés à un équipement y sont prévus)"
        return {"verdicts": ["non"], "article": art, "citation": phrase, "pourquoi": pourquoi}
    if projet == "abri de jardin" and chap in ("Ncu", "Ner"):
        art, phrase = INTERDIT_NEUF[chap]
        return {"verdicts": ["non"], "article": art, "citation": phrase,
                "pourquoi": f"un abri de jardin est une construction nouvelle, qu'aucune exception de l'article {chap} 2 ne prévoit"}
    if projet in ("abri de jardin", "piscine") and chap == "N" and z not in HABITABLES_N | {"Nf", "NF"}:
        art, phrase = ANNEXES_N
        return {"verdicts": ["non", "impossible à dire"], "article": art, "citation": phrase,
                "pourquoi": "en zone N, une annexe n'est admise que pour une construction qui existait en mars 1995 "
                            "(N 2 b) : la réponse dépend de la date de la maison, que la question ne donne pas",
                "fait_manquant": "savoir si la maison existait déjà en mars 1995 (révision du P.O.S.)"}
    return None
