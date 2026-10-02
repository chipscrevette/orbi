"""Les exclusions expresses du règlement, garanties par le code plutôt que laissées au modèle.

Le règlement de Biarritz écrit des exclusions que le modèle lit bien (il les cite) mais n'applique pas toujours (il compte la
piscine dans l'emprise deux lignes après avoir noté qu'elle n'y compte pas : V01, V04 au banc de mise au point) :
  · « Les piscines, spas et jacuzzis sont exclus de cette règle » : tête des articles 7 (implantation par rapport aux limites
    séparatives) des zones UA à UH ;
  · DG B-5 : « les installations sportives de plein-air telles que piscines non couvertes, tennis ne sont pas comprises dans
    l'emprise au sol ».
tests/test_controle.py vérifie que ces phrases existent encore dans le règlement."""
import re

from orbi.reglement.donnees import article, norme

EXCLUT_PISCINE = re.compile(r"piscines?[^.]{0,60}exclu", re.I)
PHRASE_EMPRISE = "piscines non couvertes, tennis ne sont pas comprises dans l'emprise au sol"  # DG B-5


def articles_excluant(projet, passages):
    """Les articles lus dont le règlement exclut expressément ce projet (aujourd'hui : la piscine)."""
    if projet != "piscine":
        return set()
    return {p["ref"] for p in passages if EXCLUT_PISCINE.search(norme(article(p["ref"])["texte"]))}


def emprise_exclue(projet, couverte):
    """Une piscine non couverte ne compte pas dans l'emprise au sol (DG B-5)."""
    return projet == "piscine" and not couverte
