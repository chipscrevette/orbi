"""Banc d'essai v2 : de VRAIES questions trouvées en ligne (forums, FAQ de mairies, experts), transposées sur de vraies
adresses de Biarritz. Chaque réponse attendue = la démarche (Code de l'urbanisme) + les règles du PLU (citations
vérifiées par le code, à leur page) + ce qu'il faut vérifier en mairie.
Sorties : bancs/jeux/questions-reelles.json (le catalogue), bancs/jeux/questions-v2.json et questions-v2.html."""
import html, json, os
from _socle_banc import ARTICLES, B, C, EMPRISE_DG, SPR, r

# ---------------------------------------------------------------- les textes de loi (Légifrance)
LOI = {
    "R421-2": ("Sont dispensées de toute formalité [...] sauf lorsqu'ils sont implantés dans le périmètre d'un site "
               "patrimonial remarquable", "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000050497056"),
    "R421-9": ("constructions de 5 à 20 m² : déclaration préalable ; piscines dont le bassin fait 100 m² au plus, non "
               "couvertes ou couvertes à moins de 1,80 m : déclaration préalable",
               "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037799137/"),
    "R421-11": ("en site patrimonial remarquable, les petites constructions (jusqu'à 20 m²) sont soumises à déclaration "
                "préalable, sans le seuil de 5 m²", "https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006074075/LEGISCTA000006188272/"),
    "R421-12": ("clôtures soumises à déclaration préalable en site patrimonial remarquable, aux abords d'un monument "
                "historique, en site classé ou si la commune l'a décidé",
                "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000034355392"),
    "R421-14": ("agrandissement en zone urbaine d'un PLU : déclaration préalable jusqu'à 40 m², permis au-delà, ou dès "
                "20 m² si la maison dépasse 150 m² après travaux", "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031764577"),
    "L421-8": ("un projet dispensé de formalité doit quand même respecter les règles d'urbanisme (le PLU)",
               "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049398814"),
    "R431-2": ("architecte obligatoire quand la surface dépasse 150 m² après travaux",
               "https://www.cauegironde.com/Ma-maison-fait-plus-de-150-m-et-je-veux-faire-une-extension-dois-je-recourir-a-un-architecte/"),
    "délais": ("déclaration préalable : 1 mois, 2 mois en site patrimonial remarquable (avis de l'ABF)",
               "https://www.culture.gouv.fr/catalogue-des-demarches-et-subventions/mes-travaux-en-site-protege/foire-aux-questions"),
}


def loi(*cles):
    return [{"texte": k, "dit": LOI[k][0], "url": LOI[k][1]} for k in cles]


