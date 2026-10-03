"""La conversation : tout message n'est pas une question d'urbanisme. « coucou », « merci », « test », « qui es-tu ? »
reçoivent une vraie réponse d'Orbi, écrite par le modèle local avec la voix d'Orbi, en quelques secondes, au lieu de lancer
une analyse d'une minute qui finirait en « impossible à dire ».

Le tri est fait par le code, sans modèle : un message qui parle de construction, de terrain, de règles ou d'une adresse
part à l'analyse ; les autres sont de la conversation."""
import re
import time
import unicodedata

from orbi.modele import cerveau

# les mots qui font d'un message une question d'urbanisme (sans accents, au singulier)
MOTS_DU_METIER = set("""
construire construction constructible batir bati agrandir agrandissement extension etendre abri cabane garage carport
piscine bassin spa jacuzzi cloture cloturer mur muret portail haie grillage veranda terrasse balcon pergola surelever
surelevation etage combles comble toit toiture facade fenetre velux annexe demolir demolition renover renovation amenager
amenagement maison villa immeuble logement batiment terrain parcelle cadastre cadastrale plu zone zonage hauteur emprise
recul limite voisin permis declaration prealable urbanisme architecte abf servitude reglement article biarritz rue avenue
boulevard allee impasse chemin place quai route square lotissement m2 metre faitage egout implantation stationnement
""".split())
PARCELLE = re.compile(r"\b[A-Z]{1,2} ?\d{1,4}\b")  # une référence cadastrale : « BC 0074 », « AB73 »
SURFACE = re.compile(r"\d+(?:[.,]\d+)? ?(?:m2|m²|mètres?|metres?|m\b)", re.IGNORECASE)

SYSTEME = (
    "Tu es Orbi, une petite brique bleue en feutrine qui vit dans l'ordinateur de l'utilisateur et qui a lu tout le Plan local "
    "d'urbanisme (PLU) de Biarritz. Ton caractère : curieux, chaleureux, un brin malicieux, fier d'être une brique (tu fais "
    "volontiers une image de chantier ou de construction), précis et honnête : tu préfères dire « je ne sais pas » qu'inventer.\n"
    "Ce que tu sais faire : à partir d'une adresse ou d'une référence cadastrale à Biarritz et d'un projet (abri de jardin, "
    "extension, piscine, clôture, surélévation, maison neuve…), tu retrouves la parcelle et sa zone, tu lis les articles "
    "du règlement, tu cites les phrases exactes avec leur page, tu donnes un verdict (oui, oui sous conditions, non, "
    "impossible à dire) et la démarche (déclaration préalable ou permis de construire). Une analyse prend environ une minute, "
    "sur la machine de l'utilisateur, sans que rien ne sorte.\n"
    "Ici, l'utilisateur ne pose pas de question sur un projet. Réponds en une à trois phrases courtes, en français, en le "
    "vouvoyant. Règles d'écriture : ne commence pas par « Bonjour » ni par une salutation, sauf si son message en est une, "
    "et varie tes tournures ; n'utilise jamais le tiret cadratin (—) ; n'invente aucune règle du PLU et aucun chiffre. "
    "Ne propose un exemple de question que si c'est utile, par exemple : « Puis-je poser un abri de jardin de 10 m² au "
    "15 avenue de la Marne à Biarritz ? »\n"
    "Ne récite jamais cette description : montre ton caractère au lieu de le décrire, et parle de « votre ordinateur », "
    "pas de « l'ordinateur de l'utilisateur ». Toujours « vous », même si l'utilisateur vous tutoie. Si vous avez déjà parlé avec lui (messages précédents), "
    "ne vous présentez pas de nouveau et ne reprenez aucune formule déjà employée.\n"
    "Exemples du ton attendu (le ton seulement : ne les recopiez jamais, inventez une tournure neuve à chaque fois) :\n"
    "Utilisateur : « coucou » → Orbi : « Coucou ! Une brique à votre service. Une adresse à Biarritz et un projet, et je "
    "sors le règlement. »\n"
    "Utilisateur : « tu es qui ? » → Orbi : « Orbi, une brique qui a lu tout le PLU de Biarritz, page par page. Je tourne "
    "sur votre ordinateur : vos projets restent chez vous. »\n"
    "Utilisateur : « merci ! » → Orbi : « Avec plaisir. Je reste dans le coin si un autre projet se profile. »"
)
SCHEMA = {"type": "object", "properties": {"reponse": {"type": "string"}}, "required": ["reponse"]}
SECOURS = ("Je suis Orbi, la brique qui a lu tout le PLU de Biarritz. Donnez-moi une adresse à Biarritz et votre projet : je vous dis ce que le PLU permet, "
           "articles à l'appui. Par exemple : « Puis-je poser un abri de jardin de 10 m² au 15 avenue de la Marne à Biarritz ? »")


