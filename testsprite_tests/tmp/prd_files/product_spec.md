# Product Specification: Beep Manager (Project Owners)

## 1. Project Overview
"Beep Manager" is a premium store management application designed for store owners and managers. It provides a centralized platform for communication, task management, and operations monitoring.

## 2. Core Features & User Flows

### 2.1. Authentication
- **Login**: Users authenticate using an email and password.
- **Session**: The app maintains user sessions and routes to the home screen upon successful login.

### 2.2. Home Dashboard
- A central hub with 3D-styled menu items:
    - **Messenger**: Real-time communication channel.
    - **Calendar**: Store schedule and event management with real-time sync.
    - **Handover (Work Log)**: Recording and sharing daily operational notes.
    - **Checklist**: Safety and operational verification tasks for opening/closing.
    - **Attendance**: Clock-in/out tracking with GPS/Wi-Fi verification.
    - **Settings**: Store and profile management.

### 2.3. Attendance Management (High Priority)
- **Clock-In/Out**: Users can record their work hours via a premium UI.
- **Verification**: Supports GPS-based (location) and Wi-Fi-based (network) verification to ensure presence at the store.
- **Real-time Feedback**: Displays current time and status (In/Out) with smooth animations.

### 2.4. Messenger & Calendar
- **Messenger**: Real-time chat synchronization across devices.
- **Calendar**: Displays store events by month, supports adding/editing events with real-time updates.

## 3. Design System (Premium UI/UX)
- **Aesthetics**: Glassmorphism effects, heavy use of gradients (Linear/Radial), and 3D icons.
- **Responsiveness**: Optimized for mobile-first interactive layouts.
- **Modes**: Full support for both Light and Dark modes.

## 4. Technical Constraints
- **Framework**: Built with Flet (Python-based Flutter UI).
- **Navigation**: Custom router handles path changes and state cleanup.
- **Real-time**: Real-time features are handled via internal polling and sync service handlers.
