"""Avant / après : deux passages du banc d'essai sur les mêmes questions, et ce que chaque correction a changé.
Le premier passage est renoté avec le banc tel qu'il est aujourd'hui (3 attentes corrigées, voir outils/banc_essai_v2.py) :
sinon le progrès serait gonflé par les corrections du banc lui-même.
Usage : uv run python -m orbi.evaluation.pages.comparer bancs/resultats/banc-AVANT.json bancs/resultats/banc-APRES.json"""
import html
import json
import os
import sys

from orbi.evaluation.notation import renoter
from orbi.reglement.donnees import RACINE
from orbi.chemins import RESULTATS  # noqa: E402

CRITERES = [("verdict", "Verdict exact"), ("sens", "Bon sens"), ("grave", "Sans contresens"), ("demarche", "Démarche juste"), ("articles", "Bon article cité"),
            ("citations", "Citations exactes"), ("garde_fous", "Garde-fous passés")]
ETAPES = [("tri", "Tri", "K2, réflexion courte"), ("outils", "Outils", "code, API publiques"),
          ("perimetre", "Périmètre", "code"), ("demarche", "Démarche", "code, Code de l'urbanisme"),
          ("articles", "Articles", "code + recherche"), ("redaction", "Rédaction", "K2, réflexion moyenne"),
          ("garde_fous", "Garde-fous", "code")]
# chaque correction : l'étape du harnais où elle vit, ce qu'elle fait, une image du quotidien, les questions visées
CORRECTIONS = [
    ("outils", "L'adresse est cherchée à Biarritz",
     "« 12 avenue Édouard VII » sans nom de ville partait à Pau, « 96 avenue de Verdun » à Châteauroux.",
     "Comme un taxi à qui l'on donne la rue sans la ville.", ["V17", "V19", "V20"]),
    ("tri", "La référence cadastrale est lue",
     "Une rue sans numéro tombait en zone UD ; la parcelle CA 0044 est en zone Ncu, où l'on ne construit pas.",
     "La rue, c'est tout un quartier ; la parcelle, c'est le terrain.", ["V29"]),
    ("tri", "Le sujet « explication » impose le verdict « information »",
     "« 25 % de quoi ? », « lequel s'applique ? » : le code interdit alors oui et non. Effet de bord : avec la "
     "nouvelle liste de sujets, le tri a laissé passer une dérogation et un contentieux (V21, V24).",
     "À « quelle heure est-il ? », on ne répond pas « oui ».",
     ["V08", "V09", "V10", "V15", "V19", "V20", "V23", "V21", "V24"]),
    ("perimetre", "« Autres travaux » n'est plus refusé d'office",
     "Une question sans projet de la liste partait en « hors périmètre » ; elle lit maintenant les articles généraux.",
     "Le guichet ne renvoie plus quelqu'un parce que sa question n'est pas dans le formulaire.", ["V08", "V09", "V23"]),
    ("perimetre", "Une définition se passe d'adresse",
     "Sans adresse, l'agent répond avec les dispositions générales, valables dans toutes les zones.",
     "Le dictionnaire ne demande pas où vous habitez.", ["V10"]),
    ("tri", "La surface du projet est comptée",
     "« Moins de 10 m² » devient 10 ; deux abris de 9 m² font 18, écrit dans le contexte pour le contrôle des chiffres.",
     "Le devis additionne les lignes avant de donner le total.", ["V02", "V07"]),
    ("articles", "Les recherches parlent la langue du règlement",
     "« Permis d'aménager » est écarté des recherches ; le premier résultat par les mots est toujours gardé (« parpaing »).",
     "On ne cherche pas le mot « recette » dans un livre de cuisine.", ["V18"]),
    ("articles", "Les prescriptions de la parcelle appellent leur article",
     "« Règles architecturales particulières (cf. Art. 11) » ajoute l'article 11 ; l'article 11 entre aussi dans les "
     "recettes extension, abri et surélévation.",
     "Un renvoi en bas de page, on le suit.", ["V18", "V19"]),
    ("redaction", "Le verdict porte sur le projet",
     "« La mairie peut-elle refuser ? » appelle un verdict sur la piscine ; « pourront être interdites » n'est pas "
     "« interdit » ; en zone N, une exception réservée aux espaces verts protégés ne vaut pas ailleurs.",
     "« Peut-on me refuser ce crédit ? » : la vraie question est « l'aurai-je ? ».", ["V03", "V11", "V12", "V25", "V28"]),
    ("redaction", "Pas de JSON : nouvel essai en réflexion courte",
     "La réflexion mangeait les 1 600 jetons avant la réponse ; 2 400 jetons, puis un essai court si rien ne sort.",
     "Si l'élève n'a rien rendu, on lui redonne la copie avec moins de brouillon.", ["V16", "V26"]),
    ("garde_fous", "Les citations sont recalées sur le texte exact",
     "Le modèle « corrigeait » un accord (existants → existantes) ; des puces invisibles du PDF bloquaient la "
     "comparaison. Le code remet la phrase exacte, jamais si un chiffre ou une négation change.",
     "Le correcteur remet la citation telle qu'elle est dans le livre, sans toucher au sens.", ["V07", "V14", "V29"]),
]
# une étape sans correction dit pourquoi
INCHANGE = {"demarche": ("Rien à corriger", "La démarche applique le Code de l'urbanisme, écrit en dur dans le code. Ses "
                         "erreurs venaient d'une surface mal lue au tri (« moins de 10 m² »), corrigée là-bas.")}
