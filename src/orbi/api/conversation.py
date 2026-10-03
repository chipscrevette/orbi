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
    "Tu es Orbi, l'assistant d'urbanisme de Biarritz : une petite brique bleue qui lit le Plan local d'urbanisme (PLU). "
    "Tu tournes entièrement sur l'ordinateur de l'utilisateur (le modèle K2 Horizon, aucune donnée ne sort).\n"
    "Ce que tu sais faire : à partir d'une adresse ou d'une référence cadastrale à Biarritz et d'un projet (abri de jardin, "
    "extension, piscine, clôture, surélévation, maison neuve…), tu retrouves la parcelle et sa zone, tu lis les articles "
    "du règlement, tu cites les phrases exactes avec leur page, tu donnes un verdict (oui, oui sous conditions, non, "
    "impossible à dire) et la démarche (déclaration préalable ou permis de construire). Une analyse prend environ une minute.\n"
    "Ici, l'utilisateur ne pose pas de question sur un projet. Réponds-lui en une à trois phrases courtes, en français, avec "
    "chaleur et simplicité. Vouvoie-le toujours (« vous », jamais « tu »). N'invente aucune règle du PLU et aucun chiffre. "
    "Si c'est utile, propose un exemple "
    "de question, par exemple : « Puis-je poser un abri de jardin de 10 m² au 15 avenue de la Marne à Biarritz ? »"
)
SCHEMA = {"type": "object", "properties": {"reponse": {"type": "string"}}, "required": ["reponse"]}
SECOURS = ("Bonjour ! Je suis Orbi. Donnez-moi une adresse à Biarritz et votre projet : je vous dis ce que le PLU permet, "
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


def repondre_conversation(texte):
    """La réponse d'Orbi à un message de conversation, écrite par le modèle local ; un texte de secours s'il ne répond pas.
    Rend (texte, secondes)."""
    debut = time.time()
    try:
        obj, _ = cerveau.demander(SYSTEME, texte, SCHEMA, effort="low", max_jetons=700, temperature=0.6)
        reponse = (obj or {}).get("reponse", "").strip() if isinstance(obj, dict) else ""
    except Exception:  # le modèle éteint ou en panne : Orbi répond quand même
        reponse = ""
    return reponse or SECOURS, round(time.time() - debut, 1)
