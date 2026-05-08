# Guide des Outils - Tower Project

## 📍 Structure des Fichiers

| Chemin | Description |
|--------|-------------|
| `/app` | Working directory (code source) |
| `/home/projects/tower_project` | Dossier principal (prompt, configs) |
| `/home/projects/tower_project/inject` | Prompts injectés (instructions.md, tool.md, notes.md, context_summary.md) |
| `/home/projects/tower_project/generate` | Prompts de génération (summarize.md) |

**Important:** Pour lister le dossier prompt, utiliser `ls /home/projects/tower_project` ou `ls /home/projects/tower_project/inject`.

---

## 📋 Outils Disponibles (24)

### 1. Fichiers

| Outil | Usage | Paramètres |
|-------|-------|------------|
| `read_file` | Lire un fichier | `file_path`, `offset`, `limit` |
| `write_file` | Écrire/créer | `file_path`, `content` |
| `edit_file` | Modifier | `file_path`, `old_string`, `new_string`, `replace_all` |
| `glob` | Trouver fichiers | `pattern`, `path` |
| `grep` | Chercher texte | `pattern`, `path`, `include` |
| `ls` | Lister dossier | `path` |

### 2. Système

| Outil | Usage | Paramètres |
|-------|-------|------------|
| `bash` | Commandes système | `command`, `timeout` |
| `docker` | Gestion containers | `command`, `timeout` |
| `git` | Commandes git | `command`, `repo_path` |
| `pkill` | Tuer processus | `pattern`, `force` |

### 3. Web

| Outil | Usage | Paramètres |
|-------|-------|------------|
| `web_fetch` | Lire page web | `url`, `max_length` |
| `web_search` | Recherche Google | `query`, `num_results` |
| `api_fetch` | Appel API | `url`, `method`, `headers`, `body` |

### 4. Base de Données

| Outil | Usage | Paramètres |
|-------|-------|------------|
| `postgres_query` | Requête SQL | `query`, `params` |
| `postgres_list_tables` | Lister tables | — |
| `postgres_describe_table` | Voir structure | `table` |

### 5. Telegram

| Outil | Usage | Paramètres |
|-------|-------|------------|
| `telegram_send_message` | Message simple | `chat_id`, `text` |
| `telegram_send_notification` | Notification stylée | `chat_id`, `title`, `message`, `notification_type` |
| `telegram_get_user_info` | Info utilisateur | `chat_id` |
| `telegram_bot_health` | État du bot | — |

### 6. Scraping & Recherche Vectorielle

| Outil | Usage | Paramètres |
|-------|-------|------------|
| `scrape_and_store` | Scraper et indexer URLs | `urls`, `collection_name`, `user_id`, `max_length`, `dry_run` |
| `search_stored_content` | Rechercher dans collection | `query`, `collection_name`, `limit`, `score_threshold` |

### 7. NAS Synology

| Outil | Usage | Paramètres |
|-------|-------|------------|
| `nas_list_share` | Lister shares | — |
| `nas_list_folder` | Contenu dossier | `folder_path` |
| `nas_search` | Chercher fichier | `folder_path`, `keyword` |

### 8. Modèle & Notes

| Outil | Usage | Paramètres |
|-------|-------|------------|
| `model_switch` | Changer de modèle | `action` (list/switch), `model_id` |
| `user_write_notes` | Écrire notes | `content` |

---

## 🔥 Workflows Courants

### Docker
```bash
docker(command="ps -a")
docker(command="logs tower_qdrant")
docker(command="restart tower_ollama")
```

### PostgreSQL
```bash
postgres_query(query="SELECT * FROM users LIMIT 10")
postgres_list_tables()
postgres_describe_table(table="users")
```

### Fichiers
```bash
read_file(file_path="/home/projects/tower_project/docker-compose.yml")
edit_file(file_path="/home/projects/tower_project/.env", old_string="DEBUG=True", new_string="DEBUG=False")
grep(pattern="ERROR", path="/home/projects/tower_project", include="*.log")
```

### NAS
```bash
nas_list_share()
nas_list_folder(folder_path="/chat")
nas_search(folder_path="/chat", keyword="backup")
```

### Web
```bash
web_search(query="docker container unhealthy fix", num_results=5)
web_fetch(url="https://api.example.com/health", max_length=4000)
```

---

## ✅ Checklist Avant Action

1. **Permission** — Ai-je les droits ?
2. **Impact** — Ça peut-il casser quelque chose ?
3. **Backup** — Données critiques sauvegardées ?
4. **Rollback** — Comment annuler si échec ?

---

## 🚨 Anti-Patterns

| Erreur | Solution |
|--------|----------|
| DELETE sans WHERE | SELECT d'abord |
| docker rm -f sans backup | Exporter avant |
| API sans timeout | Toujours timeout |

---

**📍 Chemin:** `/home/projects/tower_project/prompt/inject/tool.md`
