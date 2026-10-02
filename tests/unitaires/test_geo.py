"""Les outils géographiques, sans réseau : un faux requests.get joue les API publiques (géocodage, cadastre, Géoportail de
l'Urbanisme), le cache disque est redirigé vers tmp_path et les attentes entre deux essais sont notées au lieu d'être dormies.
On vérifie ce que l'agent reçoit vraiment : l'adresse, la parcelle, la zone, les contraintes et le périmètre (Biarritz seul)."""
import json

import pytest
import requests

import orbi.outils.geo as geo

URL = "https://api.exemple.test/recherche"
GEOCODAGE = "https://data.geopf.fr/geocodage/search"
CADASTRE = "https://apicarto.ign.fr/api/cadastre/parcelle"
GPU = "https://apicarto.ign.fr/api/gpu/"
ZONES = GPU + "zone-urba"
PRESCRIPTIONS = [GPU + "prescription-surf", GPU + "prescription-lin", GPU + "prescription-pct"]
INFORMATIONS, SERVITUDES = GPU + "info-surf", GPU + "assiette-sup-s"
COUCHES = PRESCRIPTIONS + [INFORMATIONS, SERVITUDES]  # dans l'ordre où contraintes() les interroge
VIDE = {"type": "FeatureCollection", "features": []}


def reponse(corps, code=200):
    """Une vraie requests.Response : .ok et .json() s'y comportent comme sur le réseau (une page HTML lève l'erreur de requests)."""
    r = requests.Response()
    r.status_code = code
    r._content = corps if isinstance(corps, bytes) else json.dumps(corps).encode("utf-8")
    r.encoding = "utf-8"
    return r


class FauxReseau:
    """Joue les API à la place de requests.get. Une route est un corps JSON, une fonction des paramètres, ou une liste d'issues
    prises dans l'ordre (corps, Response, exception). Une URL sans route fait échouer le test : rien ne part sur le réseau."""

    def __init__(self):
        self.routes, self.appels, self.attentes = {}, [], []

    def __call__(self, url, params=None, headers=None, timeout=None):
        params = dict(params or {})
        self.appels.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        assert url in self.routes, f"appel réseau inattendu : {url}"
        issue = self.routes[url]
        if isinstance(issue, list):
            issue = issue.pop(0)
        elif callable(issue):
            issue = issue(params)
        if isinstance(issue, Exception):
            raise issue
        return issue if isinstance(issue, requests.Response) else reponse(issue)

    def urls(self):
        return [a["url"] for a in self.appels]

    def params(self, url):
        return [a["params"] for a in self.appels if a["url"] == url]


@pytest.fixture(autouse=True)
def reseau(monkeypatch, tmp_path):
    """Chaque test a son faux réseau, son cache vide (tmp_path) et des attentes instantanées : aucun test ne touche donnees/."""
    faux = FauxReseau()
    monkeypatch.setattr(geo, "CACHE", str(tmp_path))
    monkeypatch.setattr(geo.requests, "get", faux)
    monkeypatch.setattr(geo.time, "sleep", faux.attentes.append)
    return faux


def en_cache(dossier):
    """Les réponses gardées sur le disque."""
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(dossier.glob("*.json"))]


def lieu(label, code_insee, commune, lon, lat, score=0.9629):
    """Une réponse du géocodage : un seul résultat, le meilleur."""
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                                                       "properties": {"label": label, "score": score, "citycode": code_insee,
                                                                      "city": commune}}]}


def carre(lon, lat, cote=0.001):
    """Une parcelle carrée en MultiPolygon, comme le cadastre ; l'anneau est fermé (le premier sommet est répété à la fin)."""
    return {"type": "MultiPolygon", "coordinates": [[[[lon, lat], [lon + cote, lat], [lon + cote, lat + cote], [lon, lat + cote],
                                                      [lon, lat]]]]}


def parcelle_cadastre(section, numero, contenance, geometrie):
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": geometrie, "properties": {
        "section": section, "numero": numero, "contenance": contenance, "code_insee": "64122", "idu": f"64122000{section}{numero}"}}]}


def zone_plu(libelle, typezone):
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": None, "properties": {
        "libelle": libelle, "typezone": typezone, "idurba": "64122_PLU_20250927"}}]}


def couche(*proprietes):
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": None, "properties": p} for p in proprietes]}


