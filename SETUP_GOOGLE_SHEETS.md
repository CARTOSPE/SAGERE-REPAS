# SAGERE — Guide de configuration Google Sheets

## Pourquoi Google Sheets ?

Sur Streamlit Cloud gratuit, le système de fichiers est **éphémère** : les fichiers JSON
sont effacés à chaque redéploiement. Google Sheets est la solution gratuite et permanente.

---

## ⏱ Temps de configuration : ~15 minutes

---

## ÉTAPE 1 — Créer le Google Sheet

1. Aller sur [sheets.google.com](https://sheets.google.com)
2. Créer un nouveau tableur vide, nommer-le **SAGERE-Données**
3. **Copier l'ID** depuis l'URL :
   ```
   https://docs.google.com/spreadsheets/d/ [ID_ICI] /edit
   ```
4. Créer **3 onglets** (clic droit sur l'onglet "+") nommés exactement :
   - `menus`
   - `commandes`
   - `config`

---

## ÉTAPE 2 — Créer un compte de service Google Cloud

1. Aller sur [console.cloud.google.com](https://console.cloud.google.com)
2. **Créer un projet** (ou utiliser un existant) → nommer-le `sagere`
3. Dans le menu → **APIs & Services** → **Bibliothèque**
4. Rechercher et **activer** :
   - `Google Sheets API`
   - `Google Drive API`
5. Dans **APIs & Services** → **Identifiants** → **Créer des identifiants** → **Compte de service**
   - Nom : `sagere-sheets`
   - Rôle : **Éditeur** (ou laisser vide)
   - Cliquer **Créer**
6. Cliquer sur le compte de service créé → onglet **Clés** → **Ajouter une clé** → **JSON**
7. Un fichier `.json` est téléchargé — **le garder précieusement**

---

## ÉTAPE 3 — Partager le Google Sheet avec le compte de service

1. Ouvrir le fichier JSON téléchargé, copier la valeur `client_email`
   (ressemble à : `sagere-sheets@sagere-xxxxx.iam.gserviceaccount.com`)
2. Ouvrir le Google Sheet **SAGERE-Données**
3. Cliquer **Partager** → coller l'email du compte de service → rôle **Éditeur** → **Envoyer**

---

## ÉTAPE 4 — Configurer les secrets Streamlit

### En local (tests sur votre PC)

Créer le fichier `.streamlit/secrets.toml` à partir du template `.streamlit/secrets.toml.template` :

```toml
[gsheet]
spreadsheet_id = "COLLER_L_ID_DU_GOOGLE_SHEET"

[gcp_service_account]
type = "service_account"
project_id = "..."        # depuis le fichier JSON
private_key_id = "..."    # depuis le fichier JSON
private_key = "..."       # depuis le fichier JSON (toute la clé avec \n)
client_email = "..."      # depuis le fichier JSON
client_id = "..."         # depuis le fichier JSON
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."  # depuis le fichier JSON
```

### Sur Streamlit Cloud

1. Aller sur [share.streamlit.io](https://share.streamlit.io)
2. Sélectionner votre application → **⋮** → **Settings** → **Secrets**
3. Coller le contenu complet du `secrets.toml` (sans les commentaires)
4. Cliquer **Save** → l'application redémarre automatiquement

---

## ÉTAPE 5 — Vérifier que ça fonctionne

1. Lancer l'application : `streamlit run app.py`
2. Aller dans **Passer commande** → choisir un salarié → cocher des plats → **Valider**
3. Ouvrir le Google Sheet → onglet `commandes` → une ligne doit apparaître
4. Redémarrer l'application → les données sont toujours là ✓

---

## Structure des données dans Google Sheets

| Onglet | Colonne A | Colonne B |
|--------|-----------|-----------|
| `menus` | `2026-S27` | `{"semaine":..., "periode":..., "jours":{...}}` |
| `commandes` | `2026-S27` | `{"GHEYSENS Eric":{"Lundi":{"Entrées":[...]},...},...}` |
| `config` | `salaries` | `["GHEYSENS Eric", "CAMPION Pascal", ...]` |
| `config` | `carte` | `{"Entrées":[...], "Plats garnis":[...], ...}` |

---

## ⚠️ Sécurité

- Ne jamais commiter `secrets.toml` sur GitHub (il est dans `.gitignore`)
- Le fichier JSON du compte de service donne accès en écriture au Google Sheet — le garder confidentiel
- Sur Streamlit Cloud, les secrets sont chiffrés et ne sont pas visibles publiquement

---

## 🔧 Dépannage

| Erreur | Solution |
|--------|----------|
| `gspread.exceptions.SpreadsheetNotFound` | Vérifier l'ID du Sheet et le partage avec le compte de service |
| `google.auth.exceptions.TransportError` | Vérifier la connexion internet |
| `ValueError: Invalid service account credentials` | Vérifier le contenu du `secrets.toml`, notamment la `private_key` |
| Les données ne s'affichent pas | Cliquer 🔄 Recharger dans Exports & Admin |
