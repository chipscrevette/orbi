"""La page du banc caché : un seul passage sur 20 questions jamais vues, comparé au banc de mise au point, avec le scellé
(empreintes des questions et du code) et le diagnostic écrit à la main après lecture des traces.
Usage : uv run python -m orbi.evaluation.pages.cache bancs/resultats/banc-cache-XXXX.json bancs/resultats/banc-MISEAUPOINT.json notes.json"""
import html
import json
import os
import sys

from orbi.evaluation.notation import renoter
from orbi.evaluation.pages.comparer import CRITERES, CSS, SOUS_TITRE
from orbi.reglement.donnees import RACINE
from orbi.chemins import JEUX  # noqa: E402


def main(cache, reference, notes):
    e = html.escape
    dc, dr = renoter(cache), renoter(reference)
    Sc, Sr = dc["resume"]["scores"], dr["resume"]["scores"]
    L = {l["id"]: l for l in dc["lignes"]}
    ok = lambda l: all(v in (True, None) for v in l["note"].values())  # noqa: E731

    def pct(s):
        return 100 * s[0] / max(1, s[1])

    tuiles = ""
    for k, titre in CRITERES:
        a, b = Sr[k], Sc[k]
        tuiles += (f"<div class='tuile'><span class='t'>{e(titre)}<em>{e(SOUS_TITRE[k])}</em></span>"
                   f"<b>{b[0]}<small>/{b[1]}</small></b>"
                   f"<div class='barre'><i class='{'ap' if pct(b) >= 80 else 're'}' style='width:{pct(b):.0f}%'></i></div>"
                   f"<span class='d'>{pct(b):.0f} % · mise au point : {a[0]}/{a[1]} ({pct(a):.0f} %)</span></div>")
    tuiles += (f"<div class='tuile'><span class='t'>Temps moyen<em>par question</em></span><b>{dc['resume']['temps_moyen_s']}<small> s</small></b>"
               f"<div class='barre'><i class='av' style='width:{min(100, 100 * dc['resume']['temps_moyen_s'] / 90):.0f}%'></i></div>"
               f"<span class='d'>max {dc['resume']['temps_max_s']} s · mise au point : {dr['resume']['temps_moyen_s']} s</span></div>")

    sceau = open(os.path.join(JEUX, "questions-cachees.sha256"), encoding="utf-8").read().strip().splitlines()
    sceau_html = (f"<p class='sous'><b>Questions :</b> <code>{e(sceau[0][:64])}</code> — {e(sceau[0][66:])}</p>"
                  f"<p class='sous'><b>Code :</b> {e(sceau[2])} — agent.py <code>{e(next(x for x in sceau if 'agent.py' in x)[:16])}…</code>, "
                  f"et 14 autres fichiers (liste complète dans <code>bancs/jeux/questions-cachees.sha256</code>).</p>")

    contresens = "".join(
        f"<div class='mort'><span class='id'>{i}</span><div><p class='q'>« {e(L[i]['question'])} »</p>"
        f"<p class='extrait'>« {e(notes['contresens'][i]['extrait'])} »</p><p>{e(notes['contresens'][i]['pourquoi'])}</p></div></div>"
        for i in notes["contresens"])
    autres = "".join(
        f"<div class='reste'><span class='id'>{i}</span><div><p class='q'>{e(L[i]['question'])}</p>"
        f"<p><b class='rate'>{e(', '.join(k for k, v in L[i]['note'].items() if v is False) or 'noté juste, faux sur le fond')}</b> · attendu « "
        f"{e(L[i]['attendu']['verdict_type'])} », obtenu « {e(L[i]['obtenu'].get('verdict_type') or 'rien')} »</p>"
        f"<p class='diag'>{e(notes['autres'][i])}</p></div></div>" for i in notes["autres"])
    tient = "".join(f"<div class='carte'><b>{e(t)}</b> {e(x)}</div>" for t, x in notes["tient"])
    suite = "".join(f"<li><b>{e(t)}</b> {e(x)}</li>" for t, x in notes["suite"])

    def case(k, l):
        v = l["note"][k]
        return "<td class='na'>—</td>" if v is None else f"<td class='{'ok' if v else 'ko'}'>{'✓' if v else '✗'}</td>"

    lignes = "".join(f"<tr><td class='id'>{i}</td><td class='qu'>{e(l['question'])}<br><small>{e(l['attendu']['verdict_type'])} attendu · "
                     f"{e(l['obtenu'].get('verdict_type') or 'rien')} obtenu</small></td>{''.join(case(k, l) for k, _ in CRITERES)}"
                     f"<td class='t'>{l['obtenu'].get('secondes') or '—'} s</td></tr>" for i, l in L.items())

    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Banc caché · assistant PLU</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&display=swap" rel="stylesheet">
<style>{CSS}
.tuile b{{font-size:40px}} code{{font-size:12px;background:#ece5da;border-radius:4px;padding:1px 4px}}
.image{{font-size:20px;font-weight:600;max-width:1100px;margin:6px 0 14px}} .image em{{color:var(--gris);font-style:normal;font-weight:400}}
.suite{{padding-left:20px;display:flex;flex-direction:column;gap:6px;font-size:15px;max-width:1150px}}
.mort .q,.reste .q{{font-weight:600}}</style></head><body>
<p class="kicker">Assistant PLU de Biarritz · banc caché · {e(dc['resume']['date'][:10])}</p>
<h1>{e(notes['titre'])}</h1>
<p class="chapo">{e(notes['chapo'])}</p>
<div class="tuiles">{tuiles}</div>
<h2>Le scellé</h2>{sceau_html}
<h2>Le défaut principal : trop permissif</h2>
<p class="image">{e(notes['image'])}</p>
<div class="morts">{contresens}</div>
<h2>Les autres échecs</h2><div class="restes">{autres}</div>
<h2>Ce qui tient sur des questions neuves</h2><div class="corr" style="grid-template-columns:repeat({len(notes['tient'])},1fr)">{tient}</div>
<h2>Ce que ça change pour la suite</h2><ul class="suite">{suite}</ul>
<h2>Question par question</h2>
<table><tr><th>n°</th><th>question</th>{''.join(f'<th>{e(t)}</th>' for _, t in CRITERES)}<th>temps</th></tr>{lignes}</table>
</body></html>"""
    sortie = cache.replace(".json", ".html")
    open(sortie, "w", encoding="utf-8").write(page)
    print(sortie)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], json.load(open(sys.argv[3], encoding="utf-8")))