def dedans(point, anneau):
    """Le point est-il dans le polygone ? Lancer de rayon : un point intérieur traverse un nombre impair de côtés."""
    x, y = point
    impair = False
    for (x1, y1), (x2, y2) in zip(anneau, anneau[1:]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            impair = not impair
    return impair


CA_0044 = carre(-1.5540, 43.4650)  # contient le point du 5 impasse Monnier
BM_0224 = carre(-1.5600, 43.4700)  # une autre parcelle, en zone Nh
CARRE = CA_0044["coordinates"][0][0]
MONNIER = lieu("5 Impasse Monnier 64200 Biarritz", "64122", "Biarritz", -1.5536, 43.4653)
ANGLET = lieu("Rue Marie Blanque 64600 Anglet", "64024", "Anglet", -1.5093, 43.4897)


def monde(reseau, dans_biarritz=MONNIER, partout=MONNIER):
    """Un petit Biarritz : le géocodage (limité à la commune ou non), le cadastre (CA 0044 au point de l'adresse, BM 0224 par sa
    référence), la zone (Nh dans BM 0224, UDa ailleurs) et une servitude de site patrimonial sur toute parcelle."""

    def geocodage(p):
        return dans_biarritz if p.get("citycode") == geo.BIARRITZ else partout

    def cadastre(p):
        if "geom" in p:
            return parcelle_cadastre("CA", "0044", 586, CA_0044)
        return parcelle_cadastre("BM", "0224", 1210, BM_0224) if (p["section"], p["numero"]) == ("BM", "0224") else VIDE

    def zone(p):
        dans_bm = dedans(json.loads(p["geom"])["coordinates"], BM_0224["coordinates"][0][0])
        return zone_plu("Nh", "N") if dans_bm else zone_plu("UDa", "U")

    reseau.routes.update({GEOCODAGE: geocodage, CADASTRE: cadastre, ZONES: zone, **{u: VIDE for u in COUCHES}})
    reseau.routes[SERVITUDES] = couche({"suptype": "ac4", "nomsuplitt": "Site patrimonial remarquable de Biarritz"})


# ── _get : le cache disque et les nouveaux essais ────────────────────────────────────────────────────────────────────────────

def test_la_premiere_requete_est_ecrite_sur_le_disque(reseau, tmp_path):
    corps = {"features": [{"properties": {"label": "12 Avenue Édouard VII 64200 Biarritz"}}]}
    reseau.routes[URL] = corps
    assert geo._get(URL, q="12 avenue Édouard VII", limit=1) == corps
    assert en_cache(tmp_path) == [corps]


def test_la_deuxieme_requete_est_lue_sur_le_disque_sans_reseau(reseau):
    """C'est ce qui rend le banc rejouable à l'identique."""
    reseau.routes[URL] = {"features": ["la réponse du serveur"]}
    premiere = geo._get(URL, q="5 impasse Monnier")
    del reseau.routes[URL]  # désormais, un appel au réseau ferait échouer le test
    assert geo._get(URL, q="5 impasse Monnier") == premiere
    assert len(reseau.appels) == 1


def test_l_ordre_des_parametres_ne_change_pas_l_entree_du_cache(reseau):
    reseau.routes[URL] = VIDE
    geo._get(URL, section="CA", numero="0044")
    geo._get(URL, numero="0044", section="CA")
    assert len(reseau.appels) == 1


def test_deux_requetes_differentes_ont_chacune_leur_entree(reseau, tmp_path):
    reseau.routes[URL] = lambda p: {"q": p["q"]}
    reseau.routes[URL + "/autre"] = lambda p: {"autre": p["q"]}
    assert geo._get(URL, q="5 impasse Monnier") == {"q": "5 impasse Monnier"}
    assert geo._get(URL, q="6 impasse Monnier") == {"q": "6 impasse Monnier"}
    assert geo._get(URL + "/autre", q="5 impasse Monnier") == {"autre": "5 impasse Monnier"}
    assert len(en_cache(tmp_path)) == 3


def test_la_requete_porte_ses_parametres_l_agent_et_un_delai(reseau):
    """Les API publiques veulent savoir qui appelle ; sans délai, un serveur muet bloquerait l'agent."""
    reseau.routes[URL] = VIDE
    geo._get(URL, q="5 impasse Monnier", limit=1)
    assert reseau.appels == [{"url": URL, "params": {"q": "5 impasse Monnier", "limit": 1}, "headers": geo.UA, "timeout": 60}]


def test_une_reponse_vide_mais_valide_est_gardee(reseau):
    """« Aucune parcelle ici » est une vraie réponse : le banc la rejoue sans redemander."""
    reseau.routes[URL] = VIDE
    assert geo._get(URL, q="x") == VIDE == geo._get(URL, q="x")
    assert len(reseau.appels) == 1


PANNES = [
    pytest.param(reponse({"message": "erreur interne"}, 500), id="erreur 500"),
    pytest.param(reponse({"message": "introuvable"}, 404), id="erreur 404"),
    pytest.param(requests.ConnectionError("réseau coupé"), id="pas de connexion"),
    pytest.param(requests.Timeout("60 s sans réponse"), id="délai dépassé"),
    pytest.param(reponse(b"<html>maintenance</html>"), id="page HTML au lieu du JSON"),
]


@pytest.mark.parametrize("panne", PANNES)
def test_une_reponse_en_erreur_n_est_pas_mise_en_cache(reseau, tmp_path, panne):
    """Trois essais, puis {} : l'agent continue sans ces faits, et rien de faux n'est gardé pour les passages suivants."""
    reseau.routes[URL] = lambda p: panne
    assert geo._get(URL, q="x") == {}
    assert len(reseau.appels) == 3
    assert en_cache(tmp_path) == []


def test_un_echec_n_est_pas_retenu_la_requete_suivante_repart_sur_le_reseau(reseau):
    reseau.routes[URL] = [reponse({}, 503)] * 3 + [{"features": ["revenu"]}]
    assert geo._get(URL, q="x") == {}
    assert geo._get(URL, q="x") == {"features": ["revenu"]}
    assert len(reseau.appels) == 4


def test_une_panne_passagere_est_rattrapee(reseau, tmp_path):
    reseau.routes[URL] = [requests.ConnectionError("coupure"), reponse({}, 502), {"features": ["enfin"]}]
    assert geo._get(URL, q="x") == {"features": ["enfin"]}
    assert reseau.attentes == [2, 4], "une attente après chaque échec, de plus en plus longue"
    assert en_cache(tmp_path) == [{"features": ["enfin"]}]


def test_pas_d_attente_apres_le_dernier_essai(reseau):
    reseau.routes[URL] = lambda p: requests.ConnectionError("réseau coupé")
    geo._get(URL, q="x")
    assert reseau.attentes == [2, 4]


# ── adresse, parcelle, zonage ────────────────────────────────────────────────────────────────────────────────────────────────

def test_l_adresse_est_cherchee_dans_la_commune_imposee(reseau):
    reseau.routes[GEOCODAGE] = MONNIER
    a = geo.adresse("5 impasse Monnier", geo.BIARRITZ)
    assert reseau.params(GEOCODAGE) == [{"q": "5 impasse Monnier", "limit": 1, "citycode": "64122"}]
    assert a == {"label": "5 Impasse Monnier 64200 Biarritz", "lon": -1.5536, "lat": 43.4653, "commune": "Biarritz",
                 "code_insee": "64122", "fiabilite": 0.96}


def test_sans_commune_imposee_l_adresse_est_cherchee_partout(reseau):
    reseau.routes[GEOCODAGE] = ANGLET
    a = geo.adresse("rue Marie Blanque, Anglet")
    assert reseau.params(GEOCODAGE) == [{"q": "rue Marie Blanque, Anglet", "limit": 1}]
    assert (a["commune"], a["code_insee"]) == ("Anglet", "64024")


@pytest.mark.parametrize("route", [pytest.param(VIDE, id="aucun résultat"),
                                   pytest.param(lambda p: requests.ConnectionError("réseau coupé"), id="API injoignable")])
def test_une_adresse_introuvable_donne_none(reseau, route):
    reseau.routes[GEOCODAGE] = route
    assert geo.adresse("999 rue qui n'existe pas", geo.BIARRITZ) is None


def test_sans_score_la_fiabilite_est_nulle(reseau):
    corps = lieu("Biarritz", "64122", "Biarritz", -1.5586, 43.4832)
    del corps["features"][0]["properties"]["score"]
    reseau.routes[GEOCODAGE] = corps
    assert geo.adresse("Biarritz", geo.BIARRITZ)["fiabilite"] == 0


def test_la_parcelle_est_cherchee_au_point_de_l_adresse(reseau):
    reseau.routes[CADASTRE] = parcelle_cadastre("CA", "0044", 586, CA_0044)
    p = geo.parcelle(-1.5536, 43.4653)
    assert json.loads(reseau.params(CADASTRE)[0]["geom"]) == {"type": "Point", "coordinates": [-1.5536, 43.4653]}
    assert p == {"parcelle": "CA 0044", "surface_m2": 586, "geometrie": CA_0044}


def test_la_zone_est_cherchee_au_point(reseau):
    reseau.routes[ZONES] = zone_plu("UDa", "U")
    z = geo.zonage(-1.5536, 43.4653)
    assert json.loads(reseau.params(ZONES)[0]["geom"]) == {"type": "Point", "coordinates": [-1.5536, 43.4653]}
    assert z == {"zone": "UDa", "type_zone": "U", "document": "64122_PLU_20250927"}


@pytest.mark.parametrize("outil, url", [pytest.param(geo.parcelle, CADASTRE, id="pas de parcelle (point sur la voie)"),
                                        pytest.param(geo.zonage, ZONES, id="pas de zone (hors du PLU)")])
def test_rien_au_point_donne_none(reseau, outil, url):
    reseau.routes[url] = VIDE
    assert outil(-1.5536, 43.4653) is None


# ── contraintes : prescriptions, informations, servitudes ────────────────────────────────────────────────────────────────────

def test_les_cinq_couches_sont_interrogees_sur_la_parcelle(reseau):
    reseau.routes.update({u: VIDE for u in COUCHES})
    geo.contraintes(CA_0044)
    assert reseau.urls() == COUCHES
    assert all(json.loads(p["geom"]) == CA_0044 for p in (a["params"] for a in reseau.appels))


def test_les_contraintes_sont_rangees_par_nature(reseau):
    reseau.routes.update({
        PRESCRIPTIONS[0]: couche({"libelle": "Espace boisé\n   classé", "txt": "EBC"}, {"libelle": "Hauteur maximale", "txt": "5"}),
        PRESCRIPTIONS[1]: couche({"libelle": "Espace boisé classé", "txt": "EBC"}, {"libelle": "Hauteur maximale", "txt": "5"}),
        PRESCRIPTIONS[2]: couche({"libelle": None, "txt": "Arbre remarquable"}, {"libelle": "Hauteur maximale", "txt": "12"}),
        INFORMATIONS: couche({"libelle": "Secteur d'information sur les sols", "txt": "SIS"}),
        SERVITUDES: couche({"suptype": "ac4", "nomsuplitt": "Site patrimonial remarquable de Biarritz", "libelle": "AC4"}),
    })
    assert geo.contraintes(CA_0044) == {
        "prescriptions": ["Espace boisé classé", "Arbre remarquable"],  # espaces unifiés, doublon d'une couche à l'autre écarté
        "informations": ["Secteur d'information sur les sols"],
        "servitudes": ["Site patrimonial remarquable de Biarritz"],  # le nom lisible plutôt que le code
        "hauteurs_au_plan": ["5", "12"],  # rangées à part, sans doublon
        "site_patrimonial": True}


ECARTEES = [
    pytest.param({"libelle": "Majoration des volumes constructibles pour les programmes comportant\ndes logements locatifs "
                             "sociaux", "txt": "MVC"}, id="majoration des volumes (logement social)"),
    pytest.param({"libelle": "UB", "txt": "mix soc"}, id="secteur de mixité sociale (un nom de zone)"),
    pytest.param({"libelle": "UDa*", "txt": "mix soc"}, id="nom de zone de quatre caractères"),
    pytest.param({"libelle": "", "txt": None}, id="libellé vide"),
    pytest.param({"libelle": "   ", "txt": None}, id="libellé fait d'espaces"),
    pytest.param({"libelle": "Hauteur maximale", "txt": "5"}, id="hauteur au plan (rangée à part)"),
]


@pytest.mark.parametrize("proprietes", ECARTEES)
def test_ce_qui_n_interesse_pas_un_particulier_est_ecarte(reseau, proprietes):
    reseau.routes.update({u: VIDE for u in COUCHES})
    reseau.routes[PRESCRIPTIONS[0]] = couche(proprietes)
    assert geo.contraintes(CA_0044)["prescriptions"] == []


@pytest.mark.parametrize("suptype, patrimonial", [pytest.param("ac4", True, id="site patrimonial (AC4)"),
                                                  pytest.param("ac1", False, id="monument historique (AC1)"),
                                                  pytest.param("pm1", False, id="plan de prévention des risques (PM1)")])
def test_seul_le_site_patrimonial_leve_le_drapeau(reseau, suptype, patrimonial):
    """Le drapeau commande l'avis de l'Architecte des Bâtiments de France : une autre servitude ne le lève pas."""
    reseau.routes.update({u: VIDE for u in COUCHES})
    reseau.routes[SERVITUDES] = couche({"suptype": suptype, "nomsuplitt": "Une servitude d'utilité publique"})
    c = geo.contraintes(CA_0044)
    assert c["site_patrimonial"] is patrimonial
    assert c["servitudes"] == ["Une servitude d'utilité publique"]


def test_sans_reseau_les_contraintes_sont_vides_sans_planter(reseau):
    reseau.routes.update({u: (lambda p: requests.ConnectionError("réseau coupé")) for u in COUCHES})
    assert geo.contraintes(CA_0044) == {"prescriptions": [], "informations": [], "servitudes": [], "hauteurs_au_plan": [],
                                        "site_patrimonial": False}
    assert len(reseau.appels) == 15


# ── parcelle_par_reference ───────────────────────────────────────────────────────────────────────────────────────────────────

REFERENCES = [
    pytest.param("CA 0044", "CA", "0044", id="référence complète"),
    pytest.param("parcelle CA 44", "CA", "0044", id="dans une phrase, sans les zéros"),
    pytest.param("ca44", "CA", "0044", id="minuscules collées"),
    pytest.param("AB 521", "AB", "0521", id="numéro à trois chiffres"),
    pytest.param("BM0224", "BM", "0224", id="collée, avec ses zéros"),
]


@pytest.mark.parametrize("reference, section, numero", REFERENCES)
def test_une_reference_cadastrale_est_lue(reseau, reference, section, numero):
    reseau.routes[CADASTRE] = lambda p: parcelle_cadastre(p["section"], p["numero"], 586, CA_0044)
    p = geo.parcelle_par_reference(reference)
    assert reseau.params(CADASTRE) == [{"code_insee": "64122", "section": section, "numero": numero}]
    assert p == {"parcelle": f"{section} {numero}", "surface_m2": 586, "geometrie": CA_0044}


@pytest.mark.parametrize("reference", [pytest.param(None, id="aucune"), pytest.param("", id="vide"),
                                       pytest.param("parcelle 44", id="numéro sans section"),
                                       pytest.param("12 avenue Édouard VII", id="une adresse")])
def test_une_reference_illisible_ne_part_pas_sur_le_reseau(reseau, reference):
    assert geo.parcelle_par_reference(reference) is None
    assert reseau.appels == []


def test_une_reference_absente_du_cadastre_donne_none(reseau):
    reseau.routes[CADASTRE] = VIDE
    assert geo.parcelle_par_reference("ZZ 9999") is None


# ── _point_dans ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

L = [[0, 0], [40, 0], [40, 4], [4, 4], [4, 40], [0, 40], [0, 0]]  # deux bandes de 4 m sur 40 m, en équerre


@pytest.mark.parametrize("point, attendu", [pytest.param((2, 20), True, id="dans la branche verticale"),
                                            pytest.param((20, 2), True, id="dans la branche horizontale"),
                                            pytest.param((20, 20), False, id="dans le creux du L")])
def test_le_juge_du_test_reconnait_l_interieur_d_un_L(point, attendu):
    """Le juge doit être juste, sinon le xfail de la parcelle en L ne prouverait rien."""
    assert dedans(point, L) is attendu


@pytest.mark.parametrize("geometrie", [pytest.param(CA_0044, id="MultiPolygon (cadastre)"),
                                       pytest.param({"type": "Polygon", "coordinates": [CARRE]}, id="Polygon")])
def test_le_point_tombe_dans_une_parcelle_compacte(geometrie):
    assert dedans(geo._point_dans(geometrie), CARRE)


def test_d_une_parcelle_en_deux_morceaux_on_prend_le_premier():
    loin = carre(-1.5000, 43.5000)["coordinates"][0]
    assert dedans(geo._point_dans({"type": "MultiPolygon", "coordinates": [[CARRE], loin]}), CARRE)


@pytest.mark.xfail(strict=True, reason="défaut connu : la moyenne des sommets tombe hors d'une parcelle concave ; pour une "
                                       "parcelle en L citée par sa référence, la zone serait cherchée chez le voisin")
def test_le_point_tombe_dans_une_parcelle_en_L():
    assert dedans(geo._point_dans({"type": "Polygon", "coordinates": [L]}), L)


# ── faits : le périmètre, la référence cadastrale, ce que l'agent reçoit ─────────────────────────────────────────────────────

def test_une_adresse_de_biarritz_donne_tous_les_faits(reseau):
    monde(reseau)
    f = geo.faits("5 impasse Monnier", "Puis-je poser un abri de jardin de 8 m² au 5 impasse Monnier à Biarritz ?")
    assert reseau.params(GEOCODAGE)[0]["citycode"] == geo.BIARRITZ
    assert reseau.urls() == [GEOCODAGE, CADASTRE, ZONES, *COUCHES], "dans l'ordre où l'agent les obtient"
    assert f == {
        "trouvee": True, "dans_le_perimetre": True,
        "adresse": {"label": "5 Impasse Monnier 64200 Biarritz", "lon": -1.5536, "lat": 43.4653, "commune": "Biarritz",
                    "code_insee": "64122", "fiabilite": 0.96},
        "parcelle": {"parcelle": "CA 0044", "surface_m2": 586},  # sans la géométrie
        "zonage": {"zone": "UDa", "type_zone": "U", "document": "64122_PLU_20250927"},
        "contraintes": {"prescriptions": [], "informations": [], "servitudes": ["Site patrimonial remarquable de Biarritz"],
                        "hauteurs_au_plan": [], "site_patrimonial": True}}


def test_une_adresse_sans_ville_est_cherchee_a_biarritz(reseau):
    """« 12 avenue Édouard VII » sans nom de ville partait à Pau."""
    monde(reseau, dans_biarritz=lieu("12 Avenue Édouard VII 64200 Biarritz", "64122", "Biarritz", -1.5536, 43.4653),
          partout=lieu("12 Avenue Édouard VII 64000 Pau", "64445", "Pau", -0.3700, 43.2950))
    f = geo.faits("12 avenue Édouard VII", "Puis-je construire une véranda de 20 m² au 12 avenue Édouard VII ?")
    assert reseau.params(GEOCODAGE)[0]["citycode"] == geo.BIARRITZ
    assert f["dans_le_perimetre"] is True and f["adresse"]["commune"] == "Biarritz"


@pytest.mark.parametrize("adresse, question", [
    pytest.param("rue Marie Blanque, Anglet", "Puis-je construire une véranda rue Marie Blanque ?", id="commune dans l'adresse"),
    pytest.param("rue Marie Blanque", "Puis-je construire une véranda rue Marie Blanque à Anglet ?",
                 id="commune dans la question (V30)"),
])
def test_une_adresse_hors_de_biarritz_est_hors_perimetre(reseau, adresse, question):
    monde(reseau, partout=ANGLET)
    f = geo.faits(adresse, question)
    assert "citycode" not in reseau.params(GEOCODAGE)[0], "la commune nommée lève la limite à Biarritz"
    assert f == {"trouvee": True, "dans_le_perimetre": False,
                 "adresse": {"label": "Rue Marie Blanque 64600 Anglet", "lon": -1.5093, "lat": 43.4897, "commune": "Anglet",
                             "code_insee": "64024", "fiabilite": 0.96}}
    assert reseau.urls() == [GEOCODAGE], "ni cadastre ni zonage pour une adresse hors périmètre"


@pytest.mark.parametrize("adresse, question, commune", [
    pytest.param("route du Golf", "Puis-je poser un abri de jardin route du Golf, à Arcangues ?", "Arcangues", id="Arcangues"),
    pytest.param("rue du Port", "Puis-je poser un abri de jardin rue du Port, à Guéthary ?", "Guéthary", id="Guéthary"),
    pytest.param("rue du Port", "Puis-je poser un abri de jardin rue du Port, à Saint-Jean-de-Luz ?", "Saint-Jean-de-Luz",
                 id="Saint-Jean-de-Luz (majuscules)"),
])
def test_la_commune_nommee_l_emporte_sur_le_geocodage(reseau, adresse, question, commune):
    """« route du Golf, Arcangues » était géocodé « Route d'Arcangues, Biarritz » : une rue de Biarritz porte le nom de la commune
    voisine. La personne a nommé une autre commune : c'est elle qui compte."""
    monde(reseau, partout=lieu("Route d'Arcangues 64200 Biarritz", "64122", "Biarritz", -1.5536, 43.4653))
    f = geo.faits(adresse, question)
    assert "citycode" not in reseau.params(GEOCODAGE)[0]
    assert f["dans_le_perimetre"] is False
    assert f["adresse"] == {"label": adresse, "lon": -1.5536, "lat": 43.4653, "commune": commune, "code_insee": None,
                            "fiabilite": 0.96}


def test_une_rue_au_nom_d_une_commune_voisine_reste_a_biarritz(reseau):
    """D33 du 2e banc caché : le « 93 Avenue de Bidart » de la question est à Biarritz, et la question le dit."""
    monde(reseau, dans_biarritz=lieu("93 Avenue de Bidart 64200 Biarritz", "64122", "Biarritz", -1.5536, 43.4653),
          partout=lieu("Avenue de Bidart 64210 Bidart", "64125", "Bidart", -1.5910, 43.4370))
    f = geo.faits("93 Avenue de Bidart 64200 Biarritz",
                  "Je voudrais une piscine non couverte de 35 m² au 93 Avenue de Bidart à Biarritz. Est-ce autorisé ?")
    assert reseau.params(GEOCODAGE)[0]["citycode"] == geo.BIARRITZ
    assert f["dans_le_perimetre"] is True and f["adresse"]["label"] == "93 Avenue de Bidart 64200 Biarritz"


def test_la_reference_cadastrale_passe_avant_l_adresse(reseau):
    """Une rue sans numéro peut tomber sur la parcelle d'en face : avec une référence, on se place dans la parcelle elle-même."""
    monde(reseau, dans_biarritz=lieu("Impasse Monnier 64200 Biarritz", "64122", "Biarritz", -1.5536, 43.4653, score=0.71))
    f = geo.faits("impasse Monnier", "Puis-je agrandir ma maison, parcelle BM 224, impasse Monnier à Biarritz ?",
                  reference_parcelle="BM 224")
    assert f["parcelle"] == {"parcelle": "BM 0224", "surface_m2": 1210}
    assert f["zonage"]["zone"] == "Nh", "la zone est cherchée dans la parcelle référencée, pas au point de l'adresse (UDa)"
    assert f["adresse"]["label"] == "Impasse Monnier 64200 Biarritz", "l'adresse trouvée reste celle qu'on affiche"
    assert all("geom" not in p for p in reseau.params(CADASTRE)), "pas de recherche de parcelle au point de l'adresse"
    assert all(json.loads(p["geom"]) == BM_0224 for u in COUCHES for p in reseau.params(u)), "les contraintes de BM 0224"


def test_une_reference_seule_suffit(reseau):
    monde(reseau)
    f = geo.faits(None, "Que puis-je construire sur la parcelle BM 224 ?", reference_parcelle="BM 224")
    lon, lat = geo._point_dans(BM_0224)
    assert f["adresse"] == {"label": "parcelle BM 0224, Biarritz", "lon": lon, "lat": lat, "commune": "Biarritz",
                            "code_insee": "64122", "fiabilite": 1}
    assert f["dans_le_perimetre"] is True and f["zonage"]["zone"] == "Nh"
    assert GEOCODAGE not in reseau.urls()


def test_une_reference_introuvable_laisse_l_adresse_decider(reseau):
    monde(reseau)
    f = geo.faits("5 impasse Monnier", "Puis-je poser un abri de jardin, parcelle ZZ 9999, 5 impasse Monnier à Biarritz ?",
                  reference_parcelle="ZZ 9999")
    assert f["parcelle"] == {"parcelle": "CA 0044", "surface_m2": 586}
    assert f["zonage"]["zone"] == "UDa"


@pytest.mark.parametrize("adresse", [pytest.param(None, id="pas d'adresse"), pytest.param("", id="adresse vide"),
                                     pytest.param("999 rue qui n'existe pas", id="adresse introuvable")])
def test_sans_adresse_ni_reference_rien_n_est_trouve(reseau, adresse):
    monde(reseau, dans_biarritz=VIDE)
    assert geo.faits(adresse, "Puis-je construire une véranda à Biarritz ?") == {"trouvee": False}
    assert set(reseau.urls()) <= {GEOCODAGE}


def test_une_adresse_hors_de_toute_parcelle_garde_sa_zone(reseau):
    """Le point d'une adresse peut tomber sur la voie : pas de parcelle, donc pas de contraintes, mais la zone reste connue."""
    monde(reseau)
    reseau.routes[CADASTRE] = VIDE
    f = geo.faits("5 impasse Monnier", "Puis-je construire une véranda au 5 impasse Monnier à Biarritz ?")
    assert (f["parcelle"], f["contraintes"], f["zonage"]["zone"]) == ({}, {}, "UDa")
    assert not set(COUCHES) & set(reseau.urls())


@pytest.mark.parametrize("reference", [pytest.param("ZZ 9999", id="absente du cadastre"),
                                       pytest.param("parcelle 44", id="illisible (sans section)")])
def test_une_reference_introuvable_sans_adresse_n_est_pas_trouvee(reseau, reference):
    monde(reseau)
    assert geo.faits(None, "Que puis-je construire sur ma parcelle ?", reference_parcelle=reference) == {"trouvee": False}


@pytest.mark.parametrize("adresse, ailleurs", [
    pytest.param("3 rue Paul Bert", lieu("3 Rue Paul Bert 64000 Pau", "64445", "Pau", -0.3650, 43.2980), id="Paul n'est pas Pau"),
    pytest.param("2 rue d'Angleterre", lieu("2 Rue d'Angleterre 59000 Lille", "59350", "Lille", 3.0570, 50.6400),
                 id="Angleterre n'est pas Anglet"),
])
def test_un_mot_qui_contient_le_nom_d_une_commune_ne_la_nomme_pas(reseau, adresse, ailleurs):
    monde(reseau, dans_biarritz=lieu(f"{adresse} 64200 Biarritz", "64122", "Biarritz", -1.5536, 43.4653), partout=ailleurs)
    f = geo.faits(adresse, f"Puis-je poser un abri de jardin au {adresse} ?")
    assert reseau.params(GEOCODAGE)[0].get("citycode") == geo.BIARRITZ
    assert f["dans_le_perimetre"] is True


@pytest.mark.parametrize("adresse, question, ailleurs", [
    pytest.param("rue du Port", "Puis-je poser un abri de jardin rue du Port à Guethary ?",
                 lieu("Rue du Port 64210 Guéthary", "64249", "Guéthary", -1.6090, 43.4230), id="Guethary sans accent"),
    pytest.param("rue du Port", "Puis-je poser un abri de jardin rue du Port à St-Jean-de-Luz ?",
                 lieu("Rue du Port 64500 Saint-Jean-de-Luz", "64483", "Saint-Jean-de-Luz", -1.6630, 43.3880),
                 id="St-Jean-de-Luz en abrégé"),
    pytest.param("avenue de Biarritz", "Puis-je construire une véranda avenue de Biarritz à Anglet ?",
                 lieu("Avenue de Biarritz 64600 Anglet", "64024", "Anglet", -1.5200, 43.4800), id="avenue de Biarritz à Anglet"),
])
def test_une_autre_commune_ecrite_autrement_est_reconnue(reseau, adresse, question, ailleurs):
    monde(reseau, dans_biarritz=lieu("Rue du Port Vieux 64200 Biarritz", "64122", "Biarritz", -1.5536, 43.4653, score=0.52),
          partout=ailleurs)
    assert geo.faits(adresse, question)["dans_le_perimetre"] is False


def test_une_autre_commune_nommee_reste_hors_perimetre_sans_geocodage(reseau):
    monde(reseau, partout=VIDE)
    f = geo.faits("chemin de Larre", "Puis-je poser un abri de jardin de 10 m² chemin de Larre, à Arcangues ?")
    assert f.get("dans_le_perimetre") is False