# le banc aussi a été corrigé : chaque attente relue dans le règlement ou le Code de l'urbanisme
BANC_CORRIGE = [
    ("V03", "La démarche d'une piscine dépend de la taille du bassin, que la question ne donne pas : « dépend de la "
            "surface », et non « déclaration préalable »."),
    ("V14", "Rehausser un toit sans dire la surface créée : « dépend de la surface créée »."),
    ("V28", "En zone N, l'article N 2 b) admet les annexes des constructions qui existaient au P.O.S. de 1995 : sans "
            "connaître la date de la maison, le verdict est « impossible à dire », pas « non »."),
    ("V16 · V26", "La notation aussi : au 1er passage, ces deux questions n'avaient pas de réponse, et le « impossible à dire » "
                  "affiché par défaut tombait juste. Une non-réponse ne compte plus comme un verdict juste."),
]

BANC_SOUS_TITRE = ("En relisant le règlement et les traces, trois attentes du banc et une règle de notation se sont "
                   "révélées fausses. Les deux passages sont notés avec le banc corrigé : les scores ci-dessus ne "
                   "profitent pas de ces changements.")


SOUS_TITRE = {"verdict": "le type exact : oui, sous conditions, non…", "sens": "permis, interdit ou indéterminé", "grave": "jamais « oui » quand c'est « non », ni l'inverse",
              "demarche": "rien, déclaration ou permis", "articles": "au moins un des articles attendus",
              "citations": "mot pour mot dans l'article", "garde_fous": "aucune faute relevée par le code"}
RATE = {"verdict": "verdict exact", "sens": "mauvais sens", "grave": "contresens (oui ↔ non)", "demarche": "démarche", "articles": "article attendu absent",
        "citations": "citation inexacte", "garde_fous": "garde-fou non satisfait"}


def charger(chemin):
    d = renoter(chemin)  # renoté avec le banc d'aujourd'hui
    return d, {l["id"]: l for l in d["lignes"]}, d["resume"]["scores"]


