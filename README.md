# 🎓 API Bacc Madagascar - REST API

API REST pour consulter les résultats du Baccalauréat à Madagascar, basée sur les APIs officielles de [bacc.digital.gov.mg](https://bacc.digital.gov.mg/).

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
```

**Paramètres :**
| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `nom` | Nom et prénom du candidat | `RAKOTOMALALA Miora` |
| `matricule` | Numéro d'inscription | `1340023` |
| `province` | Code province | `antsiranana`, `mahajanga`, `toliara`, `toamasina` |

> ⚠️ Si les deux sont fournis, `matricule` est prioritaire.

### 📋 Réponse type
```json
{
  "status": "OK",
  "province": "mahajanga",
  "mode": "matricule",
  "search_term": "1340023",
  "count": 1,
  "results": [
    {
      "id": 24,
      "matricule": "1340023",
      "fullname": "RAKOTOVAZAHA Germinah Aimela",
      "serie": "A1",
      "mention": "Passable",
      "center": "MAHAJANGA I",
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
| Fianarantsoa | `fianarantsoa` | ❌ Site externe |
| Antananarivo | `antananarivo` | ❌ Non disponible |

## 🔧 Fonctionnement

L'API agit comme un **proxy** entre votre application et les APIs officielles de chaque province :

1. Elle reçoit votre requête de recherche
2. Génère automatiquement la clé MD5 requise (`MD5("UGD2024" + searchTerm)`)
3. Interroge l'API de la province correspondante
4. Enrichit et retourne les résultats

### APIs sources

| Province | URL API |
|----------|---------|
| Antsiranana | `https://diego-api.bacc.digital.gov.mg/api/search` |
| Mahajanga | `https://mahajanga-api.bacc.digital.gov.mg/api/search` |
| Toliara | `https://bacc.toliara.digital.gov.mg/api/search` |

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
