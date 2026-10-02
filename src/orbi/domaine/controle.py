"""Le contrôle de la grille : le code vérifie chaque ligne du modèle avant qu'elle compte dans la décision.

  1. La preuve. Le passage existe et la citation est une phrase exacte du règlement (recalée ou raccordée si elle est presque
     exacte). Une ligne sans preuve ne peut ni interdire ni autoriser : elle devient un simple point à vérifier. C'est la
     règle « l'absence de preuve n'est pas une autorisation », et son contraire : sans preuve, pas de « non » non plus.
  2. Le secteur. Une phrase qui ne nomme que d'autres secteurs que celui de la parcelle (« En Nh, … » pour une parcelle en N)
     ne vaut pas ici.
  3. Les nombres. Quand la règle donne un seuil et le projet une valeur, le code compare lui-même les deux nombres : le
     modèle ne fait que les extraire. Un nombre qui ne vient ni de la question, ni des faits, ni des passages est refusé.
Chaque correction est écrite dans le journal, que la trace garde."""
import itertools
import re

from orbi.reglement.donnees import chapitre, cite_bien, norme, page_citation, raccorder, recaler
from orbi.domaine.schemas import normaliser, sans_accent

CODES = r"U[A-HPY][a-z*]{0,3}|N(?:a|b|d|er|f|F|g|h|hd|hi|r|cu)\*?|IIAU[a-z]?"
MAX_REGLES = 8
# le fait qui manque est-il un fait déjà fixé (l'état actuel du bâtiment, la date de la maison) ? Le modèle range presque tout
# sous « projet » (V14, V26 : « la hauteur actuelle du bâtiment ») : le code relit la phrase
ETAT_ACTUEL = re.compile(r"\b(?:actuel(?:le)?s?|deja|aujourd'?hui|existait|date (?:de|d)|annee (?:de|d)|anterieur\w*|"
                         r"(?:avant|depuis) (?:le |l)?(?:\d{1,2} )?(?:[a-z]+ )?(?:19|20)\d\d)\b")
# l'emprise déjà construite s'AJOUTE à celle du projet : une somme à vérifier contre un plafond connu, qui ne change aucune règle,
# contrairement à une date ou à la hauteur actuelle d'un bâtiment qu'on surélève (V07 : deux abris de 9 m², la maison oubliée)
EMPRISE_EXISTANTE = re.compile(r"\b(?:emprise|surface au sol)\b.*\b(?:deja|existant\w*|present\w*|construit\w*)\b|"
                               r"\b(?:deja|existant\w*|present\w*|construit\w*)\b.*\b(?:emprise|surface au sol)\b")
# une règle de DISTANCE (« à 3 m de la limite ») que les murs existants ne respectent pas déjà : une surélévation ne la modifie pas
# (V14 : « mes murs sont à 2 m, je rehausse le toit »). Des travaux sur un bâtiment existant qui ne respecte pas une règle ne la
# violent pas pour autant, tant qu'ils ne l'aggravent pas (jurisprudence du Conseil d'État) : la violation n'est pas établie.
REGLE_DE_DISTANCE = re.compile(r"\b(?:limites?|distance|recul|eloign\w*)\b")
# pour une surélévation, tout ce qui touche au bâtiment (sa hauteur, sa distance à la limite) est déjà fixé
OBJET_BATI = re.compile(r"\b(?:le|du|de la|de l|la) ?(?:batiment|maison|immeuble|toit|egout|facade)\b")


def nombres(texte):
    """Tous les nombres d'un texte. Le point peut être un séparateur de milliers (« 1.000 m² » = 1000) : on garde les deux
    lectures. Les espaces de milliers (« 1 000 ») sont recollés."""
    t = re.sub(r"(?<=\d)[   ](?=\d{3}\b)", "", texte or "")
    out = set()
    for tok in re.findall(r"\d+(?:[.,]\d+)*", t):
        try:
            out.add(float(tok.replace(",", ".")))
        except ValueError:
            pass
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", tok):
            out.add(float(tok.replace(".", "")))
    return out


def _present(x, ensemble, conversions=False):
    """x figure-il dans l'ensemble ? Avec conversions, « 50 cm » dans la question valide aussi 0,5 (mètre)."""
    essais = {x, x * 100, x / 100} if conversions else {x}
    return any(abs(e - y) < 1e-6 for e in essais for y in ensemble)


