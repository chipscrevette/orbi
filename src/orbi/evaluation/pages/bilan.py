"""La page-bilan de la grille : une affiche. Le schéma (docs/schemas/grille-v1.png), les chiffres du 2e banc caché (ancien agent contre grille),
trois cas réels, et ce qui reste faux. Les chiffres viennent des fichiers de résultats, les mots des notes écrites à la main après lecture
des traces (bancs/resultats/notes-bilan-grille.json).
Usage : uv run python -m orbi.evaluation.pages.bilan GRILLE_CACHE2.json HISTORIQUE_CACHE2.json GRILLE_DEV.json HISTORIQUE_DEV.json NOTES.json"""
import html
import json
import os
import sys

from orbi.evaluation.analyse_passage import resume  # noqa: E402
from orbi.evaluation.pages.comparer import CSS  # noqa: E402
from orbi.chemins import JEUX, RESULTATS  # noqa: E402

e = html.escape

STYLE = """
.affiche{max-width:1840px;padding:20px 36px 24px}
.haut{display:flex;justify-content:space-between;align-items:flex-end;gap:30px}
.haut h1{font-size:38px;margin:2px 0 2px;max-width:none}.haut .chapo{margin:0;max-width:760px;font-size:16px}
.scel{font:12px/1.35 ui-monospace,Consolas,monospace;color:var(--gris);text-align:right;max-width:520px;overflow-wrap:anywhere}
.coeur{display:grid;grid-template-columns:1.32fr 1fr;gap:16px;margin-top:12px;align-items:stretch}
.coeur .figure{margin:0;display:flex;flex-direction:column}.coeur .figure img{height:100%;object-fit:contain;background:#fff}
.coeur .figure figcaption{margin-top:4px}
.chiffres{display:flex;flex-direction:column;gap:10px}
.groupe-t{display:flex;justify-content:space-between;align-items:baseline;color:var(--gris);font-weight:700;font-size:13px;letter-spacing:.05em;text-transform:uppercase}
.paire{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.duo-t{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:12px 16px;display:flex;flex-direction:column;gap:6px}
.duo-t .t{font-weight:700;font-size:14px;color:var(--gris)}
.ligne{display:grid;grid-template-columns:96px 1fr 70px;gap:8px;align-items:center}
.ligne span{font-size:12px;color:var(--gris);font-weight:600}.ligne b{font-size:24px;font-weight:800;text-align:right;white-space:nowrap}
.ligne b small{font-size:13px;color:var(--gris);font-weight:600}
.ligne.nouveau b{color:var(--encre)}
.barre.k2 i{background:var(--k2)}.barre.cd i{background:var(--vert)}
.rouge{color:var(--rouge)}.vert{color:var(--vert)}
.groupes{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.g{background:var(--carte);border:1px solid var(--filet);border-radius:12px;padding:9px 12px;display:flex;flex-direction:column;gap:3px}
.g .t{font-size:12px;font-weight:700;color:var(--gris)}.g .v{display:flex;justify-content:space-between;font-weight:800;font-size:17px}
.g .v span{font-size:13px;font-weight:600;color:var(--gris)}
.cas{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}
.carte-cas{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:12px 16px;display:flex;flex-direction:column;gap:6px}
.carte-cas .q{font-weight:700;font-size:15px}.carte-cas .id{color:var(--gris);font-weight:800;margin-right:6px}
.carte-cas .duo2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.carte-cas .moi{border-radius:10px;padding:8px 10px;font-size:13px;display:flex;flex-direction:column;gap:3px}
.carte-cas .moi.avant{background:#f1ede5}.carte-cas .moi.apres{background:#eef7f0}
.carte-cas .moi b.v{font-size:15px}.carte-cas .pq{font-size:13px;color:#4a443e}
.pied{display:grid;grid-template-columns:1.3fr 1fr;gap:16px;margin-top:12px}
.pied .carte{background:#1D1A17;color:#e9e3da;border-radius:14px;padding:12px 18px}.pied .carte b{color:#fff}
.pied ul{margin:4px 0 0;padding-left:0;list-style:none;display:flex;flex-direction:column;gap:3px;font-size:13.5px}
.pied .suite{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:12px 18px;font-size:14px}
@media (max-width:1100px){.coeur,.cas,.pied{grid-template-columns:1fr}.haut{flex-direction:column;align-items:flex-start}}
"""


def pct(a, b):
    return 100 * a / max(1, b)


def tuile(titre, a_av, a_ap, sur, bas_est_bien=False, sous=""):
    """Une tuile : la valeur de l'ancien agent et celle de la grille, deux barres."""
    def barre(v, cls):
        return f"<div class='barre {cls}'><i style='width:{pct(v, sur):.0f}%'></i></div>"
    return (f"<div class='duo-t'><span class='t'>{e(titre)}</span>"
            f"<div class='ligne'><span>ancien agent</span>{barre(a_av, 'av')}<b>{a_av}<small>/{sur}</small></b></div>"
            f"<div class='ligne nouveau'><span>la grille</span>{barre(a_ap, 'k2' if not bas_est_bien else 'cd')}<b>{a_ap}<small>/{sur}</small></b></div>"
            f"<span class='t' style='font-weight:500'>{e(sous)}</span></div>")