def main(avant, apres, notes=None):
    """notes (fichier JSON écrit à la main après lecture des traces) : l'exemple à montrer, le diagnostic de chaque
    échec restant, les angles morts (les fautes que la notation automatique ne voit pas), et pour une autre paire de
    passages que 1 → 2 : les corrections, les noms des passages, l'historique (passages plus anciens, en repère)."""
    notes = notes or {}
    exemple, restes, angles = notes.get("exemple", "V29"), notes.get("restes", {}), notes.get("angles_morts", [])
    corrections = [tuple(c) for c in notes.get("corrections", CORRECTIONS)]
    inchange = {k: tuple(v) for k, v in notes.get("inchange", INCHANGE).items()}
    banc_corrige = [tuple(c) for c in notes.get("banc_corrige", BANC_CORRIGE)]
    nom1, nom2 = notes.get("noms", ["Passage 1", "Passage 2"])
    qui_etape = notes.get("etapes_qui", {})
    etapes = [tuple(x) for x in notes.get("etapes", ETAPES)]
    e = html.escape
    d1, L1, T1 = charger(avant)
    d2, L2, T2 = charger(apres)
    anciens = [(h.get("nom"), charger(os.path.join(RACINE, h["banc"]))[2]) for h in notes.get("historique", [])]
    brut1 = d1["resume"]["scores_publies"]  # le score publié au passage « avant », avant la correction du banc
    t1, t2 = d1["resume"]["temps_moyen_s"], d2["resume"]["temps_moyen_s"]

    # ---------------------------------------------------------------- tuiles : avant → après, repère = le maximum
    note_temps = f"<em>{e(notes['temps'])}</em>" if notes.get("temps") else ""
    tuiles = ""
    for k, titre in CRITERES:
        (a, n), (b, _) = T1[k], T2[k]
        note = "".join(f"<em>{e(nom.lower())} : {T[k][0]}/{T[k][1]}</em>" for nom, T in anciens)
        note += (f"<em>publié au {nom1.lower()} : {brut1[k][0]}/{brut1[k][1]}</em>" if k in brut1 and list(brut1[k]) != [a, n]
                 else ("<em>nouveau critère, les passages notés pareil</em>" if k not in brut1 else ""))
        tuiles += (f"<div class='tuile'><span class='t'>{e(titre)}<em>{e(SOUS_TITRE[k])}</em></span><b><s>{a}</s> → {b}<small>/{n}</small></b>"
                   f"<div class='barre'><i class='av' style='width:{100 * a / n:.1f}%'></i>"
                   f"<i class='ap' style='width:{100 * max(0, b - a) / n:.1f}%;left:{100 * a / n:.1f}%'></i>"
                   f"{'' if b >= a else f'<i class=re style=width:{100 * (a - b) / n:.1f}%;left:{100 * b / n:.1f}%></i>'}</div>"
                   f"<span class='d {'plus' if b > a else ('moins' if b < a else '')}'>{'+' if b >= a else ''}{b - a}</span>{note}</div>")
    tuiles += (f"<div class='tuile'><span class='t'>Temps moyen<em>par question, sur une carte graphique de joueur</em></span>"
               f"<b><s>{t1}</s> → {t2}<small> s</small></b>"
               f"<div class='barre'><i class='av' style='width:{min(100, 100 * t1 / 90):.0f}%'></i></div>"
               f"<span class='d moins'>max {d2['resume']['temps_max_s']} s</span>{note_temps}</div>")

    # ---------------------------------------------------------------- le harnais, et ce que chaque correction a réparé
    def puce(i):
        n1, n2 = L1[i]["note"], L2[i]["note"]
        ok1 = all(v in (True, None) for v in n1.values())  # une question est juste si tous ses critères le sont
        ok2 = all(v in (True, None) for v in n2.values())
        cls = "repare" if ok2 and not ok1 else ("casse" if ok1 and not ok2 else ("ok" if ok2 else "ko"))
        titre = f"{i} : {L2[i]['question']} — verdict attendu « {L2[i]['attendu']['verdict_type']} », obtenu « {L2[i]['obtenu']['verdict_type']} »"
        return f"<span class='puce {cls}' title='{e(titre)}'>{i}</span>"

    def rien(cle):
        t = inchange.get(cle, ("Inchangée", ""))
        return f"<div class='fiche calme'><h4>{e(t[0])}</h4><p>{e(t[1])}</p></div>"

    colonnes = ""
    for cle, nom, qui in etapes:
        fiches = "".join(
            f"<div class='fiche'><h4>{e(t)}</h4><p>{e(quoi)}</p><p class='image'>{e(image)}</p>"
            f"<div class='puces'>{''.join(puce(i) for i in ids)}</div></div>"
            for etape, t, quoi, image, ids in corrections if etape == cle)
        colonnes += (f"<div class='etape {'k2' if 'K2' in qui else 'code'}'><div class='tete'><b>{e(nom)}</b>"
                     f"<span>{e(qui_etape.get(cle, qui))}</span></div>{fiches or rien(cle)}</div>")

    image = notes.get("image")
    image_html = (f"<figure class='figure'><img src='{e(image['src'])}' alt='{e(image['legende'])}'><figcaption>{e(image['legende'])}"
                  f"</figcaption></figure>") if image else ""
    tests = notes.get("tests") or []
    tests_html = ("<h2>" + e(notes.get("tests_titre", "Du code qu'on teste")) + "</h2><div class='corr' style='grid-template-columns:repeat("
                  + str(len(tests)) + ",1fr)'>" + "".join(f"<div class='carte'><b>{e(t)}</b> {e(x)}</div>" for t, x in tests) + "</div>") if tests else ""

    # ---------------------------------------------------------------- une variante du passage « après » (même code, un réglage)
    var_html = ""
    if notes.get("variante"):
        var = notes["variante"]
        dv, Lv, Tv = charger(os.path.join(RACINE, var["banc"]))
        base = var.get("nom_base", nom2)  # le nom du passage « après » dans ce duel

        def cellule(a, b, plus_petit_mieux=False):
            if a == b:
                return f"<td>{a}</td><td>{b}</td>"
            gagne_a = (a < b) if plus_petit_mieux else (a > b)
            return f"<td class='{'gagne' if gagne_a else ''}'>{a}</td><td class='{'' if gagne_a else 'gagne'}'>{b}</td>"

        rangs = "".join(f"<tr><th>{e(t)}</th>{cellule(T2[k][0], Tv[k][0])}<td class='sur'>/{T2[k][1]}</td></tr>" for k, t in CRITERES)
        rangs += (f"<tr><th>Temps moyen (s)</th>{cellule(d2['resume']['temps_moyen_s'], dv['resume']['temps_moyen_s'], True)}"
                  f"<td class='sur'></td></tr>")
        ecarts = ""
        for i in L2:
            a, b = L2[i]["note"]["verdict"], Lv[i]["note"]["verdict"]
            if a != b:
                ecarts += (f"<li><b>{i}</b> juste en {e((base if a else var['nom']).lower())} seulement : « "
                           f"{e((L2[i] if a else Lv[i])['obtenu']['verdict_type'])} » contre « "
                           f"{e((Lv[i] if a else L2[i])['obtenu']['verdict_type'])} »</li>")
        var_html = (f"<h2>{e(var['titre'])}</h2><p class='sous'>{e(var['texte'])}</p><div class='duel'><table class='duel-t'>"
                    f"<tr><th></th><th>{e(base)}</th><th>{e(var['nom'])}</th><th></th></tr>{rangs}</table>"
                    f"<div class='carte abdiff'><b>Questions où les deux réglages divergent</b><ul>{ecarts or '<li>aucune</li>'}</ul>"
                    f"<p>{e(var.get('conclusion', ''))}</p></div></div>")

    # ---------------------------------------------------------------- un exemple réel, avant / après
    def carte(l, titre):
        o = l["obtenu"]
        regles = "".join(f"<li class='{'v' if g.get('verifiee') else 'x'}'><b>{e(g.get('article') or '')}</b>"
                         f"{' p. ' + str(g.get('page')) if g.get('page') else ''} « {e(g.get('citation') or '')} »</li>"
                         for g in o.get("regles") or [])
        fautes = "".join(f"<li>{e(x)}</li>" for x in o.get("garde_fous") or [])
        return (f"<div class='ex'><span class='quand'>{titre}</span><span class='badge {'bon' if l['note']['verdict'] else 'faux'}'>"
                f"{e(o.get('verdict_type') or '')}</span><p class='rep'>{e(o.get('reponse') or '')}</p>"
                f"{f'<ul class=cit>{regles}</ul>' if regles else ''}{f'<ul class=fautes>{fautes}</ul>' if fautes else ''}</div>")

    x = L2[exemple]
    exemple_html = (f"<p class='q'>« {e(x['question'])} »</p><p class='attendu'>Attendu : <b>{e(x['attendu']['verdict_type'])}</b> — "
                    f"{e(x['attendu']['verdict'])}</p><div class='duo'>{carte(L1[exemple], nom1)}{carte(x, nom2)}</div>")

    # ---------------------------------------------------------------- ce qui reste faux
    rest_html = ""
    for i, l in L2.items():
        if all(v in (True, None) for v in l["note"].values()):
            continue
        rates = ", ".join(RATE[k] for k, _ in CRITERES if l["note"][k] is False)
        rest_html += (f"<div class='reste'><span class='id'>{i}</span><div><p class='q'>{e(l['question'])}</p>"
                      f"<p><b class='rate'>{e(rates)}</b> · attendu « {e(l['attendu']['verdict_type'])} », obtenu « "
                      f"{e(l['obtenu'].get('verdict_type') or '')} »</p>"
                      f"{f'<p class=diag>{e(restes[i])}</p>' if i in restes else ''}</div></div>")

    synthese = notes.get("synthese") or []
    if synthese:  # les causes regroupées : ce que corrigera le prochain passage
        n_restes = sum(1 for l in L2.values() if not all(v in (True, None) for v in l["note"].values()))
        rest_html += (f"<div class='reste synthese' style='grid-column:span {1 if n_restes % 2 else 2}'><div><p class='q'>"
                      f"Les causes, regroupées</p><ul>"
                      + "".join(f"<li><b>{e(s['cause'])}</b> <span class='ids'>{e(s['ids'])}</span> → {e(s['remede'])}</li>"
                                for s in synthese) + "</ul></div></div>")

    # ---------------------------------------------------------------- toutes les questions
    def case(k, i):
        a, b = L1[i]["note"][k], L2[i]["note"][k]
        if b is None:
            return "<td class='na'>—</td>"
        if a == b:
            return f"<td class='{'ok' if b else 'ko'}'>{'✓' if b else '✗'}</td>"
        return f"<td class='{'rep' if b else 'cas'}'>{'✗ → ✓' if b else '✓ → ✗'}</td>"

    lignes = "".join(f"<tr><td class='id'>{i}</td><td class='qu'>{e(l['question'])}</td>{''.join(case(k, i) for k, _ in CRITERES)}"
                     f"<td class='t'>{L1[i]['obtenu'].get('secondes') or '—'} → {l['obtenu'].get('secondes') or '—'} s</td></tr>"
                     for i, l in L2.items())
    corr = "".join(f"<div class='carte'><b>{i}</b> {e(t)}</div>" for i, t in banc_corrige)
    morts = "".join(f"<div class='mort'><span class='id'>{e(a['id'])}</span><div><p class='extrait'>« {e(a['extrait'])} »</p>"
                    f"<p>{e(a['pourquoi'])}</p><p class='capteur'><b>À faire :</b> {e(a['capteur'])}</p></div></div>"
                    for a in angles)
    morts_html = (f"<h2>Ce que le banc ne voit pas</h2><p class='sous'>Des fautes trouvées en lisant les réponses et les traces, que la notation automatique ne compte pas.</p><div class='morts'>{morts}</div>"
                  if angles else "")

    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Avant, après · assistant PLU</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<p class="kicker">Assistant PLU de Biarritz · banc d'essai · {e(d2['resume']['date'][:10])}</p>
