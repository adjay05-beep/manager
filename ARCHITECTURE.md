# Project Architecture & Map

**Last Updated:** 2026-02-03
**Version:** 2.1 (Feature Sync)

This document maps the **The Manager** project's structure, data flow, and infrastructure rules. It serves as the single source of truth for understanding the application's design.

## 1. 🏗️ The Big Picture (System Design)

The application follows a strict **Service-Repository Pattern** to ensure separation of concerns.

```mermaid
graph TD
    User((User)) --> View[FE: Views (Flet UI)]
    View --> Router[Service: Router]
    View --> Service[Service: Business Logic]
    
    subgraph "Application Core"
    Service --> Repo[Repository: Data Access]
    Service --> State[State: page.app_session]
    end
    
    subgraph "Infrastructure"
    Repo --> Supabase[(Supabase DB)]
    Main[main.py] --> Flet[Flet Runtime]
    Main --> Patch[Runtime Patches]
    end
```

### Core Design Principles
1.  **UI/Logic Separation**: Views never touch the Database. They only call Services.
2.  **State Management**:
    *   **Session State**: `page.app_session` (User ID, Channel ID) - Cleared on logout.
    *   **Persistent State**: `page.client_storage` (Theme, Auto-login Tokens) - Persists across restarts.
3.  **Logical Navigation**: structural navigation (Home -> Feature) over browser history.

---

## 2. 📂 Detailed Structure (The Map)

### 🟢 Presentation Layer (`views/`)
*   **Role**: Renders UI, handles user input, delegates to Services.
*   **Key Files**:
    *   `main.py`: Entry point. Contains **Infrastructure Patches** (see Section 4).
    *   `attendance_view.py`: GPS/Wi-Fi verified clock-in/out.
    *   `chat_view.py`: Real-time chat interface.
    *   `voice_view.py`: Dual-mode voice recording.
    *   `handover_view.py`: Operational logs with data hashing.
    *   `closing_view.py`: Operational checklist for store closing.
    *   `store_manage_view.py`: Store information and channel management.
    *   `profile_view.py`: User profile and identity display.

### 🔵 Business Logic Layer (`services/`)
*   **Role**: Validates rules, processes data, orchestrates multiple Repositories.
*   **Key Services**:
    *   `router.py`: Centralized navigation & overlay management (Dialog cleanup).
    *   `chat_service.py`: **Performance Optimized** (ThreadPool for N+1 queries).
    *   `voice_service.py`: Manages transcribing and memo lifecycle.
    *   `payroll_service.py`: Complex salary calculations.

### 🟠 Data Access Layer (`repositories/`)
*   **Role**: Pure SQL/Supabase interactions. Singleton pattern.
*   **Files**: `auth_repository.py`, `chat_repository.py`, `channel_repository.py`, etc.
*   **Rule**: functions here return raw Dicts or Supabase Responses, not Flet Controls.

### 🟣 Tooling & Scripts (`scripts/`)
*   **Role**: Verification, Maintenance, and Migration tools.
*   **Scope**: 50+ scripts for verifying logic (`verify_read_logic.py`), DB integrity, and deployment checks.

---

## 3. ⚡ Key Mechanisms & Flows

### Navigation Flow (Logical Back)
*   **Rule**: Sub-pages (Profile, Settings, Detail Views) must return to **HOME**, not the previous browser history page.
*   **Implementation**: `on_back_click=lambda _: navigate_to("home")`
*   **Reason**: Prevents users from getting stuck in a loop or returning to a login screen.

### Voice Recording Strategy (Hybrid)
*   **Web (Browser)**: Uses **Web Speech API** (JavaScript injection).
    *   *Why?* Browsers block direct mic access for Python threads.
*   **Desktop (Windows)**: Uses **AudioRecorder** (Flet component).
    *   *Why?* Native quality is better and supports file saving.

### Performance Optimization
1.  **Handover View**: Implements **Data Hashing (MD5)**.
    *   UI only re-renders if the fetched data hash changes. Prevents 10s "freeze".
2.  **Chat Unread Counts**: Uses **ThreadPoolExecutor**.
    *   Parallels N+1 DB queries for "never read" topics.

---

## 4. 🔧 Infrastructure & Runtime Patches (`main.py`)

Current Flet/System environment requires specific patches injected at runtime in `main.py`. **Do NOT remove these.**

| Patch Name | Target | Reason |
| :--- | :--- | :--- |
| **WebSocket Fix** | `starlette.websockets.receive_bytes` | Fixes `KeyError: 'bytes'` crash due to Flet/Starlette version mismatch. Filters non-bytes frames. |
| **Page.open Polyfill** | `ft.Page.open` | Adds support for `page.open(dlg)` syntax on Flet versions where it is missing/deprecated. |
| **Deprecation Silence** | `ft.app` | Handling of `DeprecationWarning` for older `ft.app` usage until migration to `ft.run_app`. |

---

## 5. 🚀 Deployment Rules
1.  **Environment**: Requires `FLET_SECRET_KEY` for secure uploads.
2.  **Port**: Defaults to `8555`, respects `$PORT` env var.
3.  **Uploads**: `uploads/` directory must be writable.

---
*Maintained by Antigravity AI*
