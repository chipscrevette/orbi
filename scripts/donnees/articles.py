"""Le règlement du PLU de Biarritz découpé par zone et par article : donnees/articles.json.
C'est aussi le découpage que le RAG utilisera (une citation = un article exact, avec ses pages)."""
import json, os, re

from orbi.chemins import DONNEES

pages = json.load(open(os.path.join(DONNEES, "pages.json"), encoding="utf-8"))
ENTETE = re.compile(r"P\.L\.U\. DE BIARRITZ appr\. le 22/12/2003 – Modification n°13 appr\. le 23/03/2024\s*(ZONE\s+\S+\s+)?\d*")
CHAPITRES = [("DG", 4), ("UA", 17), ("UB", 35), ("UC", 51), ("UD", 64), ("UG", 77), ("UH", 89), ("UP", 100),
             ("UY", 109), ("IIAU", 124), ("N", 131), ("Ncu", 141), ("Ner", 147)]
texte, debut_page = "", []
for p, t in pages:
    debut_page.append((len(texte), p))
    texte += " " + ENTETE.sub(" ", t)
texte = re.sub(r"[ \t]+", " ", texte)


def page_de(pos):
    return max(p for d, p in debut_page if d <= pos)


out = {}
for k, (zone, p0) in enumerate(CHAPITRES):
    d = next(d for d, p in debut_page if p == p0)
    f = next(d for d, p in debut_page if p == CHAPITRES[k + 1][1]) if k + 1 < len(CHAPITRES) else len(texte)
    bloc = texte[d:f]
    if zone == "DG":
        out[zone] = {"0": {"titre": "Dispositions générales", "pages": [4, 16], "texte": " ".join(bloc.split())}}
        # les dispositions générales ont leurs propres articles : A-I, A-V… B-5 (emprise), B-8 (clôtures), B-16 (biotope)
        motif_dg = re.compile(r"ARTICLE\s+([A-Z])\s*-\s*([IVX]+|\d+)\s*[-–]\s*")
        rep = list(motif_dg.finditer(bloc))
        for i, m in enumerate(rep):
            fin_a = rep[i + 1].start() if i + 1 < len(rep) else len(bloc)
            corps = " ".join(bloc[m.end():fin_a].split())
            out[zone][f"{m.group(1)}-{m.group(2)}"] = {"titre": corps[:80], "pages": [page_de(d + m.start()), page_de(d + fin_a - 1)],
                                                       "texte": corps}
        continue
    arts = {}
    motif = re.compile(r"ARTICLE\s+(?:[0-9IV]*[A-Z][A-Za-z]{0,3})\s*(\d{1,2})\s*[-–]\s*")
    reperes = list(motif.finditer(bloc))
    for i, m in enumerate(reperes):
        fin = reperes[i + 1].start() if i + 1 < len(reperes) else len(bloc)
        corps = " ".join(bloc[m.end():fin].split())
        titre = corps[:90].split("  ")[0]
        n = m.group(1)
        if n in arts:  # un renvoi « article UA 11 » au milieu d'un texte : on garde le vrai titre (le premier)
            arts[n]["texte"] += " " + " ".join(bloc[m.start():fin].split())
            continue
        arts[n] = {"titre": titre, "pages": [page_de(d + m.start()), page_de(d + fin - 1)], "texte": corps}
    out[zone] = arts
json.dump(out, open(os.path.join(DONNEES, "articles.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for z, arts in out.items():
    print(z, len(arts), "articles :", ", ".join(f"{n} (p.{a['pages'][0]})" for n, a in sorted(arts.items(), key=lambda x: (not x[0].isdigit(), int(x[0]) if x[0].isdigit() else 0, x[0]))))
