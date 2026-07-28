#!/usr/bin/env python3
"""
API REST - Résultats du Baccalauréat Madagascar
================================================
Proxy API pour interroger les résultats du Bacc à Madagascar par province.

Endpoints:
  GET /api/bacc/recherche?nom=XXX&province=YYY
  GET /api/bacc/recherche?matricule=XXX&province=YYY
  GET /api/bacc/provinces

Basé sur les APIs officielles de bacc.digital.gov.mg :
  - Antsiranana : https://diego-api.bacc.digital.gov.mg/api
  - Mahajanga   : https://mahajanga-api.bacc.digital.gov.mg/api
  - Toliara     : https://bacc.toliara.digital.gov.mg/api
"""

import hashlib
import os
from flask import Flask, jsonify, request
import requests
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SECRET_KEY = "UGD2024"  # Clé secrète utilisée par l'API officielle

PROVINCE_APIS = {
    "antsiranana": "https://diego-api.bacc.digital.gov.mg/api",
    "mahajanga":   "https://mahajanga-api.bacc.digital.gov.mg/api",
    "toamasina":   "https://mahajanga-api.bacc.digital.gov.mg/api",  # redirige vers Mahajanga
    "toliara":     "https://bacc.toliara.digital.gov.mg/api",
}

PROVINCE_INFO = {
    "antsiranana": {"nom": "Antsiranana (Diego)",   "universite": "Oniversite Antsiranana",   "disponible": True},
    "mahajanga":   {"nom": "Mahajanga",             "universite": "Oniversite Mahajanga",     "disponible": True},
    "toamasina":   {"nom": "Toamasina",             "universite": "Oniversite Toamasina",     "disponible": False, "note": "Redirigé vers Mahajanga"},
    "toliara":     {"nom": "Toliara",               "universite": "Oniversite Toliara",       "disponible": True},
    "fianarantsoa":{"nom": "Fianarantsoa",          "universite": "Oniversite Fianarantsoa",  "disponible": False, "note": "Site externe"},
    "antananarivo":{"nom": "Antananarivo",          "universite": "Oniversite Antananarivo",  "disponible": False, "note": "Non disponible"},
}

# Session HTTP avec retry
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
})

# ---------------------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)  # Activer CORS pour permettre l'accès depuis n'importe quel domaine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_key(search_term: str) -> str:
    """
    Génère la clé MD5 utilisée par l'API officielle.
    key = MD5(UGD2024 + searchTerm)
    """
    return hashlib.md5(f"{SECRET_KEY}{search_term}".encode()).hexdigest()


def normalize_name(name: str) -> str:
    """
    Nettoie et normalise un nom pour la recherche.
    Supprime les espaces en trop, met en majuscules.
    """
    return " ".join(name.strip().upper().split())


def search_bacc(province: str, search_term: str, mode: str = "nom") -> dict:
    """
    Effectue une recherche dans l'API du Baccalauréat.
    
    Args:
        province: Code de la province (antsiranana, mahajanga, toliara...)
        search_term: Terme de recherche (nom complet ou matricule)
        mode: "nom" (par nom) ou "matricule" (par numéro d'inscription)
    
    Returns:
        dict: Résultat de la recherche
    """
    if province not in PROVINCE_APIS:
        return {"error": f"Province inconnue: {province}", "status": "ERROR"}

    api_base = PROVINCE_APIS[province]
    key = generate_key(search_term)

    if mode == "matricule":
        params = {"matricule": search_term, "key": key}
    else:
        params = {"nom": search_term, "key": key}

    try:
        resp = session.get(
            f"{api_base}/search",
            params=params,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()

        # L'API retourne {"status": "OK", "data": [...]}
        if data.get("status") == "OK":
            results = data.get("data", [])
            # Enrichir les résultats avec des infos lisibles
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
    """Documentation de l'API."""
    return jsonify({
        "api": "Bacc Madagascar - API REST",
        "version": "1.0.0",
        "description": "API pour consulter les résultats du Baccalauréat à Madagascar",
        "source": "https://bacc.digital.gov.mg/",
        "endpoints": {
            "GET /api/bacc/recherche": "Rechercher des résultats par nom ou matricule",
            "GET /api/bacc/provinces": "Lister les provinces disponibles",
        },
        "exemples": {
            "par_nom": "/api/bacc/recherche?nom=RAKOTOMALALA%20Miora&province=antsiranana",
            "par_matricule": "/api/bacc/recherche?matricule=1340023&province=mahajanga",
        },
        "provinces_disponibles": list(PROVINCE_APIS.keys()),
    })


@app.route("/api/bacc/recherche")
def recherche():
    """
    Recherche les résultats du Baccalauréat.
    
    Paramètres:
        nom (str):        Nom et prénom du candidat (ex: "RAKOTOMALALA Miora")
        matricule (str):  Numéro d'inscription (ex: "1340023")
        province (str):   Code province: antsiranana, mahajanga, toliara, toamasina
    
    Note: Utilisez soit "nom" soit "matricule", pas les deux.
          Si les deux sont fournis, "matricule" est prioritaire.
    """
    nom = request.args.get("nom", "").strip()
    matricule = request.args.get("matricule", "").strip()
    province = request.args.get("province", "").strip().lower()

    # Validation
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
            "exemple": "/api/bacc/recherche?nom=RAKOTOMALALA Miora&province=antsiranana"
        }), 400

    # Mode matricule prioritaire si les deux sont fournis
    if matricule:
        search_term = matricule.strip()
        mode = "matricule"
    else:
        search_term = normalize_name(nom)
        mode = "nom"

    result = search_bacc(province, search_term, mode)
    return jsonify(result)


@app.route("/api/bacc/provinces")
def provinces():
    """Liste les provinces disponibles avec leur statut."""
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
                "api": PROVINCE_APIS.get(code)
            }
            for code, info in PROVINCE_INFO.items()
        ]
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    print(f"🚀 API Bacc Madagascar - http://localhost:{port}")
    print(f"📖 Documentation : http://localhost:{port}/")
    print(f"🔍 Recherche : http://localhost:{port}/api/bacc/recherche?nom=RAKOTO&province=mahajanga")
    app.run(host="0.0.0.0", port=port, debug=debug)
