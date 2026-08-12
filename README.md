# 🎓 API Bacc Madagascar - REST API

API REST pour consulter les résultats du Baccalauréat à Madagascar, basée sur les APIs officielles de [bacc.digital.gov.mg](https://bacc.digital.gov.mg/) et [bacc.univ-fianarantsoa.mg](https://bacc.univ-fianarantsoa.mg/).

## 🚀 Démarrage rapide

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
python server.py

# Serveur démarré sur http://localhost:5000
```

## 📡 Endpoints

### 🔍 Rechercher des résultats
```
GET /api/bacc/recherche?nom=RAKOTOMALALA Miora&province=antsiranana
GET /api/bacc/recherche?matricule=1340023&province=mahajanga
GET /api/bacc/recherche?nom=Miora&province=fianarantsoa
GET /api/bacc/recherche?matricule=1260219&province=fianarantsoa
```

**Paramètres :**
| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `nom` | Nom et prénom du candidat | `Miora` |
| `matricule` | Numéro d'inscription | `1260219` |
| `province` | Code province | `antsiranana`, `mahajanga`, `toliara`, `toamasina`, `fianarantsoa` |

> ⚠️ Si les deux sont fournis, `matricule` est prioritaire.

### 📋 Réponse type (Fianarantsoa)
```json
{
  "status": "OK",
  "province": "fianarantsoa",
  "mode": "nom",
  "search_term": "Miora",
  "count": 68,
  "results": [
    {
      "matricule": "1260219",
      "fullname": "MIORA Niaina",
      "serie": "A1",
      "mention": "Passable",
      "center": "FIANARANTSOA 301",
      "admis": 1,
      "admis_label": "Admis(e)"
    }
  ]
}
```

### 🗺️ Provinces disponibles
```
GET /api/bacc/provinces
```

## 🏛️ Provinces supportées

| Province | Code | Statut |
|----------|------|--------|
| Antsiranana (Diego) | `antsiranana` | ✅ Disponible |
| Mahajanga | `mahajanga` | ✅ Disponible |
| Toliara | `toliara` | ✅ Disponible |
| Toamasina | `toamasina` | ⚠️ Redirigé vers Mahajanga |
| Fianarantsoa | `fianarantsoa` | ✅ Disponible |
| Antananarivo | `antananarivo` | ❌ Non disponible |

## 🔧 Fonctionnement

L'API agit comme un **proxy** entre votre application et les APIs officielles de chaque province :

1. Elle reçoit votre requête de recherche
2. Génère automatiquement la clé MD5 requise (`MD5("UGD2024" + searchTerm)`) pour les provinces `bacc.digital.gov.mg`
3. Interroge l'API de la province correspondante
4. Enrichit et retourne les résultats

### APIs sources

| Province | URL API |
|----------|---------|
| Antsiranana | `https://diego-api.bacc.digital.gov.mg/api/search` |
| Mahajanga | `https://mahajanga-api.bacc.digital.gov.mg/api/search` |
| Toliara | `https://bacc.toliara.digital.gov.mg/api/search` |
| Fianarantsoa | `https://bacc.univ-fianarantsoa.mg/api/search/{type}/{terme}` où `{type}` = `name` ou `num` |

> ℹ️ **Note sur Fianarantsoa** : L'API de l'Université de Fianarantsoa utilise un format différent :
> - Recherche par nom : `GET /api/search/name/{nom}` (sensible à la casse)
> - Recherche par matricule : `GET /api/search/num/{num}`
> - Réponse brute : `{"count": N, "bacc": [{num, nom, mention, serie, centre, resultat}]}`

## 📦 Déploiement Vercel

```bash
vercel --prod
```

La configuration `vercel.json` est déjà incluse.

## 📝 Structure du projet

```
bacc-api/
├── server.py          # API principale (Flask)
├── requirements.txt   # Dépendances Python
├── vercel.json        # Configuration Vercel
├── api/
│   └── index.py       # Point d'entrée WSGI
└── README.md
```