def derives(nb):
    """Les nombres qu'on tire de ceux de la question : la somme de deux d'entre eux (90 m² existants + 8 m² créés = 98 m² ; un étage de
    3 m sur 9 m = 12 m) ou leur produit (8 m sur 4 m = 32 m²). Le modèle fait l'arithmétique ; le code vérifie que ses deux termes
    viennent bien de la question, et jamais des limites de la règle."""
    out = set()
    for a, b in itertools.combinations(sorted(nb), 2):
        out |= {a + b, a * b}
    return out


def comparer(valeur, seuil, sens):
    """Le jugement d'un chiffre : la seule comparaison que le modèle n'a plus à faire."""
    eps = 1e-9
    if sens == "au_plus":
        return "respectee" if valeur <= seuil + eps else "violee"
    if sens == "au_moins":
        return "respectee" if valeur >= seuil - eps else "violee"
    if sens == "limite_ou_au_moins":  # « sur la limite séparative ou à au moins 3 mètres »
        return "respectee" if abs(valeur) < eps or valeur >= seuil - eps else "violee"
    return None


def _par_citation(citation, passages):
    c = norme(citation)
    if len(c) < 20:
        return None
    return next((p for p in passages if c in norme(p["texte"])), None)


def indice_passage(pid):
    """« A » → 1, « B » → 2, « AA » → 27 ; « 3 » ou « P3 » → 3 ; rien → 0."""
    pid = re.sub(r"^P(?=\d)", "", (pid or "").strip().upper())
    if pid.isdigit():
        return int(pid)
    n = 0
    for c in pid:
        n = n * 26 + (ord(c) - 64) if "A" <= c <= "Z" else 0
    return n


def lettre(i):
    """1 → « A », 27 → « AA » : l'identifiant d'un passage, qui ne se confond pas avec un numéro d'article."""
    s = ""
    while i > 0:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _fmt(x):
    return f"{x:g}".replace(".", ",")