# ---------------------------------------------------------------- les vraies questions trouvées en ligne
SOURCES = {
    "fp24": ("ForumPiscine, 9 oct. 2024", "https://www.forumpiscine.com/forum/t32502-refus-declaration-prealable-plu.php"),
    "ccm-abri": ("CommentCaMarche (forum droit)", "https://droit-finances.commentcamarche.com/forum/affich-4909524-abris-de-jardin"),
    "fc-emprise": ("Forum Construire", "https://www.forumconstruire.com/construire/topic-388828-emprise-sol-rapport-surface-terrain.php"),
    "ccm-piscine": ("CommentCaMarche, 3 nov. 2016", "https://droit-finances.commentcamarche.com/forum/affich-7311710-piscine-et-limite-separative"),
    "fp15": ("ForumPiscine, 11 oct. 2015", "https://www.forumpiscine.com/forum/t10618-mini-piscine-10m-max-et-distance-voisinage.php"),
    "alexia-abri": ("Alexia (question à un avocat)", "https://www.alexia.fr/questions/507259/limites-separatives-abri-de-jardin.htm"),
    "alexia-veranda": ("Alexia (question à un avocat)", "https://www.alexia.fr/questions/412385/projet-de-creation-de-veranda-refuse-hors-le-plu-le-permet.htm"),
    "alexia-conforme": ("Alexia (question à un avocat)", "https://www.alexia.fr/questions/267070/construction-d-une-veranda-mais-qui-ne-respecte-pas-la-plu.htm"),
    "fc-toit": ("Forum Construire, 13 janv. 2015", "https://www.forumconstruire.com/construire/topic-270827-avis-sur-faisabilite-elevation-de-toiture-.php"),
    "fc-brisevue": ("Forum Construire, 2015-2017", "https://www.forumconstruire.com/construire/topic-288055-reglementation-sur-la-pose-de-brise-vue.php"),
    "alexia-voisin": ("Alexia (question à un avocat)", "https://www.alexia.fr/questions/506635/plu-et-voisin.htm"),
    "faq-bressuire": ("FAQ de la mairie de Bressuire", "https://www.ville-bressuire.fr/foire-aux-questions/"),
    "caue33": ("CAUE de la Gironde (FAQ)", "https://www.cauegironde.com/Ma-maison-fait-plus-de-150-m-et-je-veux-faire-une-extension-dois-je-recourir-a-un-architecte/"),
    "anil": ("ANIL, la parole de l'expert", "https://www.anil.org/parole-expert-logement-urbanisme-installation-abri-jardin/"),
}
# (source, question paraphrasée, projet, point de vue, nature)
REELLES = [
    ("fp24", "Terrain de 530 m², emprise limitée à 30 % soit 159 m² ; maison 155 m² + piscine 28 m² = 183 m² : ma déclaration est refusée, que faire ?", "piscine", "propriétaire", "règle"),
    ("fp24", "Peut-on demander une dérogation à la mairie quand on dépasse l'emprise ?", "piscine", "propriétaire", "hors périmètre"),
    ("fp24", "Une piscine de moins de 10 m², sans aucune demande, permettrait-elle de contourner le dépassement ?", "piscine", "propriétaire", "démarche"),
    ("fp24", "Une noue paysagère peut-elle compenser l'emprise de la piscine ?", "piscine", "propriétaire", "règle"),
    ("fp24", "La règle des éléments de moins de 60 cm non comptés dans l'emprise s'applique-t-elle aux piscines ?", "piscine", "propriétaire", "définition"),
    ("ccm-abri", "Mon voisin a mis un abri de moins de 20 m² à 1 m de la clôture, il bouche ma baie vitrée : est-ce légal, quels recours ?", "abri de jardin", "voisin", "règle"),
    ("ccm-abri", "Combien d'abris peut-on construire si aucun ne dépasse la limite de surface ?", "abri de jardin", "propriétaire", "règle"),
    ("ccm-abri", "Un abri à bois de moins de 1,80 m : quelles règles ?", "abri de jardin", "propriétaire", "démarche"),
    ("ccm-abri", "Plusieurs abris : sont-ils taxés ?", "abri de jardin", "propriétaire", "hors périmètre"),
    ("fc-emprise", "954 m² de terrain dont 366 constructibles, emprise 40 % : 40 % de quoi ?", "extension", "propriétaire", "définition"),
    ("fc-emprise", "Les parties enterrées et les patios non couverts comptent-ils dans l'emprise ?", "extension", "propriétaire", "définition"),
    ("fc-emprise", "Le règlement du lotissement peut-il calculer l'emprise sur le terrain avant division ?", "extension", "propriétaire", "hors périmètre"),
    ("fc-emprise", "PLU et règlement de lotissement disent des choses différentes : lequel s'applique ?", "extension", "propriétaire", "règle"),
    ("ccm-piscine", "Piscine refusée : le bord est à 3,5 m de la limite au lieu de 4 m ; la margelle compte-t-elle ?", "piscine", "propriétaire", "règle"),
    ("ccm-piscine", "Piscine en L, petite partie en limite avec l'accord du voisin : faut-il 4 m pour la grande longueur ?", "piscine", "propriétaire", "règle"),
    ("ccm-piscine", "La mairie impose « 4 mètres ou 0 » : qu'est-ce que ça veut dire ?", "piscine", "propriétaire", "définition"),
    ("fp15", "Une mini-piscine de 4 x 2 m, semi-enterrée ou hors sol, doit-elle être à 3 m de la limite ?", "piscine", "propriétaire", "règle"),
    ("fp15", "Si je la colle contre le mur de séparation, est-ce conforme au PLU ?", "piscine", "propriétaire", "règle"),
    ("fp15", "Que veut dire « limite voisinage » dans le PLU ?", "piscine", "propriétaire", "définition"),
    ("alexia-abri", "Abri de 7 m² : la mairie exige 2 m de retrait des limites alors que le PLU a une exception pour les abris de moins de 8 m² : laquelle s'applique ?", "abri de jardin", "propriétaire", "règle"),
    ("alexia-veranda", "Véranda de 25 m² : la mairie parle de 8 m de la limite alors que le PLU dirait 4,36 m : la mairie peut-elle être plus stricte que le PLU ?", "véranda", "propriétaire", "règle"),
    ("alexia-conforme", "Véranda de moins de 20 m² construite après déclaration, à 3 m au lieu des 4 m du PLU : la mairie peut-elle contester ?", "véranda", "propriétaire", "hors périmètre"),
    ("fc-toit", "Mes murs sont à 2 m des limites et le PLU exige 3 m : puis-je rehausser la toiture de 60 cm ?", "surélévation", "propriétaire", "règle"),
    ("fc-toit", "Surélévation refusée faute d'une place de stationnement en plus : peut-on obtenir une dérogation ?", "surélévation", "propriétaire", "règle"),
    ("fc-brisevue", "Un brise-vue de 2 m sur un grillage mitoyen de 1 m, sans l'accord du voisin : possible ?", "clôture", "propriétaire", "règle"),
    ("fc-brisevue", "Un brise-vue à 1,5 m de la clôture, de 1,80 m à 3 m de haut : autorisé ?", "clôture", "propriétaire", "règle"),
    ("alexia-voisin", "Brise-vue de 2,60 m légèrement en retrait de la clôture alors que le PLU limite à 2 m ; le voisin porte plainte : est-ce une clôture ?", "clôture", "propriétaire", "règle"),
    ("alexia-voisin", "L'extension du voisin, en parpaings nus avec un toit en bac acier, ne respecte pas le PLU : que faire ?", "extension", "voisin", "règle"),
    ("faq-bressuire", "Quelles autorisations pour une piscine hors-sol ?", "piscine", "propriétaire", "démarche"),
    ("faq-bressuire", "Quelles autorisations pour modifier ou installer une clôture ?", "clôture", "propriétaire", "démarche"),
    ("faq-bressuire", "Quelles autorisations pour installer un abri de jardin ?", "abri de jardin", "propriétaire", "démarche"),
    ("faq-bressuire", "Quelles autorisations pour agrandir une maison ou construire une véranda ?", "extension", "propriétaire", "démarche"),
    ("faq-bressuire", "Quelles autorisations pour construire un garage ?", "autre", "propriétaire", "hors périmètre"),
    ("faq-bressuire", "Quels sont les délais d'instruction des dossiers ?", "tous", "propriétaire", "démarche"),
    ("faq-bressuire", "Comment savoir si un bâtiment est protégé ?", "tous", "propriétaire", "règle"),
    ("faq-bressuire", "Quelle différence entre surface de plancher et emprise au sol ?", "tous", "propriétaire", "définition"),
    ("faq-bressuire", "Changer les fenêtres, refaire le toit, poser des panneaux solaires : quelles autorisations ?", "autre", "propriétaire", "hors périmètre"),
    ("caue33", "Ma maison fait plus de 150 m² et je veux une extension : dois-je recourir à un architecte ?", "extension", "propriétaire", "démarche"),
    ("anil", "Faut-il une autorisation pour un abri de jardin, et est-il soumis à la taxe d'aménagement ?", "abri de jardin", "propriétaire", "démarche"),
]
json.dump([{"id": f"R{k:02d}", "source": SOURCES[s][0], "url": SOURCES[s][1], "question": q, "projet": p, "point_de_vue": v,
            "nature": n} for k, (s, q, p, v, n) in enumerate(REELLES, 1)],
          open(os.path.join(B, "questions-reelles.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- le banc v2
A = {"castellamare": "6 Rue Castellamare 64200 Biarritz", "dartiguelongue": "3 Rue Pierre Dartiguelongue 64200 Biarritz",
     "moura": "9 Allée du Moura 64200 Biarritz", "verdun": "96 Avenue de Verdun 64200 Biarritz",
     "etienne": "2 Avenue d'Etienne 64200 Biarritz", "mairie": "12 Avenue Edouard VII 64200 Biarritz",
     "bergerie": "2 Rue de la Bergerie 64200 Biarritz", "moura37": "37 Allée du Moura 64200 Biarritz",
     "chabiague": "14 Rue du Moulin de Chabiague 64200 Biarritz", "dorziat": "Allée Gabrielle Dorziat 64200 Biarritz",
     "anglet": "Rue Marie Blanque 64600 Anglet"}
UD7 = r("UD 7", "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci",
        "sur la limite, ou à 3 m au moins ; et plus on est haut, plus il faut s'écarter (D ≥ h − 3)")
UD7_PISCINE = r("UD 7", "Les piscines, spas et jacuzzis sont exclus de cette règle", "la règle des distances ne s'applique pas aux piscines")
UD9_25 = r("UD 9", "L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa",
           "25 % de la parcelle en UDa (40 % pour une parcelle de moins de 1 000 m² existant avant 2003), 250 m² au plus")
UC9 = r("UC 9", "l'emprise au sol maximale est fixée à 70 % de l'unité foncière", "emprise au sol maximale : 70 %")
DG_TOUT = r("DG B-5", "L’ensemble des constructions sur l’unité foncière est comptabilisé dans l’emprise au sol",
            "tous les bâtiments de la parcelle comptent dans l'emprise")
Q = []


def q(n, src, question, adresse, projet, vue, nature, verdict, demarche, regles, lois, verifier, piege, faits=None):
    c = C.get(adresse, {})
    f = faits or {"zone": (c.get("zone") or ["?"])[0], "parcelle": c.get("parcelle"), "surface_m2": c.get("surface_m2"),
                  "contraintes": [x for x in c.get("prescriptions", []) + c.get("servitudes", [])
                                  if x not in ("UA", "UB", "UBa", "UC", "UD", "UDa", "UH")
                                  and not x.startswith("Majoration des volumes")]}
    reelle = src in SOURCES
    Q.append({"id": f"V{n:02d}", "origine": "vraie question" if reelle else "cas de zone",
              "source": {"nom": SOURCES[src][0], "url": SOURCES[src][1]} if reelle else None,
              "question": question, "adresse": adresse, "projet": projet, "point_de_vue": vue, "nature": nature,
              "faits": f, "attendu": {"verdict": verdict, "demarche": demarche, "regles": regles, "loi": lois,
                                      "a_verifier": verifier}, "piege": piege})


# --- piscines
q(1, "fp24", "J'ai 342 m² de terrain au 3 rue Pierre Dartiguelongue et ma maison fait déjà 80 m² d'emprise. "
  "Si j'ajoute une piscine non couverte de 28 m², est-ce que je dépasse l'emprise autorisée ?",
  A["dartiguelongue"], "piscine", "propriétaire", "règle",
  "non : une piscine non couverte ne compte pas ; l'emprise reste à 80 m² sur 85,5 m² autorisés", "déclaration préalable",
  [EMPRISE_DG, UD9_25], loi("R421-9"), ["que la maison fait bien 80 m² d'emprise"],
  "compter la piscine dans l'emprise, comme dans la commune de la question d'origine")
q(2, "fp24", "Si je fais une piscine de moins de 10 m² au 6 rue Castellamare, je n'ai rien à déclarer, donc le PLU ne "
  "s'applique pas ?", A["castellamare"], "piscine", "propriétaire", "démarche",
  "non : même dispensée, elle doit respecter le PLU ; et ici, en site patrimonial, la dispense ne joue pas",
  "déclaration préalable (site patrimonial remarquable)", [EMPRISE_DG], loi("L421-8", "R421-2"), [SPR],
  "croire que « sans formalité » veut dire « sans règle » ; oublier le site patrimonial")
q(3, "ccm-piscine", "Ma future piscine serait à 1,5 m de la limite du voisin, au 6 rue Castellamare : la mairie peut-elle "
  "refuser pour la distance ?", A["castellamare"], "piscine", "propriétaire", "règle",
  "non pour la distance : en UD, les piscines sont exclues de la règle des limites séparatives",
  "déclaration préalable jusqu'à 100 m² de bassin, sans dispense en site patrimonial ; permis au-delà (surface non donnée)",
  [UD7_PISCINE], loi("R421-9", "R421-2"), [SPR],
  "appliquer 3 ou 4 m comme dans la commune de la question d'origine")
q(4, "fp15", "Une petite piscine hors sol de 8 m² collée au mur du voisin, au 3 rue Pierre Dartiguelongue : c'est conforme ?",
  A["dartiguelongue"], "piscine", "propriétaire", "règle",
  "oui pour la distance (piscines exclues de l'article UD 7) ; aucune formalité sous 10 m² ici, mais le PLU s'applique",
  "aucune formalité (hors secteur protégé)", [UD7_PISCINE], loi("R421-2", "L421-8"), [],
  "exiger 3 m ; oublier que le PLU s'applique même sans formalité")
# --- abris de jardin
q(5, "alexia-abri", "Je veux un abri de jardin de 7 m² au 3 rue Pierre Dartiguelongue : à quelle distance de la limite "
  "dois-je le mettre ?", A["dartiguelongue"], "abri de jardin", "propriétaire", "règle",
  "sur la limite, ou à 3 m au moins ; entre les deux, non", "déclaration préalable (5 à 20 m²)", [UD7], loi("R421-9"), [],
  "reprendre l'exception « abris de moins de 8 m² » d'une autre commune")
q(6, "ccm-abri", "Mon voisin a installé un abri de 15 m² à 1 m de notre limite, au 6 rue Castellamare : a-t-il le droit ?",
  A["castellamare"], "abri de jardin", "voisin", "règle",
  "a priori non : en UD, une construction doit être sur la limite ou à 3 m au moins, sauf exceptions (adossement à une façade aveugle)",
  "il lui fallait une déclaration préalable (5 à 20 m², site patrimonial)", [UD7], loi("R421-9", "R421-11"),
  ["s'il a obtenu une autorisation", "les recours : hors périmètre (mairie, conciliateur)"],
  "répondre « tout abri de moins de 20 m² est libre »")
q(7, "ccm-abri", "Puis-je faire deux abris de 9 m² chacun au 3 rue Pierre Dartiguelongue ?", A["dartiguelongue"],
  "abri de jardin", "propriétaire", "règle",
  "oui si l'emprise totale de la parcelle reste sous 85,5 m² : tous les bâtiments comptent",
  "une déclaration préalable par abri (5 à 20 m²)", [DG_TOUT, UD9_25], loi("R421-9"), ["l'emprise des constructions existantes"],
  "croire que chaque abri de moins de 20 m² échappe aux règles")
# --- définitions
q(8, "fc-emprise", "L'emprise de 25 % au 3 rue Pierre Dartiguelongue, c'est 25 % de quoi exactement ?", A["dartiguelongue"],
  "extension", "propriétaire", "définition",
  "de la surface de la parcelle (l'unité foncière) : 25 % de 342 m² = 85,5 m², tous bâtiments compris", "sans objet",
  [UD9_25, DG_TOUT], [], [], "calculer sur la surface constructible ou sur la surface de la maison")
q(9, "fc-emprise", "Une cave enterrée ou une terrasse de plain-pied comptent-elles dans l'emprise au sol, au 9 allée du Moura ?",
  A["moura"], "extension", "propriétaire", "définition",
  "très probablement non : à Biarritz, l'emprise se mesure « à 0,60 m du sol naturel » ; formulation à faire confirmer par la mairie",
  "sans objet", [r("DG B-5", "prise à 0,60 m du sol naturel avant travaux", "l'emprise se mesure à 0,60 m au-dessus du sol naturel")],
  [], ["l'interprétation exacte de la mairie"], "affirmer avec certitude alors que le texte est ambigu")
q(10, "faq-bressuire", "Quelle est la différence entre la surface de plancher et l'emprise au sol ?", A["moura"], "tous",
  "propriétaire", "définition",
  "l'emprise est la trace du bâtiment au sol (tous bâtiments, hors piscines non couvertes) ; la surface de plancher compte "
  "les étages fermés et couverts, sous plus de 1,80 m de plafond", "sans objet",
  [r("DG B-5", "L’emprise au sol correspond à la projection verticale de la surface hors-œuvre", "définition de l'emprise"),
   r("UC 10", "Un niveau est déterminé par un volume dont au moins une partie a un", "un niveau compte à partir de 1,80 m de hauteur")],
  [], [], "confondre les deux")
# --- extensions, vérandas, démarches
q(11, "faq-bressuire", "Quelle autorisation pour une véranda de 30 m² au 9 allée du Moura ?", A["moura"], "véranda",
  "propriétaire", "démarche", "une déclaration préalable, sauf si la maison dépasse 150 m² après travaux (alors permis)",
  "déclaration préalable (zone urbaine : jusqu'à 40 m²)", [UC9], loi("R421-14"), ["la surface totale de la maison après travaux"],
  "appliquer le seuil de 20 m² au lieu de 40 m² en zone urbaine")
q(12, "caue33", "Ma maison fait 140 m² et je veux une extension de 30 m² au 9 allée du Moura : faut-il un architecte ?",
  A["moura"], "extension", "propriétaire", "démarche",
  "oui : 170 m² après travaux, donc permis de construire et architecte obligatoire", "permis de construire + architecte",
  [UC9], loi("R421-14", "R431-2"), [], "s'arrêter au seuil de 40 m² sans voir celui de 150 m²")
q(13, "alexia-veranda", "Pour ma véranda de 25 m² au 3 rue Pierre Dartiguelongue, à quelle distance de la limite du voisin "
  "dois-je être ?", A["dartiguelongue"], "véranda", "propriétaire", "règle",
  "sur la limite ou à 3 m au moins ; plus la véranda est haute, plus il faut s'écarter (D ≥ h − 3)",
  "déclaration préalable (zone urbaine : jusqu'à 40 m²)", [UD7, UD9_25], loi("R421-14"), ["l'emprise existante"],
  "donner une distance d'une autre commune")
# --- surélévations
q(14, "fc-toit", "Mes murs sont à 2 m de la limite et je veux rehausser le toit de 60 cm au 3 rue Pierre Dartiguelongue : "
  "c'est possible ?", A["dartiguelongue"], "surélévation", "propriétaire", "règle",
  "impossible à dire sans la mairie : le mur est déjà à moins des 3 m de l'article UD 7 ; la hauteur doit rester sous "
  "R+1+comble, 6 m à l'égout, 9,50 m au faîtage", "au moins une déclaration préalable (aspect extérieur modifié)",
  [UD7, r("UD 10", "R + 1 + comble (2 niveaux + combles)", "R+1+comble, 6 m à l'égout, 9,50 m au faîtage en UDa")], [],
  ["comment la mairie traite un bâtiment existant déjà trop près de la limite"],
  "répondre oui ou non de façon catégorique")
q(15, "fc-toit", "On me dit qu'il faut une place de parking de plus pour ma surélévation au 3 rue Pierre Dartiguelongue : "
  "c'est dans le PLU ?", A["dartiguelongue"], "surélévation", "propriétaire", "règle",
  "seulement si la surélévation crée un besoin nouveau (par exemple un logement de plus)", "sans objet",
  [r("UD 12", "il ne sera exigé de places de stationnement que pour les besoins nouveaux engendrés par les projets",
     "pour une extension, seules les places des besoins nouveaux sont exigées")], [],
  ["le nombre de places exigé par logement (article UD 12)"], "exiger des places pour tout agrandissement")
# --- clôtures
q(16, "alexia-voisin", "Je veux poser un brise-vue de 2,60 m un peu en retrait de ma clôture, au 6 rue Castellamare : "
  "c'est permis ?", A["castellamare"], "clôture", "propriétaire", "règle",
  "impossible à dire avec certitude : en limite, une clôture fait 2 m au plus ; en retrait, la mairie peut la traiter comme une clôture",
  "déclaration préalable (clôture en site patrimonial remarquable)",
  [r("UD 11", "clôtures en limites séparatives : La hauteur de la clôture ne peut excéder 2,00 mètres", "en limite séparative : 2 m au plus")],
  loi("R421-12"), [SPR, "si l'écran en retrait est considéré comme une clôture"], "répondre simplement oui ou non")
q(17, "faq-bressuire", "Faut-il une autorisation pour refaire ma clôture au 96 avenue de Verdun ?", A["verdun"], "clôture",
  "propriétaire", "démarche", "oui : une déclaration préalable, parce que la parcelle est en site patrimonial remarquable",
  "déclaration préalable",
  [r("UB 11", "e-2 - clôtures sur l'espace public : La hauteur totale des clôtures ne peut excéder 2 mètres", "sur la rue : 2 m au plus")],
  loi("R421-12"), [SPR], "répondre « les clôtures sont libres »")
# --- le voisin et les matériaux
q(18, "alexia-voisin", "Mon voisin a fait une extension en parpaings non enduits avec un toit en bac acier, au 2 avenue "
  "d'Etienne : est-ce autorisé ?", A["etienne"], "extension", "voisin", "règle",
  "non : les parpaings laissés nus et le bac acier en toiture en pente sont interdits en UB (sauf photovoltaïque, commerce ou industrie)",
  "sans objet (question sur un projet existant)",
  [r("UB 11", "l'emploi à nu des matériaux fabriqués en vue d'être recouverts d'un enduit",
     "parpaings nus et couverture en bac acier interdits")], [],
  ["les recours : hors périmètre (mairie, conciliateur)"], "ne regarder que la surface et oublier l'aspect extérieur")
# --- protections, délais
q(19, "faq-bressuire", "Comment savoir si la maison du 12 avenue Édouard VII est protégée ?", A["mairie"], "tous",
  "propriétaire", "règle",
  "elle l'est deux fois : « règles architecturales particulières » au plan (article UA 11) et site patrimonial remarquable",
  "sans objet", [r("UA 11", "ajouts ou excroissances, vérandas etc... pourront être interdites",
                   "un bâtiment repéré au plan a des règles d'aspect particulières")], [], [SPR],
  "ne pas interroger le Géoportail", faits={"zone": "UAs", "parcelle": "BA 0008", "surface_m2": 1472,
                                            "contraintes": ["Règles architecturales particulières (cf. Art. 11)", "Site patrimonial remarquable de Biarritz"]})
q(20, "faq-bressuire", "Combien de temps la mairie met-elle à répondre pour une véranda de 20 m² au 12 avenue Édouard VII ?",
  A["mairie"], "véranda", "propriétaire", "démarche",
  "2 mois : une déclaration préalable prend 1 mois, un de plus en site patrimonial remarquable (avis de l'ABF)",
  "déclaration préalable", [], loi("délais"), [], "donner 1 mois sans voir le site patrimonial",
  faits={"zone": "UAs", "parcelle": "BA 0008", "surface_m2": 1472, "contraintes": ["Site patrimonial remarquable de Biarritz"]})
# --- hors périmètre, réels
q(21, "fp24", "Mon extension dépasse de 6 m² l'emprise autorisée au 3 rue Pierre Dartiguelongue : la mairie peut-elle "
  "m'accorder une dérogation ?", A["dartiguelongue"], "extension", "propriétaire", "hors périmètre",
  "hors périmètre : l'assistant ne peut pas le promettre ; la loi ne prévoit que des « adaptations mineures », c'est la mairie qui décide",
  "sans objet", [UD9_25], [], ["le service urbanisme de la mairie"], "promettre une dérogation")
q(22, "anil", "Mon abri de jardin de 12 m² au 3 rue Pierre Dartiguelongue sera-t-il taxé ?", A["dartiguelongue"],
  "abri de jardin", "propriétaire", "hors périmètre",
  "hors périmètre : la taxe d'aménagement relève des impôts, pas du PLU ; la démarche, elle, est une déclaration préalable",
  "déclaration préalable (5 à 20 m²)", [], loi("R421-9"), ["les impôts (taxe d'aménagement)"], "inventer un montant")
q(23, "fc-emprise", "Mon lotissement a son propre règlement, au 6 rue Castellamare : lequel s'applique, lui ou le PLU ?",
  A["castellamare"], "extension", "propriétaire", "règle",
  "en principe la règle la plus stricte : le PLU s'il est plus restrictif, sinon celle du lotissement si elle est encore en vigueur",
  "sans objet", [r("DG A-I", "Si les dispositions du P.L.U. sont plus restrictives que celles d'un lotissement approuvé",
                   "le PLU s'applique s'il est plus restrictif ; sinon, les règles plus strictes du lotissement restent applicables")],
  [], ["le règlement du lotissement et s'il est toujours en vigueur"], "ignorer le lotissement ou l'appliquer seul")
q(24, "alexia-conforme", "J'ai construit ma véranda à 2 m de la limite au lieu de 3, au 3 rue Pierre Dartiguelongue : la "
  "mairie peut-elle m'obliger à démolir ?", A["dartiguelongue"], "véranda", "propriétaire", "hors périmètre",
  "hors périmètre : c'est une question de contentieux (avocat, mairie) ; la règle, elle, est sur la limite ou à 3 m au moins",
  "sans objet", [UD7], [], ["un avocat ou le service urbanisme"], "répondre sur les sanctions")
# --- cas de zone (construits pour couvrir les zones du PLU)
q(25, "", "Puis-je construire une véranda de 20 m² à la mairie de Biarritz, 12 avenue Édouard VII ?", A["mairie"], "véranda",
  "propriétaire", "règle", "oui sous conditions, avec un vrai risque de refus",
  "déclaration préalable (2 mois en site patrimonial remarquable)",
  [r("UA 9", "Il n'est pas fixé d'emprise au sol sauf en UAc", "aucune emprise maximale en UAs"),
   r("UA 11", "ajouts ou excroissances, vérandas etc... pourront être interdites", "sur un bâtiment repéré, une véranda peut être interdite")],
  loi("R421-14", "délais"), [SPR], "appliquer une limite d'emprise qui ne vaut qu'en UAc",
  faits={"zone": "UAs", "parcelle": "BA 0008", "surface_m2": 1472,
         "contraintes": ["Règles architecturales particulières (cf. Art. 11)", "Site patrimonial remarquable de Biarritz"]})
q(26, "", "Je veux surélever d'un étage le bâtiment du 2 rue de la Bergerie à Biarritz. C'est possible ?", A["bergerie"],
  "surélévation", "propriétaire", "règle", "impossible à dire sans savoir où est le bâtiment : le plan fixe deux hauteurs sur la parcelle",
  "permis de construire si plus de 40 m² sont créés, sinon déclaration préalable",
  [r("UA 10", "La hauteur des constructions est fixée par le plan de P.L.U., au 1/2000è ci-annexé",
     "niveaux « 3 » (12,50 m à l'égout, R+3+comble) et « 5 » (18 m, R+5+comble) sur cette parcelle")],
  loi("R421-14"), ["la hauteur actuelle et la position du bâtiment", SPR], "donner une seule hauteur")
q(27, "", "Puis-je construire une maison individuelle au 37 allée du Moura, à Biarritz ?", A["moura37"], "maison neuve",
  "propriétaire", "règle", "non : l'habitation est interdite en UG, sauf extension de l'existant ou logement lié à l'équipement",
  "sans objet", [r("UG 1", "les constructions destinées à l’habitation", "habitation interdite en UG")], [],
  ["l'emplacement réservé pour l'élargissement de la rue du Moura"], "répondre oui parce que la parcelle est grande")
q(28, "", "Puis-je poser un abri de jardin au 14 rue du Moulin de Chabiague, à Biarritz ?", A["chabiague"], "abri de jardin",
  "propriétaire", "règle", "impossible à dire sans savoir si une construction existait en mars 1995 : en zone N tout "
  "est interdit, sauf (N 2 b) les annexes des constructions existant à la révision du P.O.S. de 1995",
  "déclaration préalable jusqu'à 20 m², même sous 5 m² (site patrimonial remarquable) ; permis au-delà (surface non donnée)",
  [r("N 1", "Tous les types d'occupation ou d'utilisation des sols sont interdits", "en zone N, tout est interdit sauf exceptions"),
   r("N 2", "l'extension, aménagement, les annexes des constructions existantes à la date d'approbation de la révision du P.O.S. de mars 1995",
     "annexes admises seulement pour une construction existante en 1995")],
  loi("R421-11"), ["s'il existe une construction de 1995 ou avant", SPR], "raisonner comme en zone urbaine")
q(29, "", "Puis-je construire une maison allée Gabrielle Dorziat (parcelle CA 0044), à Biarritz ?", A["dorziat"],
  "maison neuve", "propriétaire", "règle", "non : en Ncu, une construction neuve n'est admise que pour la sécurité, un service public ou le confortement de l'existant",
  "sans objet", [r("Ncu 1", "Toutes constructions qui ne seraient pas justifiées par la sécurité", "constructions neuves interdites en Ncu")],
  [], ["espace boisé classé et espace vert protégé", SPR], "confondre Ncu et Nh")
q(30, "", "Puis-je construire une véranda rue Marie Blanque à Anglet ?", A["anglet"], "véranda", "propriétaire",
  "hors périmètre", "hors périmètre : la v1 ne couvre que Biarritz", "sans objet", [], [],
  ["le PLU d'Anglet auprès de la mairie"], "répondre avec le règlement de Biarritz", faits={"zone": "hors Biarritz (commune 64024)"})

# ce que la notation automatique compare : un type de verdict et un type de démarche (valeurs fermées)
TYPES = {  # id : (verdict, démarche)
    1: ("oui", "déclaration préalable"), 2: ("oui sous conditions", "déclaration préalable"),
    3: ("oui sous conditions", "dépend de la surface du bassin"), 4: ("oui", "aucune formalité"),
    5: ("oui sous conditions", "déclaration préalable"), 6: ("non", "déclaration préalable"),
    7: ("oui sous conditions", "déclaration préalable"), 8: ("information", "sans objet"), 9: ("information", "sans objet"),
    10: ("information", "sans objet"), 11: ("oui sous conditions", "déclaration préalable"),
    12: ("oui sous conditions", "permis de construire + architecte"), 13: ("oui sous conditions", "déclaration préalable"),
    14: ("impossible à dire", "dépend de la surface créée"), 15: ("information", "sans objet"),
    16: ("impossible à dire", "déclaration préalable"), 17: ("oui sous conditions", "déclaration préalable"),
    18: ("non", "sans objet"), 19: ("information", "sans objet"), 20: ("information", "déclaration préalable"),
    21: ("hors périmètre", "sans objet"), 22: ("hors périmètre", "déclaration préalable"), 23: ("information", "sans objet"),
    24: ("hors périmètre", "sans objet"), 25: ("oui sous conditions", "déclaration préalable"),
    26: ("impossible à dire", "dépend de la surface créée"), 27: ("non", "sans objet"), 28: ("impossible à dire", "dépend de la surface"),
    29: ("non", "sans objet"), 30: ("hors périmètre", "sans objet"),
}
# corrections du banc après le 1er passage (27/09), le texte relu à chaque fois :
# V03, V14, V28 : la question ne donne pas la surface, la démarche « dépend » donc de la surface (le banc supposait un
#   petit projet) ; V28 : N 2 b) admet les annexes des constructions existant en 1995, donc « non » était trop sec :
#   tout dépend de la date de la maison (« impossible à dire »)
CORRECTIONS = {"V03": "démarche : dépend de la surface du bassin (non donnée)", "V14": "démarche : dépend de la surface créée",
               "V28": "verdict : impossible à dire (N 2 b, annexes des constructions de 1995) ; démarche : dépend de la surface"}
for x in Q:
    v, d = TYPES[int(x["id"][1:])]
    x["attendu"]["verdict_type"], x["attendu"]["demarche_type"] = v, d
    x["attendu"]["articles"] = [g["article"] for g in x["attendu"]["regles"]]
    if x["id"] in CORRECTIONS:
        x["attendu"]["correction"] = CORRECTIONS[x["id"]]

json.dump(Q, open(os.path.join(B, "questions-v2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- la page de validation
e = html.escape


def carte(x):
    f, a = x["faits"], x["attendu"]
    tags = "".join(f"<span class='tag'>{e(t)}</span>" for t in f.get("contraintes", []))
    regles = "".join(f"<li><b>{e(g['article'])}, p. {g['page']}</b> : {e(g['dit'])}<q>{e(g['citation'])}</q></li>" for g in a["regles"])
    lois = "".join(f"<li><a href='{e(l['url'])}' target='_blank'>{e(l['texte'])}</a> : {e(l['dit'])}</li>" for l in a["loi"])
    verif = "".join(f"<li>{e(v)}</li>" for v in a["a_verifier"]) or "<li class='vide'>rien</li>"
    parcelle = f" · parcelle {e(str(f.get('parcelle')))} · {f.get('surface_m2')} m²" if f.get("parcelle") else ""
    src = (f"<p class='src'>D'après une vraie question : <a href='{e(x['source']['url'])}' target='_blank'>{e(x['source']['nom'])}</a></p>"
           if x["source"] else "<p class='src'>Cas construit pour couvrir une zone du PLU</p>")
    return f"""<article class="q {'hors' if x['nature'] == 'hors périmètre' else ''}">
  <header><span class="id">{x['id']}</span><span class="type">{e(x['nature'])} · {e(x['projet'])}{' · point de vue du voisin' if x['point_de_vue'] == 'voisin' else ''}</span></header>
  {src}<h2>« {e(x['question'])} »</h2>
  <p class="faits">zone <b>{e(str(f.get('zone')))}</b>{parcelle}</p><div class="tags">{tags}</div>
  <p class="verdict">{e(a['verdict'])}</p><p class="demarche">Démarche : <b>{e(a['demarche'])}</b></p>
  {f'<h3>Règles du PLU</h3><ul>{regles}</ul>' if regles else ''}{f'<h3>Code de l’urbanisme</h3><ul>{lois}</ul>' if lois else ''}
  <h3>À vérifier</h3><ul>{verif}</ul>
  <p class="piege"><b>Piège testé :</b> {e(x['piege'])}</p>
</article>"""


reelles = [x for x in Q if x["origine"] == "vraie question"]
page_html = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Banc d'essai v2 · assistant PLU</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{{--fond:#F5F0E8;--carte:#fff;--encre:#1D1A17;--gris:#8A837B;--filet:#E4DCD0;--acc:#1971c2;--rouge:#C22E4A;--vert:#2f9e44}}
*{{box-sizing:border-box;margin:0}} body{{background:var(--fond);color:var(--encre);font:400 16px/1.5 Geist,system-ui,sans-serif;padding:32px 40px 60px}}
h1{{font-size:34px;font-weight:800}} .chapo{{color:var(--gris);font-size:18px;margin:6px 0 24px;max-width:1150px}} a{{color:var(--acc)}}
.grille{{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:18px}}
.q{{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:18px 20px;display:flex;flex-direction:column;gap:8px}}
.q.hors{{border-style:dashed}} header{{display:flex;gap:10px;align-items:center}}
.id{{font-weight:800;background:var(--encre);color:var(--fond);border-radius:6px;padding:2px 8px;font-size:13px}}
.type{{font-size:13px;font-weight:600;color:var(--gris);text-transform:uppercase;letter-spacing:.05em}}
.src{{font-size:13px;color:var(--gris)}} h2{{font-size:18px;font-weight:600;line-height:1.35}}
h3{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--gris);margin-top:6px}}
.faits{{font-size:14px;color:var(--gris)}} .faits b{{color:var(--encre)}}
.tags{{display:flex;flex-wrap:wrap;gap:6px}} .tag{{font-size:12px;background:#fff3bf;border-radius:20px;padding:2px 10px}}
.verdict{{font-size:18px;font-weight:800;color:var(--acc);border-left:4px solid var(--acc);padding-left:10px}}
.demarche{{font-size:15px}} ul{{padding-left:18px;font-size:14px}} li{{margin:3px 0}}
q{{display:block;color:var(--gris);font-size:13px;quotes:"« " " »"}} .vide{{color:var(--gris);list-style:none;margin-left:-18px}}
.piege{{font-size:14px;color:var(--rouge);margin-top:auto;padding-top:6px;border-top:1px solid var(--filet)}}
</style></head><body>
<h1>Banc d'essai v2 : {len(Q)} questions, dont {len(reelles)} vraies</h1>
<p class="chapo">{len(reelles)} questions viennent de vraies personnes (forums, FAQ de mairies, questions posées à des avocats ou à des
experts), transposées sur de vraies adresses de Biarritz ; {len(Q) - len(reelles)} cas sont construits pour couvrir les zones du PLU.
Chaque réponse attendue donne la démarche (Code de l'urbanisme, liens Légifrance) et les règles du PLU (citations vérifiées par le
code, à leur page). Les questions hors périmètre sont en pointillés. Catalogue complet des {len(REELLES)} vraies questions trouvées :
questions-reelles.json.</p>
<div class="grille">{''.join(carte(x) for x in Q)}</div></body></html>"""
open(os.path.join(B, "questions-v2.html"), "w", encoding="utf-8").write(page_html)
print(len(REELLES), "vraies questions au catalogue ;", len(Q), "questions au banc (", len(reelles), "vraies ) ;",
      sum(len(x["attendu"]["regles"]) for x in Q), "citations du PLU vérifiées ;",
      sum(len(x["attendu"]["loi"]) for x in Q), "renvois au Code de l'urbanisme")
