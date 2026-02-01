# Project Architecture & Adaptation Guide

This document maps the project's structure, data flow, and coding rules to help AI assistants and developers maintain consistency.

## 🏗️ System Overview
**The Manager** is a cross-platform application (Mobile/Desktop) built with **Flet (Python)** for the frontend and **Supabase** for the backend/database.

### Core Architecture Pattern
The project follows a **Service-Repository Pattern** to separate UI, Business Logic, and Data Access.

```mermaid
graph TD
    UI[Views (Flet UI)] --> Service[Services (Business Logic)]
    Service --> Repos[Repositories (Data Access)]
    Repos --> Supabase[(Supabase DB)]
    
    subgraph Frontend
    UI
    end
    
    subgraph Application
    Service
    end
    
    subgraph Backend
    Repos
    end
```

## 📂 Directory Structure Rules

| Directory | Responsibility | Application Rules |
|-----------|----------------|-------------------|
| `views/` | **UI Only.** Returns Flet Controls. | ❌ No direct DB calls.<br>❌ No complex logic.<br>✅ Call `Service` for data. |
| `services/` | **Business Logic.** Process data, handle errors. | ✅ Manage application state (e.g., `current_user`).<br>✅ Handle exceptions from Repos.<br>❌ No Flet UI code (pure Python). |
| `repositories/` | **Data Access.** Interact with Supabase. | ✅ Singleton pattern.<br>✅ Direct Supabase API calls.<br>❌ No business logic. |
| `main.py` | **Entry Point.** Routing & Setup. | ✅ Initialize App.<br>✅ Define Routes.<br>❌ Avoid massive inline logic. |

## 🔄 Data Flow Guidelines

1.  **User Action**: User clicks a button in `views/home_view.py`.
2.  **View Layer**: `HomeView` calls `AuthService.sign_in()`.
3.  **Service Layer**: `AuthService` logic runs (validates input), then calls `AuthRepository.sign_in()`.
4.  **Repository Layer**: `AuthRepository` calls `supabase.auth.sign_in_with_password()`.
5.  **Return Path**: Data flows back up. Errors are caught in `Service` and returned as user-friendly messages or raised to `View` for strict handling.

## ⚠️ Critical Development Rules (AI Instructions)

1.  **UI/Logic Separation**: Never write `supabase.table(...).select(...)` inside a `view.py`. Always go through a Service.
2.  **State Management**:
    *   Use `page.app_session` for global app state (User ID, etc.).
    *   Use `page.client_storage` only for persistent settings (Theme, Auto-login token).
3.  **Routing**:
    *   All navigation logic must handle "Cleaning Overlays" (Dialogs, BottomSheets) before changing routes to prevent "stuck" UI elements.
    *   Use `navigate_to(route)` wrapper, never `page.go()` directly if possible.
4.  **Async/Sync**:
    *   Flet 0.21+ / 0.22+ generally prefers Async.
    *   Most Services are Sync-compatible but called within Async wrappers in Views. *Be consistent.*

## 🛠️ Key Components
*   **Auth**: `AuthService` (Singleton) - Handles Login/Signup/Profile.
*   **Chat**: `ChatService` - Complex logic for Topics, Categories, Messages.
*   **Navigation**: Currently in `main.py` (To be refactored into `Router`).

## 🛑 Common Pitfalls (Do Not Ignore)
*   **Flet 0.80+ Compatibility**: `FilePicker` and `AudioRecorder` have breaking changes. Check compatibility before using.
*   **Overlay Cleanup**: Always dismiss open dialogs before navigating away.
*   **Supabase RLS**: If data returns empty, check Supabase Row Level Security policies first.

---
*Created by Antigravity on 2026-02-01 for Project Stabilization*