<h1>{e(notes.get('titre', 'Mêmes 30 questions, deux passages : ce que le harnais a changé'))}</h1>
<p class="chapo">Le modèle n'a pas bougé (K2 Horizon 7B, sur la carte graphique du PC). Entre les deux passages, seules les
pièces autour de lui ont changé : {len(corrections)} corrections du harnais. Chaque critère est noté par le code, pas par une IA.</p>
<div class="tuiles">{tuiles}</div>
{image_html}

<h2>Où vivent les corrections</h2>
<p class="sous">Les {len(etapes)} étapes d'une réponse, de gauche à droite. Sous chaque étape, ses corrections et les questions
qu'elles visaient : <span class="puce repare">vert</span> réparée, <span class="puce ok">gris</span> déjà juste et restée juste,
<span class="puce ko">rouge</span> encore fausse, <span class="puce casse">barrée</span> cassée par la correction.</p>
<div class="harnais" style="grid-template-columns:repeat({len(etapes)},1fr)">{colonnes}</div>{tests_html}

{var_html}
<h2>Un exemple réel</h2>
<div class="exemple">{exemple_html}</div>

<h2>Ce qui reste faux</h2>
<p class="sous">Chaque échec du {e(nom2.lower())}, avec ce qu'il a raté et la cause lue dans sa trace.</p>
<div class="restes">{rest_html or '<p>Rien.</p>'}</div>
{morts_html}
<h2>{e(notes.get('banc_titre', 'Le banc aussi a été corrigé'))}</h2>
<p class="sous">{e(notes.get('banc_sous_titre', BANC_SOUS_TITRE))}</p>
<div class="corr" style="grid-template-columns:repeat({len(banc_corrige) + 1},1fr)">{corr}<div class="carte avert"><b>À garder en tête</b> Ces 30 questions ont servi à trouver les défauts,
puis à vérifier les corrections : c'est un banc de mise au point. Pour mesurer vraiment, il faut un second banc de questions
que l'agent n'a jamais vues, noté une seule fois.</div></div>

