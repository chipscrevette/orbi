"""Le rapport d'un passage du banc d'essai : une page HTML (bancs/resultats/rapport-<banc>.html).
Usage : uv run python -m orbi.evaluation.pages.rapport [bancs/resultats/banc-XXXX.json]"""
import glob
import html
import json
import os
import sys

from orbi.evaluation.notation import renoter
from orbi.reglement.donnees import RACINE
from orbi.chemins import RESULTATS  # noqa: E402

CRITERES = [("verdict", "Verdict exact"), ("sens", "Bon sens"), ("grave", "Sans contresens"), ("demarche", "Démarche juste"), ("articles", "Bon article cité"),
            ("citations", "Citations exactes"), ("garde_fous", "Garde-fous passés")]


def main():
    chemin = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(os.path.join(RESULTATS, "banc-2*.json")))[-1]
    d = renoter(chemin)  # le banc et la notation d'aujourd'hui
    r, L = d["resume"], d["lignes"]
    e = html.escape
    tuiles = "".join(
        f"<div class='tuile'><b>{r['scores'][k][0]}<small>/{r['scores'][k][1]}</small></b><span>{e(t)}</span>"
        f"<i style='--p:{100 * r['scores'][k][0] / max(1, r['scores'][k][1]):.0f}%'></i></div>" for k, t in CRITERES)
    tuiles += (f"<div class='tuile'><b>{r['temps_moyen_s']}<small> s</small></b><span>Temps moyen (max {r['temps_max_s']} s)</span>"
               f"<i style='--p:{min(100, 100 * r['temps_moyen_s'] / 60):.0f}%'></i></div>")
    lignes = []
    for l in L:
        cases = "".join(f"<td class='{'ok' if l['note'][k] else ('ko' if l['note'][k] is False else 'na')}'>"
                        f"{'✓' if l['note'][k] else ('✗' if l['note'][k] is False else '—')}</td>" for k, _ in CRITERES)
        o, a = l["obtenu"], l["attendu"]
        detail = ""
        if not all(v in (True, None) for v in l["note"].values()):
            fautes = "".join(f"<li>{e(x)}</li>" for x in o.get("garde_fous") or [])
            detail = (f"<tr class='detail'><td colspan='9'><p><b>Attendu :</b> {e(a['verdict'])} · démarche : {e(a['demarche_type'])}"
                      f" · articles : {e(', '.join(a['articles']) or '—')}</p><p><b>Obtenu :</b> {e(o.get('verdict_type') or '')} · "
                      f"démarche : {e(l.get('demarche_obtenue') or '')} · cités : "
                      f"{e(', '.join(g.get('article', '') + ('' if g.get('verifiee') else ' (citation inexacte)') for g in o.get('regles') or []) or '—')}</p>"
                      f"<p class='rep'>{e(o.get('reponse') or '')}</p>{f'<ul>{fautes}</ul>' if fautes else ''}</td></tr>")
        lignes.append(f"<tr><td class='id'>{l['id']}</td><td class='qu'>{e(l['question'])}</td>{cases}"
                      f"<td class='t'>{o.get('secondes') or '—'} s</td></tr>{detail}")
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Banc d'essai · assistant PLU</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{{--fond:#F5F0E8;--carte:#fff;--encre:#1D1A17;--gris:#8A837B;--filet:#E4DCD0;--vert:#2f9e44;--rouge:#C22E4A;--acc:#1971c2}}
*{{box-sizing:border-box;margin:0}} body{{background:var(--fond);color:var(--encre);font:400 15px/1.45 Geist,system-ui,sans-serif;padding:32px 40px 60px}}
h1{{font-size:34px;font-weight:800}} .chapo{{color:var(--gris);font-size:17px;margin:6px 0 22px;max-width:1150px}}
.tuiles{{display:grid;grid-template-columns:repeat(8,1fr);gap:10px;margin-bottom:24px}}
.tuile{{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:16px 18px;display:flex;flex-direction:column;gap:6px}}
.tuile b{{font-size:34px;font-weight:800;line-height:1}} .tuile small{{font-size:18px;color:var(--gris);font-weight:600}}
.tuile span{{color:var(--gris);font-size:14px}} .tuile i{{height:6px;border-radius:3px;background:linear-gradient(90deg,var(--vert) var(--p),var(--filet) var(--p))}}
table{{width:100%;border-collapse:collapse;background:var(--carte);border:1px solid var(--filet);border-radius:14px;overflow:hidden}}
th{{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--gris);padding:10px 8px;border-bottom:1px solid var(--filet)}}
td{{padding:8px;border-bottom:1px solid var(--filet);vertical-align:top}} td.id{{font-weight:800;width:48px}} td.qu{{max-width:560px}}
td.ok,td.ko,td.na{{text-align:center;font-weight:800;width:92px}} td.ok{{color:var(--vert)}} td.ko{{color:var(--rouge);background:#fff5f5}} td.na{{color:var(--filet)}}
td.t{{color:var(--gris);width:64px;text-align:right}} tr.detail td{{background:#fbf8f3;font-size:14px;color:var(--encre)}}
tr.detail p{{margin:2px 0}} .rep{{color:var(--gris);font-style:italic}} tr.detail ul{{color:var(--rouge);padding-left:18px}}
</style></head><body>
<h1>Banc d'essai : l'agent face à {r['questions']} vraies questions</h1>
<p class="chapo">Passage du {e(r['date'])}, K2 Horizon 7B en local, durée totale {round(r['duree_totale_s'] / 60)} min.
Chaque critère est noté par le code, pas par une IA. Les lignes en échec sont détaillées : attendu, obtenu, fautes relevées.</p>
<div class="tuiles">{tuiles}</div>
<table><tr><th>n°</th><th>question</th>{''.join(f'<th>{e(t)}</th>' for _, t in CRITERES)}<th>temps</th></tr>{''.join(lignes)}</table>
</body></html>"""
    sortie = chemin.replace(".json", ".html").replace("banc-", "rapport-banc-")
    open(sortie, "w", encoding="utf-8").write(page)
    print(sortie)


if __name__ == "__main__":
    main()