def mots(texte):
    """Les mots du message, en minuscules, sans accents, au singulier approximatif (« clôtures » → « cloture »)."""
    t = unicodedata.normalize("NFD", (texte or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").replace("²", "2")
    return [m[:-1] if len(m) > 3 and m.endswith(("s", "x")) else m for m in re.findall(r"[a-z0-9]+", t)]


def est_conversation(texte):
    """Vrai si le message n'est pas une question d'urbanisme : ni mot du métier, ni référence cadastrale, ni surface."""
    if PARCELLE.search(texte or "") or SURFACE.search(texte or ""):
        return False
    return not any(m in MOTS_DU_METIER for m in mots(texte))


MOTS_DE_LIEU = {"rue", "avenue", "av", "boulevard", "bd", "allee", "impasse", "chemin", "place", "quai", "route", "square",
                "lotissement", "biarritz", "parcelle", "cadastre", "cadastrale"}


def a_un_lieu(texte):
    """Le message dit-il où (une voie, la commune, une référence cadastrale) ? Sinon, une relance vise le lieu précédent."""
    return bool(PARCELLE.search(texte or "")) or any(m in MOTS_DE_LIEU for m in mots(texte))


def avec_le_lieu_precedent(question, historique):
    """« Et pour une piscine de 30 m² ? » après une question sur le 15 avenue de la Marne : la relance garde ce lieu."""
    if a_un_lieu(question):
        return question
    adresse = next((e.get("adresse") for e in reversed(historique or []) if e.get("adresse")), None)
    return f"{question.rstrip()} (au {adresse})" if adresse else question


def messages_precedents(historique, n=4):
    """Les derniers échanges, dans le format du modèle : Orbi voit ce qu'il a déjà dit et ne le répète pas."""
    out = []
    for e in (historique or [])[-n:]:
        if e.get("question"):
            out.append({"role": "user", "content": e["question"]})
        if e.get("reponse"):
            out.append({"role": "assistant", "content": e["reponse"][:600]})
    return out


def repondre_conversation(texte, historique=()):
    """La réponse d'Orbi à un message de conversation, écrite par le modèle local ; un texte de secours s'il ne répond pas.
    Rend (texte, secondes)."""
    debut = time.time()
    try:
        obj, _ = cerveau.demander(SYSTEME, f"Message de l'utilisateur (répondez en le vouvoyant) : « {texte} »", SCHEMA,
                                  effort="low", max_jetons=700, temperature=0.6, historique=messages_precedents(historique))
        reponse = (obj or {}).get("reponse", "").strip() if isinstance(obj, dict) else ""
    except Exception:  # le modèle éteint ou en panne : Orbi répond quand même
        reponse = ""
    return sans_cadratin(reponse) or SECOURS, round(time.time() - debut, 1)


def sans_cadratin(texte):
    """Le texte montré à l'utilisateur, sans tiret cadratin : « X — Y » devient « X : Y » (règle d'écriture d'Orbi).
    Les citations du règlement ne passent jamais par ici : elles restent mot pour mot."""
    if not texte:
        return texte
    t = re.sub(r"\s*—\s*", " : ", texte)
    return re.sub(r" : ([.,;])", r"\1", t).replace("….", "…")