<h2>Question par question</h2>
<table><tr><th>n°</th><th>question</th>{''.join(f'<th>{e(t)}</th>' for _, t in CRITERES)}<th>temps</th></tr>{lignes}</table>
</body></html>"""
    sortie = os.path.join(RESULTATS, notes.get("sortie") or f"avant-apres-{os.path.basename(apres)[5:-5]}.html")
    open(sortie, "w", encoding="utf-8").write(page)
    print(sortie)
    return T1, T2


CSS = """
:root{--fond:#F5F0E8;--carte:#fff;--encre:#1D1A17;--gris:#8A837B;--filet:#E4DCD0;--vert:#2f9e44;--vertc:#d3f0da;
--rouge:#C22E4A;--rougec:#fde2e7;--acc:#1971c2;--k2:#7048e8;--k2c:#efeafe;--code:#1D1A17}
*{box-sizing:border-box;margin:0}
body{background:var(--fond);color:var(--encre);font:400 15px/1.45 Geist,system-ui,sans-serif;padding:32px 40px 60px;max-width:1500px;margin:auto}
.kicker{color:var(--gris);font-weight:600;letter-spacing:.04em;text-transform:uppercase;font-size:12px}
h1{font-size:40px;font-weight:800;line-height:1.08;margin:6px 0 8px;max-width:1100px}
h2{font-size:24px;font-weight:800;margin:34px 0 6px}
.chapo{color:var(--gris);font-size:17px;max-width:1100px;margin-bottom:22px}
.sous{color:var(--gris);max-width:1100px;margin-bottom:14px}
.tuiles{display:grid;grid-template-columns:repeat(8,1fr);gap:10px}
.tuile{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:16px 18px;display:flex;flex-direction:column;gap:8px}
.tuile .t{color:var(--gris);font-size:14px;font-weight:600}
.tuile b{font-size:30px;font-weight:800;line-height:1;white-space:nowrap}
.tuile b s{color:var(--gris);font-weight:600;font-size:24px;text-decoration:none}
.tuile small{font-size:18px;color:var(--gris);font-weight:600}
.tuile em{color:var(--gris);font-size:12px;font-style:normal}
.barre{position:relative;height:10px;border-radius:5px;background:var(--filet);overflow:hidden}
.barre i{position:absolute;top:0;bottom:0;left:0}
.barre .av{background:#b9b0a4}.barre .ap{background:var(--vert)}.barre .re{background:var(--rouge)}
.d{font-weight:800;font-size:15px;color:var(--gris)}.d.plus{color:var(--vert)}.d.moins{color:var(--rouge)}
.harnais{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;align-items:start}
.etape{display:flex;flex-direction:column;gap:8px}
.tete{border-radius:12px;padding:10px 12px;color:#fff;display:flex;flex-direction:column;position:relative}
.etape.code .tete{background:var(--code)}.etape.k2 .tete{background:var(--k2)}
.tete b{font-size:17px}.tete span{font-size:12px;opacity:.8}
.etape:not(:last-child) .tete:after{content:"";position:absolute;right:-9px;top:50%;margin-top:-7px;border:7px solid transparent;border-left-color:var(--gris)}
.fiche{background:var(--carte);border:1px solid var(--filet);border-radius:12px;padding:10px 12px;display:flex;flex-direction:column;gap:5px}
.fiche h4{font-size:14px;line-height:1.25}.fiche p{font-size:13px;color:#4a443e}
.fiche .image{font-style:italic;color:var(--gris)}
.rien{color:var(--gris);font-size:13px;padding:8px 12px}
.puces{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}
.puce{display:inline-block;font-size:12px;font-weight:800;border-radius:6px;padding:2px 6px;background:var(--filet);color:var(--gris)}
.puce.repare{background:var(--vertc);color:var(--vert)}.puce.ko{background:var(--rougec);color:var(--rouge)}
.puce.casse{background:var(--rougec);color:var(--rouge);text-decoration:line-through}
.exemple{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:18px 20px}
.exemple .q{font-size:20px;font-weight:600}.exemple .attendu{color:var(--gris);margin:4px 0 12px}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.ex{border:1px solid var(--filet);border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:8px}
.quand{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--gris);font-weight:700}
.badge{align-self:flex-start;font-weight:800;font-size:18px;border-radius:8px;padding:3px 10px}
.badge.bon{background:var(--vertc);color:var(--vert)}.badge.faux{background:var(--rougec);color:var(--rouge)}
.ex .rep{font-size:15px}.cit{padding-left:0;list-style:none;display:flex;flex-direction:column;gap:4px;font-size:13px}
.cit li:before{font-weight:800;margin-right:6px}.cit li.v:before{content:"✓";color:var(--vert)}.cit li.x:before{content:"✗";color:var(--rouge)}
.fautes{color:var(--rouge);font-size:13px;padding-left:18px}
.restes{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.reste{display:flex;gap:10px;background:var(--carte);border:1px solid var(--filet);border-radius:12px;padding:10px 12px}
.reste .id{font-weight:800;color:var(--rouge);min-width:36px}.reste .q{font-weight:600}.reste p{font-size:14px}
.reste .rate{color:var(--rouge)}.reste .diag{color:#4a443e;margin-top:3px}
.reste.synthese{background:#1D1A17;color:#fff;border-color:#1D1A17}.synthese ul{padding-left:0;list-style:none;display:flex;flex-direction:column;gap:5px;margin-top:6px}
.synthese li{font-size:14px;color:#e9e3da}.synthese b{color:#fff}.synthese .ids{color:#f4a4b4;font-weight:700;font-size:12px}
.morts{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.mort{display:flex;gap:10px;background:var(--carte);border:1px solid var(--filet);border-left:4px solid #e8a33a;border-radius:12px;padding:10px 12px}
.mort .id{font-weight:800;color:#b86e00;min-width:36px}.mort p{font-size:14px}
.mort .extrait{font-style:italic;background:#fff3db;border-radius:6px;padding:2px 6px;margin-bottom:4px}
.mort .capteur{color:#4a443e;margin-top:3px}
.corr{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.figure{margin:22px 0 0}.figure img{width:100%;border:1px solid var(--filet);border-radius:14px;background:#fff}
.figure figcaption{color:var(--gris);font-size:13px;margin-top:6px}
.duel{display:grid;grid-template-columns:1fr 1.15fr;gap:14px;align-items:stretch}
table.duel-t{border-collapse:separate;border-spacing:0;width:100%}table.duel-t th,table.duel-t td{padding:9px 14px;font-size:15px}
table.duel-t th{text-transform:none;letter-spacing:0;font-size:14px;color:var(--encre);text-align:left;font-weight:600}
table.duel-t td{text-align:center;font-weight:800;font-size:18px;color:var(--gris)}table.duel-t td.gagne{color:var(--vert);background:var(--vertc)}
table.duel-t td.sur{font-size:13px;font-weight:600;text-align:left;padding-left:0}
.abdiff{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:18px 20px;font-size:15px;display:flex;flex-direction:column;gap:6px}.abdiff li{margin:5px 0}.abdiff p{margin-top:auto;font-size:16px;color:var(--encre);background:var(--vertc);border-radius:10px;padding:12px 14px}
.abdiff ul{padding-left:18px;margin:8px 0}.abdiff p{color:#4a443e}
.corr .carte{background:var(--carte);border:1px solid var(--filet);border-radius:12px;padding:12px 14px;font-size:14px}
.corr b{margin-right:6px}.corr .avert{background:#fff7e0;border-color:#f0dca0}
.tuile .t em{display:block;font-weight:400;font-size:12px;margin-top:2px}.tuile .t{min-height:56px}
.fiche.calme{background:#ece5da;border-color:transparent}
table{width:100%;border-collapse:collapse;background:var(--carte);border:1px solid var(--filet);border-radius:14px;overflow:hidden}
th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--gris);padding:10px 8px;border-bottom:1px solid var(--filet)}
td{padding:7px 8px;border-bottom:1px solid var(--filet);vertical-align:top;font-size:14px}
td.id{font-weight:800;width:48px}td.qu{max-width:560px}
td.ok,td.ko,td.na,td.rep,td.cas{text-align:center;font-weight:800;width:104px;white-space:nowrap}
td.ok{color:var(--vert)}td.ko{color:var(--rouge)}td.na{color:var(--filet)}
td.rep{color:var(--vert);background:var(--vertc)}td.cas{color:var(--rouge);background:var(--rougec)}
td.t{color:var(--gris);width:120px;text-align:right;white-space:nowrap}
@media (max-width:1100px){.tuiles{grid-template-columns:repeat(3,1fr)}.harnais{grid-template-columns:repeat(2,1fr)}
.etape .tete:after{display:none}.restes,.duo,.morts,.duel{grid-template-columns:1fr}.corr{grid-template-columns:1fr 1fr}}
@media (max-width:640px){body{padding:20px 16px}h1{font-size:28px}.tuiles{grid-template-columns:1fr 1fr}.harnais{grid-template-columns:1fr}
table{display:block;overflow-x:auto}}
"""

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else None)