def main(g2, h2, gd, hd, notes_fichier):
    notes = json.load(open(notes_fichier, encoding="utf-8"))
    dg2, pg2, _ = resume(g2)
    dh2, ph2, _ = resume(h2)
    dgd, pgd, _ = resume(gd)
    dhd, phd, _ = resume(hd)
    G, H = pg2["TOTAL"], ph2["TOTAL"]
    n = G["n"]
    scel = open(os.path.join(JEUX, "questions-cachees-2.sha256"), encoding="utf-8").read().splitlines()

    tuiles = (tuile("Verdict exact", H["exact"], G["exact"], n, sous="le mot du verdict est celui attendu")
              + tuile("Bon sens", H["sens"], G["sens"], H["sens_n"], sous="permis, interdit ou indéterminé : le bon des trois")
              + tuile("Contresens", H["contresens"], G["contresens"], n, bas_est_bien=True, sous="« oui » là où c'est « non », ou l'inverse (0 = mieux)")
              + tuile("Trop permissif", H["permissif"], G["permissif"], n, bas_est_bien=True, sous="« oui » là où c'est interdit ou indéterminé (0 = mieux)"))
    groupes = ""
    for k, titre in (("A", "A · clairement permis"), ("B", "B · clairement interdit"), ("C", "C · information manquante"), ("D", "D · zones strictes")):
        groupes += (f"<div class='g'><span class='t'>{e(titre)}</span><div class='v'>{ph2[k]['exact']} → {pg2[k]['exact']}"
                    f"<span>sur {pg2[k]['n']}</span></div></div>")

    cas = ""
    L2 = {l["id"]: l for l in dg2["lignes"]}
    L2h = {l["id"]: l for l in dh2["lignes"]}
    for c in notes["cas"]:
        lg, lh = L2[c["id"]], L2h[c["id"]]

        def mot(l):
            ok = l["note"]["verdict"]
            return f"<b class='v {'vert' if ok else 'rouge'}'>{e(l['obtenu'].get('verdict_type') or 'rien')} {'✓' if ok else '✗'}</b>"
        cas += (f"<div class='carte-cas'><span class='q'><span class='id'>{c['id']}</span>« {e(lg['question'])} »</span>"
                f"<span class='pq'>Attendu : <b>{e(lg['attendu']['verdict_type'])}</b></span>"
                f"<div class='duo2'><div class='moi avant'><span class='t'>ancien agent</span>{mot(lh)}<span>{e(c['avant'])}</span></div>"
                f"<div class='moi apres'><span class='t'>la grille</span>{mot(lg)}<span>{e(c['apres'])}</span></div></div>"
                f"<span class='pq'>{e(c['pourquoi'])}</span></div>")
    restes = "".join(f"<li><b>{e(t)}</b> {e(x)}</li>" for t, x in notes["restes"])
    suite = "".join(f"<li><b>{e(t)}</b> {e(x)}</li>" for t, x in notes["suite"])

    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Assistant PLU · la grille</title><link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&display=swap" rel="stylesheet">
<style>{CSS}{STYLE}</style></head><body class="affiche">
<div class="haut"><div><span class="kicker">Assistant PLU · bilan de la grille · {e(notes['date'])}</span>
<h1>Le modèle lit, le code décide</h1>
<p class="chapo">{e(notes['chapo'])}</p></div>
<div class="scel">{n} questions jamais vues, scellées avant le passage<br>SHA-256 {e(scel[0][:16])}… · un seul passage par agent<br>{e(notes['sceau_code'])}</div></div>
<div class="coeur"><figure class="figure"><img src="../../docs/schemas/grille-v1.png" alt="schéma de la grille">
<figcaption>{e(notes['legende_schema'])}</figcaption></figure>
<div class="chiffres"><div class="groupe-t"><span>2e banc caché · {n} questions · ancien agent → grille</span><span>{e(notes['sous_chiffres'])}</span></div>
<div class="paire">{tuiles}</div><div class="groupes">{groupes}</div></div></div>
<div class="cas">{cas}</div>
<div class="pied"><div class="carte"><b>Ce qui reste faux, dit franchement</b><ul>{restes}</ul></div>
<div class="suite"><b>Et ensuite</b><ul style="list-style:none;padding:0;margin:4px 0 0;display:flex;flex-direction:column;gap:3px">{suite}</ul></div></div>
</body></html>"""
    sortie = os.path.join(RESULTATS, "bilan-grille.html")
    open(sortie, "w", encoding="utf-8").write(page)
    print("page :", sortie)


if __name__ == "__main__":
    main(*sys.argv[1:6])
