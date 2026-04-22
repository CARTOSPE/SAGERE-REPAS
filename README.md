# SAGERE — Version Web (Streamlit)

## 🚀 Déploiement gratuit sur Streamlit Cloud

### Étape 1 — Créer un compte GitHub (gratuit)
1. Aller sur [github.com](https://github.com) → **Sign up**
2. Créer un dépôt public nommé `sagere-repas`
3. Uploader tous les fichiers de ce dossier dans le dépôt

### Étape 2 — Déployer sur Streamlit Cloud (gratuit)
1. Aller sur [share.streamlit.io](https://share.streamlit.io) → **Sign in with GitHub**
2. Cliquer **New app**
3. Sélectionner votre dépôt `sagere-repas`
4. Fichier principal : `app.py`
5. Cliquer **Deploy**

✅ En 2 minutes, l'application est accessible à l'URL :
`https://sagere-repas.streamlit.app`

**Partagez cette URL à vos salariés — aucune installation requise.**

---

## 💻 Lancer en local (test sur votre PC)

```bash
pip install streamlit openpyxl beautifulsoup4
streamlit run app.py
```

L'application s'ouvre automatiquement dans le navigateur sur `http://localhost:8501`

---

## 📁 Structure des fichiers

```
sagere-repas/
├── app.py                    ← Application principale
├── requirements.txt          ← Dépendances (installées automatiquement)
├── .streamlit/
│   └── config.toml           ← Thème et configuration
└── data/                     ← Créé automatiquement au premier lancement
    ├── commandes.json
    ├── menus.json
    ├── salaries.json
    └── carte_permanente.json
```

---

## ⚠️ Note sur les données

Sur Streamlit Cloud gratuit, les fichiers `data/*.json` sont **réinitialisés** à chaque redéploiement.

**Pour des données permanentes (recommandé)**, connecter un Google Sheets ou une base de données externe — me demander si besoin.

Pour un usage en réseau local uniquement (données persistantes sans configuration) : lancer en local avec `streamlit run app.py`.

---

## 🔄 Workflow hebdomadaire

1. **Lundi matin** : aller sur `⚙ Saisir le menu` → importer le `.xls` du traiteur
2. **Dans la journée** : chaque salarié ouvre l'URL, choisit son nom, coche ses plats, valide
3. **Avant la deadline** : `📊 Exports & Admin` → Télécharger le bon de commande → l'envoyer au traiteur
