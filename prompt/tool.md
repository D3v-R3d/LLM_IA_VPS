# 🛠️ Tool Usage Guide - Tower Project

**Utilisateur:** Red  
**Localisation:** Ajaccio, France  
**Dernière mise à jour:** 2025-12-28

---

## 📋 Table des Matières

| # | Section | Description |
|---|---------|-------------|
| 1 | [Quick Reference](#1-quick-reference) | Commandes courantes |
| 2 | [Docker](#2-docker) | Gestion des 6 containers |
| 3 | [PostgreSQL](#3-postgresql) | Requêtes et tables |
| 4 | [NAS Synology](#4-nas-synology) | Accès aux shares |
| 5 | [Telegram](#5-telegram) | Notifications |
| 6 | [Fichiers](#6-fichiers) | Manipulation locale |
| 7 | [Web & API](#7-web--api) | Recherches et appels |
| 8 | [Checklist](#8-checklist) | Validation avant action |

---

## 1. Quick Reference

### 🔥 Commandes les Plus Utilisées

| Tool | Usage Typique | Exemple |
|------|---------------|---------|
| `docker` | Vérifier status containers | `docker ps -a` |
| `postgres_query` | Requête SQL | `SELECT * FROM users LIMIT 10` |
| `read_file` | Lire config | `/home/projects/tower_project/docker-compose.yml` |
| `bash` | Commande système | `df -h`, `free -m` |
| `telegram_send_notification` | Alertes | Notification erreur/succès |

---

## 2. Docker

### 🐳 Vos Containers Actifs

| Nom | Image | Port | Status |
|-----|-------|------|--------|
| tower_backend | tower_project-backend | 8000/tcp | Up |
| tower_frontend | tower_project-frontend | - | Up |
| tower_postgres | postgres:15-alpine | 5432/tcp | healthy |
| tower_qdrant | qdrant/qdrant:v1.7.4 | 6333-6334/tcp | unhealthy ⚠️ |
| tower_ollama | ollama/ollama:latest | 11434/tcp | unhealthy ⚠️ |
| traefik-traefik-1 | traefik:latest | - | Up |

### 📌 Workflows Docker

#### Vérifier l'état des containers
```bash
docker ps -a
```

#### Voir les logs d'un container
```bash
docker logs tower_qdrant
docker logs tower_ollama
docker logs tower_backend
```

#### Redémarrer un container
```bash
docker restart tower_qdrant
docker restart tower_ollama
```

#### Inspecter health check
```bash
docker inspect tower_qdrant | grep -A 20 Health
```

#### Nettoyer les containers arrêtés
```bash
docker container prune -f
```

---

## 3. PostgreSQL

### 🗄️ Tables Disponibles

```bash
# Lister toutes les tables
postgres_list_tables
```

### 📊 Requêtes Courantes

| Objectif | Requête |
|----------|---------|
| Voir structure table | `postgres_describe_table(table="nom_table")` |
| Compter lignes | `SELECT COUNT(*) FROM nom_table` |
| Derniers enregistrements | `SELECT * FROM nom_table ORDER BY id DESC LIMIT 10` |
| Vérifier connections | `SELECT * FROM pg_stat_activity` |

### ⚠️ Précautions

| Action | Précaution |
|--------|------------|
| DELETE | Toujours tester avec SELECT d'abord |
| UPDATE | Utiliser WHERE spécifique |
| DROP | Backup avant suppression |

---

## 4. NAS Synology

### 📁 Accès NAS

| Tool | Usage | Exemple |
|------|-------|---------|
| `nas_list_share` | Lister shares | Tous les shares disponibles |
| `nas_list_folder` | Contenu dossier | `/chat`, `/PlexMediaServer` |
| `nas_search` | Chercher fichier | keyword="document", folder_path="/chat" |

### 📌 Workflows NAS

#### Lister tous les shares
```bash
nas_list_share
```

#### Voir contenu d'un dossier
```bash
nas_list_folder(folder_path="/chat")
```

#### Chercher un fichier
```bash
nas_search(folder_path="/chat", keyword="backup")
```

---

## 5. Telegram

### 📱 Notifications

| Tool | Usage | Paramètres |
|------|-------|------------|
| `telegram_send_message` | Message simple | chat_id, text |
| `telegram_send_notification` | Notification stylée | chat_id, title, message, notification_type |
| `telegram_bot_health` | Vérifier bot | Aucun paramètre |
| `telegram_get_user_info` | Info utilisateur | chat_id |

### 📌 Types de Notifications

| Type | Usage |
|------|-------|
| `success` | Opération réussie |
| `error` | Erreur critique |
| `warning` | Attention requise |
| `info` | Information générale |

### Exemple d'envoi
```bash
telegram_send_notification(
  chat_id="YOUR_CHAT_ID",
  title="Alerte Docker",
  message="Container tower_qdrant est unhealthy",
  notification_type="warning"
)
```

---

## 6. Fichiers

### 📄 Manipulation de Fichiers

| Tool | Usage | Exemple |
|------|-------|---------|
| `read_file` | Lire fichier | file_path="/home/projects/tower_project/docker-compose.yml" |
| `write_file` | Écrire fichier | file_path, content |
| `edit_file` | Modifier contenu | file_path, old_string, new_string |
| `glob` | Trouver fichiers | pattern="**/*.py", path="/home/projects" |
| `grep` | Chercher texte | pattern="error", path="/home/projects", include="*.log" |
| `ls` | Lister dossier | path="/home/projects/tower_project" |

### 📌 Workflows Fichiers

#### Lire un fichier de config
```bash
read_file(file_path="/home/projects/tower_project/docker-compose.yml")
```

#### Chercher une erreur dans les logs
```bash
grep(pattern="ERROR", path="/home/projects/tower_project/logs", include="*.log")
```

#### Trouver tous les fichiers Python
```bash
glob(pattern="**/*.py", path="/home/projects/tower_project")
```

#### Modifier une configuration
```bash
edit_file(
  file_path="/home/projects/tower_project/.env",
  old_string="DEBUG=True",
  new_string="DEBUG=False"
)
```

---

## 7. Web & API

### 🌐 Recherches et Appels

| Tool | Usage | Exemple |
|------|-------|---------|
| `search_web` | Recherche Google | query="docker unhealthy container fix" |
| `fetch_url` | Contenu URL | url="https://api.example.com/health" |
| `call_api` | Appel API complet | url, method, headers, body |

### 📌 Workflows Web

#### Recherche rapide
```bash
search_web(query="qdrant health check configuration", num_results=5)
```

#### Fetcher une page
```bash
fetch_url(url="https://qdrant.tech/documentation/", max_length=4000)
```

#### Appel API
```bash
call_api(
  url="https://api.example.com/v1/status",
  method="GET",
  headers={"Authorization": "Bearer token"}
)
```

---

## 8. Checklist

### ✅ Avant d'Exécuter un Tool

| Question | Vérification |
|----------|--------------|
| **Permission** | Ai-je les droits pour cette action ? |
| **Impact** | Cette action peut-elle casser quelque chose ? |
| **Backup** | Ai-je sauvegardé les données critiques ? |
| **Logs** | Est-ce que l'action sera loggée ? |
| **Rollback** | Comment annuler si ça échoue ? |

### ✅ Après l'Exécution

| Question | Vérification |
|----------|--------------|
| **Status** | L'action a-t-elle réussi ? |
| **Logs** | Y a-t-il des erreurs dans les logs ? |
| **Notification** | Dois-je notifier quelqu'un ? |
| **Documentation** | Dois-je documenter ce changement ? |

---

## 🚨 Anti-Patterns à Éviter

| Erreur | Solution |
|--------|----------|
| DELETE sans WHERE | Toujours tester avec SELECT d'abord |
| docker rm -f sans backup | Exporter les données avant |
| edit_file sans validation | Lire le fichier avant modification |
| Notification sans contexte | Inclure timestamp et détails |
| API call sans timeout | Toujours définir un timeout |

---

## 📞 Support & Références

| Ressource | URL |
|-----------|-----|
| Docker Docs | https://docs.docker.com/ |
| PostgreSQL Docs | https://www.postgresql.org/docs/ |
| Synology NAS | https://www.synology.com/ |
| Telegram Bot API | https://core.telegram.org/bots/api |

---

**📍 Chemin:** `/home/projects/tower_project/prompt/tool.md`  
**📏 Taille:** ~6000 bytes  
**📄 Lignes:** ~250
