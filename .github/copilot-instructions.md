# AI Copilot Instructions for Streamnotify on Bluesky

> **Note**: This file contains relative links to project documentation. Links reference files at `../v2/` and `../OLD_App/` from this `.github/` directory.

## Project Overview
**Streamnotify on Bluesky** is a Python application that monitors multiple streaming platforms (Twitch, YouTube, Niconico) via RSS feeds and automatically posts notifications to Bluesky. The codebase follows a **plugin architecture** for extensibility and supports multiple operation modes.

### Active Version
- **v2/** is the current production version (recommended for all work)
- v1/ and OLD_App/ are legacy versions (reference only)

---

## Architecture Essentials

### 1. Plugin-First Design
The system is built around a **plugin system** for notifications and extensions:

- **Plugin Interface** (v2/plugin_interface.py): All plugins inherit from `NotificationPlugin` abstract base class
  - Required methods: `is_available()`, `post_video()`, `get_name()`, `get_version()`

- **Plugin Manager** (v2/plugin_manager.py): Dynamically discovers and loads plugins from `v2/plugins/` directory
  - Auto-discovers `.py` files (except those starting with `_`)
  - Returns plugin name, path, instance status

- **Built-in Plugins** (v2/plugins/):
  - `bluesky_plugin.py` - Core Bluesky posting with Rich Text support
  - `youtube_api_plugin.py` - YouTube Data API integration (optional, requires API key)
  - `youtube_live_plugin.py` - YouTube live stream monitoring & classification
  - `niconico_plugin.py` - Niconico platform support
  - `logging_plugin.py` - Enhanced logging infrastructure

- **Asset Management System** (Asset/ directory):
  - `asset_manager.py` - Automatically deploys templates and images for loaded plugins
  - Auto-copies plugin-specific templates from Asset/ to working directories
  - Preserves user modifications (no overwrite of existing files)

**Key Pattern**: Always verify plugin availability with `is_available()` before using. Plugins are loaded lazily and may be disabled based on configuration.

### 2. Data Flow Pipeline
```
YouTube RSS Feed (youtube_rss.py)
        ↓
   Database (database.py - SQLite)
        ↓
   GUI Selection (gui_v2.py - tkinter)
        ↓
   Plugin Manager (plugin_manager.py)
        ↓
   Individual Plugins (Bluesky, Niconico, etc.)
```

- RSS feeds are fetched and video metadata is stored in SQLite
- Users select videos in GUI for manual posting or auto-posting
- Plugins handle the actual notification delivery

### 3. Core Modules
- **main_v2.py**: Application entry point; initializes config, database, plugins, and GUI
- **config.py**: Loads `.env` (via dotenv), manages operation modes, validates settings
- **database.py**: SQLite singleton with multiprocess-safe timeout/retry logic
- **bluesky_core.py**: Low-level Bluesky API client (Rich Text, image embedding) - used by plugins
- **gui_v2.py**: tkinter-based management interface (1333 lines)

---

## Operation Modes (config.py)
Specified via `OPERATION_MODE` env var. Each disables/enables different features:

| Mode | Collection | Manual Post | Auto Post | Use Case |
|------|:---:|:---:|:---:|---|
| `normal` | ✓ | ✓ | ✗ | Default - user controls posting |
| `auto_post` | ✓ | ✓ | ✓ | Auto-post matching videos |
| `collect` | ✓ | ✗ | ✗ | Data gathering only |
| `dry_run` | ✓ | ✓ | ✗ | Debug mode (no actual posts) |

Bluesky posting disabled in `collect` and `dry_run` modes.

---

## Configuration & Secrets
- **settings.env.example**: Template for all configuration
- **Key environment variables**:
  - `YOUTUBE_CHANNEL_ID` (required) - Channel ID starting with "UC"
  - `YOUTUBE_API_KEY` (optional) - Enables YouTube Data API plugin if present
  - `BLUESKY_USERNAME`, `BLUESKY_PASSWORD` - Required for Bluesky posting
  - `OPERATION_MODE` - See Operation Modes section above
  - `DEBUG_MODE` - Enables DEBUG-level logging

Load config in code with: `from config import get_config; config = get_config("settings.env")`

---

## Critical Patterns & Conventions

### 1. Logging Architecture
- **Three logger streams**: `AppLogger` (general), `PostLogger` (post events), `GUILogger` (interface events)
- Setup via **logging_config.py** which auto-detects logging plugin
- **Important**: Logging plugin takes precedence if available; falls back to console/file rotation
- Use emoji prefixes in log messages: ✅ success, ❌ error, 🔍 debug, 📦 plugin events, ⚠️ warnings, 🧪 dry run

### 2. Singleton Pattern
- `Database` uses singleton pattern via `__new__()` - only one instance per process
- Access via: `from database import get_database; db = get_database()`
- Handles multiprocess DB lock timeouts (10s timeout, 3 retry max)

### 3. Plugin Discovery & Loading
```python
# In plugin_manager.py
plugins = manager.discover_plugins()  # Returns List[Tuple[str, str]]
plugin = manager.load_plugin(name, path)
if plugin.is_available():
    plugin.post_video(video_dict)
```
- Plugins must be in `v2/plugins/` directory
- Dynamic import via `importlib.util.spec_from_file_location()`
- Failed loads are logged but don't crash the app

### 4. Video Data Structure
Standard dict passed to plugins via `post_video()`:
```python
{
    "title": str,           # Video title
    "video_id": str,        # Platform-specific ID
    "video_url": str,       # Full URL to video
    "published_at": str,    # ISO format timestamp
    "channel_name": str,    # Creator/channel name
    "platform": str,        # "YouTube", "Niconico", etc.
    # Additional fields as needed per plugin
}
```

### 5. Rich Text in Bluesky Posts
**bluesky_core.py** implements Rich Text with facets:
- URL detection and facet generation
- Hashtag support
- Mentioned users (@handle)
- See `BlueskyMinimalPoster._build_facets_for_url()` for patterns

---

## Common Tasks & Commands

### Running the Application
```bash
cd v2/
python main_v2.py
```

### Adding a New Plugin
1. Create `v2/plugins/my_plugin.py`
2. Inherit from `NotificationPlugin` (implement all abstract methods)
3. Place in `v2/plugins/` - auto-discovered
4. Example structure:
   ```python
   from plugin_interface import NotificationPlugin

   class MyPlugin(NotificationPlugin):
       def is_available(self) -> bool:
           return os.getenv("MY_API_KEY") is not None

       def post_video(self, video: Dict[str, Any]) -> bool:
           # Implementation
           return True

       def get_name(self) -> str:
           return "MyPlugin"

       def get_version(self) -> str:
           return "1.0.0"
   ```

### Testing Configuration
- Use `DRY_RUN` mode to test without posting
- Check logs in `v2/logs/` directory
- Database file at `v2/data/video_list.db`

### Debugging Database Issues
- Multiprocess-safe with 10s timeout, 3 retries
- Connection pool handled internally via `_get_connection()`
- Never share DB connection across threads - use `get_database()` helper

---

## Files Structure Reference

### Core Module Files

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| main_v2.py | Entry point | `main()`, `run_gui()`, signal handlers |
| config.py | Settings management | `Config`, `OperationMode`, validation |
| database.py | Data persistence | `Database` (singleton), schema migrations |
| plugin_interface.py | Plugin contract | `NotificationPlugin` (ABC) |
| plugin_manager.py | Plugin lifecycle | `PluginManager`, dynamic loading |
| bluesky_core.py | Bluesky API | `BlueskyMinimalPoster`, facet building |
| gui_v2.py | Management UI | `StreamNotifyGUI`, tkinter interface |
| logging_config.py | Log setup | `setup_logging()`, logger factory |
| youtube_rss.py | RSS fetching | YouTube RSS parsing |
| image_manager.py | Image handling | Thumbnail/image caching |
| asset_manager.py | Asset deployment | `AssetManager`, plugin asset management |
| template_utils.py | Template handling | Template rendering utilities |
| template_editor_dialog.py | Template editing | tkinter-based template editor |
| image_processor.py | Image processing | Image optimization/conversion |
| deleted_video_cache.py | Cache management | Deleted video tracking |

### Directory Structure

```
v2/
├── plugins/                      # Plugin implementations
│   ├── bluesky_plugin.py        # Bluesky notification
│   ├── youtube_api_plugin.py    # YouTube Data API (optional)
│   ├── youtube_live_plugin.py   # YouTube live monitoring
│   ├── niconico_plugin.py       # Niconico support
│   └── logging_plugin.py        # Enhanced logging
├── Asset/                        # Shared templates & images
│   ├── templates/               # Template files (auto-deployed)
│   ├── images/                  # Image assets
│   └── README.md                # Asset deployment guide
├── templates/                    # Active templates (working copies)
│   ├── default/
│   ├── youtube/
│   ├── niconico/
│   └── .templates/              # Template backups
├── docs/                         # Documentation
│   ├── README_GITHUB_v2.md      # GitHub README (v2 version)
│   ├── Guides/                  # User guides
│   ├── Technical/               # Technical documentation
│   ├── Local/                   # Local deployment info
│   ├── References/              # Reference materials
│   └── ARCHIVE/                 # Archived documentation
├── data/                         # Runtime data
│   └── video_list.db            # SQLite database
├── logs/                         # Application logs
├── thumbnails/                   # Cached video thumbnails
├── images/                       # Image storage
└── [Core files listed above]
```

---

## Language & Encoding Notes
- **Primary language**: Japanese (comments, logs, UI)
- **File encoding**: UTF-8 with LF line endings (not CRLF)
- Logging config uses custom handler `LFRotatingFileHandler` to enforce LF
- Exception messages in logs use emoji + Japanese

---

## Dependency Notes
- **Core**: atproto (Bluesky SDK), python-dotenv, feedparser, requests, Pillow, beautifulsoup4
- **GUI**: tkinter (stdlib, no extra install needed)
- **Optional**: Logging plugin can extend logging capabilities

---

## When Extending the System

✅ **DO**:
- Always check plugin `is_available()` before calling methods
- Add video data fields to the standard dict, don't replace it
- Log with emoji prefix: `logger.info("✅ Task completed")`
- Test new plugins in `DRY_RUN` mode first
- Use `get_database()` helper, never create DB instances directly
- Preserve plugin interface contract - don't change abstract methods

❌ **DON'T**:
- Create multiple `Database` instances (use singleton via `get_database()`)
- Share DB connections across threads
- Modify plugin discovery mechanism without updating plugin_manager.py
- Post directly from non-plugin code (use plugin layer)
- Hardcode paths - use `Path` from pathlib or relative to app root

---

## Questions? Reference These First

### Project Overview & Setup
- **Main README**: See [README.md](../README.md) for project overview and quick start
- **v2 Main Documentation**: See [v2/docs/README_GITHUB_v2.md](../v2/docs/README_GITHUB_v2.md) for comprehensive v2 documentation
- **VS Code Workspace**: See [Streamnotify_on_Bluesky.code-workspace](../Streamnotify_on_Bluesky.code-workspace) for workspace settings

### Architecture & Design
- **Architecture**: See [OLD_App/document/ARCHITECTURE.ja.md](../OLD_App/document/ARCHITECTURE.ja.md)
- **Plugin System**: See [v2/plugin_interface.py](../v2/plugin_interface.py) and [v2/docs/Technical/PLUGIN_SYSTEM.md](../v2/docs/Technical/PLUGIN_SYSTEM.md)
- **Template System**: See [v2/docs/Technical/TEMPLATE_SYSTEM.md](../v2/docs/Technical/TEMPLATE_SYSTEM.md)

### Configuration & Assets
- **Config example**: See [v2/settings.env.example](../v2/settings.env.example)
- **Asset deployment**: See [v2/Asset/README.md](../v2/Asset/README.md) and [v2/docs/Technical/ASSET_MANAGER_INTEGRATION_v2.md](../v2/docs/Technical/ASSET_MANAGER_INTEGRATION_v2.md)
- **Database schema**: See [v2/database.py](../v2/database.py) `_init_db()` method

### Implementation Guides
- **Technical guides**: See [v2/docs/Technical/](../v2/docs/Technical/) for detailed implementation guides
- **User guides**: See [v2/docs/Guides/](../v2/docs/Guides/) for setup and usage instructions
- **Development guidelines**: See [v2/docs/Technical/DEVELOPMENT_GUIDELINES.md](../v2/docs/Technical/DEVELOPMENT_GUIDELINES.md)
