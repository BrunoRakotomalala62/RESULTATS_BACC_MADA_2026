# 🎓 API Bacc Madagascar - REST API

API REST pour consulter les résultats du Baccalauréat à Madagascar, basée sur les APIs officielles des universités et du portail national. La source Antananarivo est récupérée depuis la page officielle de l'[Université d’Antananarivo](https://www.univ-antananarivo.mg/resultats-bac).

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
GET /api/bacc/recherche?nom=RAKOTO&province=antananarivo&annee=2026
```

**Paramètres :**
| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `nom` | Nom et prénom du candidat | `Miora` |
| `matricule` | Numéro d'inscription | `1260219` |
| `province` | Code province | `antsiranana`, `mahajanga`, `toliara`, `toamasina`, `fianarantsoa`, `antananarivo` |
| `annee` | Année de la session, principalement utilisée pour Antananarivo | `2026` |

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
| Antananarivo | `antananarivo` | ✅ Scraping de la page officielle |

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
| Antananarivo | `https://www.univ-antananarivo.mg/resultats-bac` — extraction du tableau rendu ou du tableau embarqué dans le bundle React |

> ℹ️ **Note sur Fianarantsoa** : L'API de l'Université de Fianarantsoa utilise un format différent :
> - Recherche par nom : `GET /api/search/name/{nom}` (sensible à la casse)
> - Recherche par matricule : `GET /api/search/num/{num}`
> - Réponse brute : `{"count": N, "bacc": [{num, nom, mention, serie, centre, resultat}]}`
>
> **Note sur Antananarivo** : la page de l’Université est une application React. Le scraper télécharge la page, tente d’abord d’extraire un tableau HTML, puis inspecte le bundle JavaScript référencé par la page pour lire les résultats embarqués. Les données sont mises en cache pendant cinq minutes et filtrées localement par matricule, nom/prénoms et année. Lorsque la source n’a encore publié aucun candidat, l’API retourne une réponse `OK` avec `results: []` et le message correspondant.

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
