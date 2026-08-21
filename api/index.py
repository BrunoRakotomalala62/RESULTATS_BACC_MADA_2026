"""
API REST - Résultats du Baccalauréat Madagascar
================================================
Point d'entrée pour Vercel (serverless).

Endpoints:
  GET /                - Documentation
  GET /api/bacc/recherche?nom=XXX&province=YYY
  GET /api/bacc/recherche?matricule=XXX&province=YYY
  GET /api/bacc/provinces
"""

import hashlib
from flask import Flask, jsonify, request
import requests
from flask_cors import CORS

try:
    from .antananarivo import SOURCE_URL as ANTANANARIVO_SOURCE_URL
    from .antananarivo import search_results as search_antananarivo_results
except ImportError:  # lancement direct via server.py / environnement Vercel
    from antananarivo import SOURCE_URL as ANTANANARIVO_SOURCE_URL
    from antananarivo import search_results as search_antananarivo_results

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SECRET_KEY = "UGD2024"

PROVINCE_APIS = {
    "antsiranana": "https://diego-api.bacc.digital.gov.mg/api",
    "mahajanga":   "https://mahajanga-api.bacc.digital.gov.mg/api",
    "toamasina":   "https://mahajanga-api.bacc.digital.gov.mg/api",
    "toliara":     "https://bacc.toliara.digital.gov.mg/api",
    "fianarantsoa":"https://bacc.univ-fianarantsoa.mg/api",
    "antananarivo": ANTANANARIVO_SOURCE_URL,
}

PROVINCE_INFO = {
    "antsiranana": {"nom": "Antsiranana (Diego)",   "universite": "Oniversite Antsiranana",   "disponible": True},
    "mahajanga":   {"nom": "Mahajanga",             "universite": "Oniversite Mahajanga",     "disponible": True},
    "toamasina":   {"nom": "Toamasina",             "universite": "Oniversite Toamasina",     "disponible": False, "note": "Redirigé vers Mahajanga"},
    "toliara":     {"nom": "Toliara",               "universite": "Oniversite Toliara",       "disponible": True},
    "fianarantsoa":{"nom": "Fianarantsoa",          "universite": "Oniversite Fianarantsoa",  "disponible": True},
    "antananarivo":{"nom": "Antananarivo",          "universite": "Oniversite Antananarivo",  "disponible": True, "note": "Scraping de la page officielle de l'Université d'Antananarivo"},
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
})

# ---------------------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_key(search_term: str) -> str:
    """Génère la clé MD5: MD5(UGD2024 + searchTerm)"""
    return hashlib.md5(f"{SECRET_KEY}{search_term}".encode()).hexdigest()


def normalize_name(name: str) -> str:
    """Nettoie et normalise un nom (majuscules, espaces normalisés)."""
    return " ".join(name.strip().upper().split())


def search_fianarantsoa(search_term: str, mode: str = "nom") -> dict:
    """
    Interroge l'API de l'Université de Fianarantsoa.

    L'API source est différente des autres provinces :
      - GET https://bacc.univ-fianarantsoa.mg/api/search/name/{nom}
      - GET https://bacc.univ-fianarantsoa.mg/api/search/num/{num}

    Réponse brute :
      {"count": 68, "bacc": [{"num", "nom", "mention", "serie", "centre", "resultat"}]}
    """
    endpoint = "num" if mode == "matricule" else "name"
    url = f"{PROVINCE_APIS['fianarantsoa']}/search/{endpoint}/{search_term}"

    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        count = data.get("count", 0)
        raw_results = data.get("bacc", [])

        results = []
        for r in raw_results:
            resultat = r.get("resultat", "")
            admis = 1 if resultat in ("Admis(e)", "Admis") else 0
            results.append({
                "matricule": r.get("num"),
                "fullname": r.get("nom"),
                "serie": r.get("serie"),
                "mention": r.get("mention"),
                "center": r.get("centre"),
                "admis": admis,
                "admis_label": resultat,
            })

        return {
            "status": "OK",
            "province": "fianarantsoa",
            "mode": mode,
            "search_term": search_term,
            "count": count,
            "results": results,
            "source_message": data.get("message"),
        }
    except requests.exceptions.Timeout:
        return {"error": "Timeout - L'API source ne répond pas", "status": "ERROR"}
    except requests.exceptions.ConnectionError:
        return {"error": "Impossible de se connecter à l'API source", "status": "ERROR"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"Erreur HTTP {e.response.status_code}", "status": "ERROR"}
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}


