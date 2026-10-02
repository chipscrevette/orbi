"""Le savoir métier : ce qu'un instructeur sait sans le chercher dans le règlement, écrit dans le code et vérifié à la
source, comme la démarche. Au banc, l'agent inventait la définition de la surface de plancher (V10, « hors des
annexes ») et disait qu'une cave enterrée compte dans l'emprise (V09, en réflexion courte comme moyenne) : ce n'était
pas un défaut de raisonnement, c'était un garde-manger vide. Chaque texte est déclenché par les mots de la question et
donné au modèle avec sa source, qui s'affiche aussi sous la réponse. Textes relus sur Légifrance le 27/09/2026."""
import re

SAVOIR = [
    {"cle": "surface de plancher",
     "declencheur": re.compile(r"surface de plancher|\bSDP\b", re.I),
     "texte": "Code de l'urbanisme, article R111-22 (en vigueur depuis le 01/01/2016) : « La surface de plancher de la "
              "construction est égale à la somme des surfaces de plancher de chaque niveau clos et couvert, calculée à "
              "partir du nu intérieur des façades », après déduction notamment « des surfaces de plancher d'une hauteur "
              "sous plafond inférieure ou égale à 1,80 mètre » et « des surfaces de plancher aménagées en vue du "
              "stationnement des véhicules ». Le règlement de Biarritz ne la redéfinit pas.",
     "source": {"texte": "Code de l'urbanisme, R111-22", "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031721274"}},
    {"cle": "emprise au sol, au sens du Code",
     "declencheur": re.compile(r"surface de plancher.*emprise|emprise.*surface de plancher|diff[ée]rence.*emprise", re.I),
     "texte": "Code de l'urbanisme, article R*420-1 (en vigueur depuis le 01/04/2014), qui sert à savoir quelle "
              "autorisation demander : « L'emprise au sol au sens du présent livre est la projection verticale du volume "
              "de la construction, tous débords et surplombs inclus. » Pour ses propres règles d'emprise (article 9 de "
              "chaque zone), le PLU de Biarritz a sa définition, à l'article DG B-5.",
     "source": {"texte": "Code de l'urbanisme, R*420-1", "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000028678466/"}},
    {"cle": "ce qui compte dans l'emprise du PLU",
     "declencheur": re.compile(r"\bcaves?\b|sous-sol|enterr[ée]|terrasse|plain-pied|balcon|d[ée]bord", re.I),
     "texte": "Règlement de Biarritz, article DG B-5 : l'emprise est mesurée « à 0,60 m du sol naturel avant travaux », "
              "hors balcons, modénature et débords de toit. Une cave entièrement enterrée ou une terrasse de plain-pied, "
              "qui ne dépassent pas 0,60 m au-dessus du sol naturel, n'y comptent donc très probablement pas (à faire "
              "confirmer par la mairie pour un cas limite). Les piscines non couvertes n'y comptent pas non plus ; toutes "
              "les autres constructions de la parcelle y comptent.",
     "source": {"texte": "Règlement du PLU de Biarritz, DG B-5", "url": None}},
]


def savoir_pour(question):
    """Les textes utiles à cette question, dans l'ordre de la liste."""
    return [s for s in SAVOIR if s["declencheur"].search(question or "")]
