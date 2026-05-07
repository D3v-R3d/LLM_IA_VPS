# Synology NAS Services

Synology NAS API integration for file operations. Uses FileStation API with session-based authentication.

## Architecture

```
SynologyNAS
├── SynologyClient  → HTTP client with cookie-based session
├── SynologyAuth    → Authentication (login/logout/check)
└── FileStation     → File operations via FileStation API
```

## Configuration

Reads credentials from Docker secrets via files:
- `SYNOLOGY_USERNAME_FILE` - Path to username secret file
- `SYNOLOGY_PASSWORD_FILE` - Path to password secret file

Environment variables (with `SYNOLOGY_` prefix):
| Variable | Default | Description |
|----------|---------|-------------|
| `host` | (required) | NAS hostname/IP |
| `port` | 5001 | API port |
| `protocol` | https | HTTP protocol |
| `timeout` | 30 | Request timeout (seconds) |

## Services

### SynologyClient (`client.py`)

HTTP client for Synology API. Maintains persistent session with cookie storage.

**Key Methods:**
- `request(method, path, params, data, json)` - Make authenticated API request
- `get(path, params)` - GET request
- `post(path, params, data, json)` - POST request
- `set_sid(sid)` / `clear_session()` - Session management
- `close()` - Close session

**Error Handling:**
- `SynologyConnectionError` - Connection/timeout/HTTP errors
- Returns `{'error': {'code': 103}, 'success': False}` for HTML error pages

### SynologyAuth (`auth.py`)

Authentication manager using `SYNO.API.Auth` API.

**Key Methods:**
- `login(username, password, session)` - Authenticate, returns SID
- `logout()` - End session
- `check()` - Validate current session

```python
from app.services.synology import SynologyClient, SynologyAuth

client = SynologyClient()
auth = SynologyAuth(client)
sid = auth.login()  # Uses config credentials
```

### FileStation (`file_station.py`)

FileStation API client for file browsing and searching.

**Key Methods:**
- `list_shares()` - List all shared folders/volumes
- `list_folders(folder_path, offset, limit, sort_by, sort_direction)` - List directory contents
- `list_files(folder_path, pattern, filetype, ...)` - List files (not dirs)
- `get_file_info(path)` - Get detailed file/folder info
- `search(folder_path, keyword, filetype, limit)` - Search files by name

```python
from app.services.synology import SynologyClient, SynologyAuth, FileStation

client = SynologyClient()
auth = SynologyAuth(client)
auth.login()

nas = FileStation(client)
shares = nas.list_shares()
nas.list_folders("/chat")
nas.search("/documents", "*.pdf")
```

## Exceptions

| Exception | Cause |
|-----------|-------|
| `SynologyConnectionError` | Cannot connect, timeout, HTTP errors |
| `SynologyAuthError` | Login failed |
| `SynologyApiError` | API returned error |

## Usage

```python
from app.services.synology import SynologyClient, SynologyAuth, FileStation

# Setup
client = SynologyClient()
auth = SynologyAuth(client)
auth.login()

# File operations
nas = FileStation(client)
result = nas.list_shares()
result = nas.list_folders("/chat")
result = nas.search(folder_path="/documents", keyword="report", filetype="file")
```

## Key Files

| File | Description |
|------|-------------|
| `client.py` | HTTP client with session management |
| `auth.py` | Authentication manager |
| `file_station.py` | FileStation API wrapper |
| `config.py` | Settings from env/secrets |
| `exceptions.py` | Custom exception classes |
| `__init__.py` | Module exports |