def search_bacc(province: str, search_term: str, mode: str = "nom", annee: str | None = None) -> dict:
    """Effectue une recherche dans l'API du Baccalauréat."""
    if province not in PROVINCE_APIS:
        return {"error": f"Province inconnue: {province}", "status": "ERROR"}

    # Fianarantsoa a son propre format d'API
    if province == "fianarantsoa":
        return search_fianarantsoa(search_term, mode)

    # Antananarivo publie actuellement ses données dans le front-end React
    # de l'Université : on scrape la page et son bundle, puis on filtre localement.
    if province == "antananarivo":
        return search_antananarivo_results(session, search_term, mode, annee)

    api_base = PROVINCE_APIS[province]
    key = generate_key(search_term)
    params = {"matricule": search_term, "key": key} if mode == "matricule" else {"nom": search_term, "key": key}

    try:
        resp = session.get(f"{api_base}/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "OK":
            results = data.get("data", [])
            for r in results:
                r["admis_label"] = "Admis(e)" if r.get("admis") == 1 else "Non admis(e)"
            return {
                "status": "OK",
                "province": province,
                "mode": mode,
                "search_term": search_term,
                "count": len(results),
                "results": results
            }
        else:
            return {
                "status": "ERROR",
                "province": province,
                "message": data.get("message", "Erreur inconnue de l'API source"),
                "results": []
            }
    except requests.exceptions.Timeout:
        return {"error": "Timeout - L'API source ne répond pas", "status": "ERROR"}
    except requests.exceptions.ConnectionError:
        return {"error": "Impossible de se connecter à l'API source", "status": "ERROR"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"Erreur HTTP {e.response.status_code}", "status": "ERROR"}
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}


# ---------------------------------------------------------------------------
# Routes API
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return jsonify({
        "api": "Bacc Madagascar - API REST",
        "version": "1.2.0",
        "description": "API pour consulter les résultats du Baccalauréat à Madagascar",
        "source": "https://bacc.digital.gov.mg/",
        "endpoints": {
            "GET /api/bacc/recherche": "Rechercher par nom ou matricule (avec pagination page/per_page et filtre annee)",
            "GET /api/bacc/provinces": "Lister les provinces disponibles",
        },
        "exemples": {
            "par_nom": "/api/bacc/recherche?nom=Miora&province=fianarantsoa",
            "par_matricule": "/api/bacc/recherche?matricule=1260219&province=fianarantsoa",
            "antananarivo": "/api/bacc/recherche?nom=RAKOTO&province=antananarivo&annee=2026",
            "pagination": "/api/bacc/recherche?nom=Miora&province=fianarantsoa&page=2&per_page=10",
        },
        "provinces_disponibles": list(PROVINCE_APIS.keys()),
    })


def paginate_results(results: list, page: int, per_page: int) -> dict:
    """Découpe une liste de résultats et retourne les métadonnées de pagination."""
    total = len(results)
    if per_page <= 0:
        per_page = 15
    total_pages = max(1, (total + per_page - 1) // per_page)

    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    page_items = results[start:end]

    return {
        "items": page_items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None,
        },
    }


@app.route("/api/bacc/recherche")
def recherche():
    nom = request.args.get("nom", "").strip()
    matricule = request.args.get("matricule", "").strip()
    annee = request.args.get("annee", "").strip()
    province = request.args.get("province", "").strip().lower()
    try:
        page = int(request.args.get("page", 1) or 1)
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get("per_page", 15) or 15)
    except ValueError:
        per_page = 15
    if per_page > 100:
        per_page = 100

    if not province:
        return jsonify({
            "status": "ERROR",
            "error": "Paramètre 'province' requis",
            "provinces_disponibles": list(PROVINCE_APIS.keys())
        }), 400

    if province not in PROVINCE_APIS:
        return jsonify({
            "status": "ERROR",
            "error": f"Province '{province}' non reconnue",
            "provinces_disponibles": list(PROVINCE_APIS.keys())
        }), 400

    if not nom and not matricule:
        return jsonify({
            "status": "ERROR",
            "error": "Paramètre 'nom' ou 'matricule' requis",
            "exemple": "/api/bacc/recherche?nom=Miora&province=fianarantsoa"
        }), 400

    if matricule:
        search_term = matricule.strip()
        mode = "matricule"
    else:
        if province == "fianarantsoa":
            # L'API de Fianarantsoa est sensible à la casse : on conserve le nom tel quel
            search_term = " ".join(nom.strip().split())
        else:
            search_term = normalize_name(nom)
        mode = "nom"

    result = search_bacc(province, search_term, mode, annee or None)

    # Appliquer la pagination si la recherche a réussi
    if result.get("status") == "OK" and isinstance(result.get("results"), list):
        paginated = paginate_results(result["results"], page, per_page)
        # Remplacer 'count' (nombre de résultats de la source) par le total réel paginé
        result["count"] = len(result["results"])
        result["results"] = paginated["items"]
        result["pagination"] = paginated["pagination"]

    return jsonify(result)


@app.route("/api/bacc/provinces")
def provinces():
    return jsonify({
        "status": "OK",
        "count": len(PROVINCE_INFO),
        "provinces": [
            {
                "code": code,
                "nom": info["nom"],
                "universite": info["universite"],
                "disponible": info["disponible"],
                "note": info.get("note"),
                "api": PROVINCE_APIS.get(code),
                "source": PROVINCE_APIS.get(code)
            }
            for code, info in PROVINCE_INFO.items()
        ]
    })