def controler(brutes, passages, zone, src_projet, src_regle, zero_ok=False, exclus=(), emprise_exclue=False, travaux_existant=False):
    """brutes : les lignes du modèle. passages : [{ref, pages, texte}] dans l'ordre où le modèle les a lues (P1, P2…).
    src_projet : les nombres de la question et des faits ; src_regle : ceux des passages. zero_ok : la question place le projet
    sur la limite (« collé au mur », « en limite ») : une distance de 0 est alors une valeur sourcée. exclus : les articles dont le
    règlement exclut expressément ce projet (« les piscines sont exclues de cette règle »). emprise_exclue : le projet ne compte pas
    dans l'emprise au sol (une piscine non couverte, DG B-5). travaux_existant : le projet est une surélévation, donc toute donnée
    sur le bâtiment est un fait déjà fixé. → (lignes, journal)"""
    chap = chapitre(zone)
    regles, journal, vus = [], [], set()
    for brute in (brutes or [])[: MAX_REGLES + 4]:
        if len(regles) >= MAX_REGLES:
            break
        r = normaliser(brute)
        r["id"] = f"R{len(regles) + 1}"
        n = indice_passage(r["passage"])
        p = passages[n - 1] if 1 <= n <= len(passages) else None
        cit = r["citation"]
        q = _par_citation(cit, passages)  # la citation décide du passage : le modèle se trompe parfois d'identifiant
        if q is not None and q is not p:
            journal.append(f"{r['id']} : identifiant de passage corrigé ({r['passage'] or 'aucun'} → {q['ref']})")
            p = q
        if p is None:
            journal.append(f"{r['id']} écartée : passage introuvable ({r['passage'] or 'aucun identifiant'})")
            continue
        ref = p["ref"]

        # 1. la preuve
        ok = bool(cit) and cite_bien(ref, cit)
        if not ok and cit:
            exact = recaler(ref, cit)
            cousue = None if exact else raccorder(ref, cit)
            for essai, nom in ((exact, "recalée sur le texte exact"), (cousue, "raccordée (« … » remis)")):
                if essai and cite_bien(ref, essai):
                    journal.append(f"{r['id']} : citation {nom}")
                    cit, ok = essai, True
                    break
        r.update(article=ref, pages=p["pages"], citation_ok=ok, citation=cit if ok else "",
                 page=page_citation(ref, cit) if ok else p["pages"][0])
        if ok:
            cle = (ref, norme(cit))
            if cle in vus:
                journal.append(f"{r['id']} : doublon écarté")
                continue
            vus.add(cle)
        else:
            journal.append(f"{r['id']} : citation introuvable dans {ref} — sans preuve, la ligne ne compte ni pour ni contre le projet")
            r["statut"], r["decisif"], r["fait_manquant"] = "inconnue", False, None

        # 2. le secteur, et l'exclusion expresse du projet par l'article
        if ref in exclus and r["nature"] in ("limite", "condition", "interdit") and not re.search(r"exclu", cit, re.I):
            r["vaut_ici"] = "non"
            journal.append(f"{r['id']} : le règlement exclut ce projet de la règle ({ref}) — règle écartée")
        if ok and r["vaut_ici"] == "oui":
            codes = set(re.findall(rf"\b(?:{CODES})\b", cit))
            if codes and not codes & {zone, chap} and not re.search(r"\bsauf\b", cit, re.I):
                r["vaut_ici"] = "non"
                journal.append(f"{r['id']} : la phrase ne vise que {sorted(codes)}, la parcelle est en {zone} — règle écartée")

        if emprise_exclue and r["vaut_ici"] != "non" and r["nature"] == "limite" and re.search("emprise", norme(cit) + " " + norme(r["exigence"])):
            r["vaut_ici"] = "non"
            journal.append(f"{r['id']} : une piscine non couverte ne compte pas dans l'emprise au sol (DG B-5) — règle écartée")

        # 3. les nombres
        if r["nature"] != "limite" and (r["sens"] or r["seuil"] is not None or r["valeur_projet"] is not None):
            r.update(sens=None, seuil=None, valeur_projet=None)  # un chiffre sur une exception ou une condition ne se compare pas
        if ok and r["sens"] and r["seuil"] is not None and r["valeur_projet"] is not None:
            if not _present(r["valeur_projet"], src_projet, conversions=True) and not (zero_ok and r["valeur_projet"] == 0):
                journal.append(f"{r['id']} : la valeur du projet ({_fmt(r['valeur_projet'])}) ne vient ni de la question ni des "
                               "faits — comparaison refusée")
                r.update(statut="inconnue", decisif=False, valeur_projet=None)
            elif not _present(r["seuil"], src_regle | src_projet):  # pas de conversion : 25 % ne devient pas 0,25 (V04)
                journal.append(f"{r['id']} : le seuil ({_fmt(r['seuil'])}) ne figure pas dans les passages — comparaison refusée")
                r.update(statut="inconnue", decisif=False, seuil=None)
            else:
                calcule = comparer(r["valeur_projet"], r["seuil"], r["sens"])
                if calcule != r["statut"]:
                    journal.append(f"{r['id']} : statut recalculé par le code, {r['statut']} → {calcule} "
                                   f"({_fmt(r['valeur_projet'])} {r['sens']} {_fmt(r['seuil'])})")
                    r["statut"], r["decisif"] = calcule, False
                r["compare_par_le_code"] = True
        if (travaux_existant and ok and r["nature"] == "limite" and r["statut"] == "violee" and r["sens"] in ("au_moins", "limite_ou_au_moins")
                and r["vaut_ici"] == "oui" and REGLE_DE_DISTANCE.search(sans_accent(norme(cit + " " + (r["exigence"] or ""))))):
            r["vaut_ici"] = "incertain"
            r["fait_manquant"] = "si la surélévation modifie la distance aux limites (les murs existants ne respectent pas déjà la règle)"
            journal.append(f"{r['id']} : une surélévation ne modifie pas la distance des murs existants — violation non établie")
        fait = sans_accent(norme(r["fait_manquant"] or ""))
        if (r["statut"] == "inconnue" and not r["decisif"] and fait and r["nature"] != "exception"
                and (ETAT_ACTUEL.search(fait) or (travaux_existant and r["nature"] == "limite" and OBJET_BATI.search(fait)))):
            r["decisif"] = True
            journal.append(f"{r['id']} : le fait qui manque est un fait déjà fixé (état actuel, date…), pas un choix de conception — il décide")
        if r["statut"] == "inconnue" and r["decisif"] and r["nature"] != "exception" and EMPRISE_EXISTANTE.search(fait):
            r["decisif"] = False
            journal.append(f"{r['id']} : l'emprise déjà construite s'ajoute à celle du projet : une somme à vérifier contre le plafond, "
                           "pas un fait qui décide")
        if r["statut"] == "inconnue" and not r["fait_manquant"] and r["nature"] != "exception" and ok:
            r["fait_manquant"] = r["exigence"] or None
        regles.append(r)
    return regles, journal
