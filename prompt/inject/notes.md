<!-- User notes will be appended here -->


## Note at 2026-05-09T10:26:09.700142
Le serveur est lent


## Note at 2026-05-09T10:55:46.234555
Format de date et heure pour les réponses : YYYY-MM-DD HH:mm (Europe/Paris).

## Note at 2026-05-09T13:44:41.554264
Test de la commande - Modèle actuel: llama-3.3-70b-versatile. Réponse inattendue.

## Note at 2026-05-09T13:45:06.558575
Liste des tables Postgres:
  - conversations
  - documents
  - llm_logs
  - messages
  - user_model_prefs

## Note at 2026-05-09T13:46:26.262364
Tables Postgres répertoriées : conversations, documents, llm_logs, messages, user_model_prefs

## Note at 2026-05-09T13:46:26.491691
Modèle actuel : llama-3.3-70b-versatile 
Réponse inattendue. Réessayez.

## Note at 2026-05-09T13:46:26.717699
Pas de problème ! Tout va bien. Qu'est-ce que je peux faire pour vous ? 

## Note at 2026-05-09T16:04:21.872090
## Docker Containers - 2026-05-09 15:22

### Container Actif
| Nom | Image | Port | Commande | Statut |
|-----|-------|------|----------|--------|
| /tower_backend | tower_project-backend | 8000/tcp | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | ✅ Actif |

**Container ID :** 55eb6fc64f501c4bc4528ebd3ebc9e67076433fd7ead0161b8309a7b017c0fe2
**Image SHA :** sha256:5e26878adcd9f8015178abf9a3688a4b5206864eed56b820f63a8744a7d8fcbf
**Dépendances :** ollama, postgres, qdrant
**Projet :** tower_project

---

## Partages NAS - 2026-05-09 15:22

| Nom | Chemin | Type |
|-----|--------|------|
| chat | /chat | 📁 Dossier |
| docker | /docker | 📁 Dossier |
| home | /home | 📁 Dossier |
| homes | /homes | 📁 Dossier |
| PlexMediaServer | /PlexMediaServer | 📁 Dossier |
| Storage | /Storage | 📁 Dossier |
| web | /web | 📁 Dossier |
| web_packages | /web_packages | 📁 Dossier |

**Total :** 8 partages disponibles

---

## PostgreSQL - Accès Confirmé

**Tables accessibles :**
- conversations
- documents
- llm_logs
- messages
- user_model_prefs

**Restrictions :** Pas d'accès aux tables système (pg_user, pg_roles)
