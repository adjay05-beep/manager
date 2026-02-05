# System Diagnosis & Architecture Map

## 1. System Overview
- **Framework**: Flet (v0.80+)
- **Architecture**: Single Page Application (SPA) with a custom `Router` service.
- **State Management**: Mixed (Global `page.session`, Local closure variables, Mutable `state` dictionaries).

## 2. Identified Root Causes

### A. Calendar: "Menu Button Not Working"
- **Diagnosis**: The `page.drawer` reference is fragile. Features like `Router.cleanup_overlays` or page updates in other views might be detaching the drawer.
- **Why previous fixes failed**: We were re-assigning it *inside* the click handler. If the click handler itself isn't wired up to the *currrent* page context (due to view recreation), it never fires.
- **Solution**: 
    1. Define the Drawer explicitly in the View creation.
    2. Assign it to `page.drawer` immediately.
    3. Ensure the `left_button` directly references this `drawer` instance via closure, *without* relying on `page.drawer` lookup if possible, OR strictly re-bind it.

### B. Chat: "Infinite Loading"
- **Diagnosis**: The `is_loading_messages` flag is a "mutex" (lock). If an error occurs (e.g., Network timeout, DB schema mismatch, or Scroll error) *before* the lock is released, the app waits forever.
- **Why previous fixes failed**: The `finally` block was added but possibly the error logic itself hangs or recurses.
- **Solution**: Add a "Circuit Breaker". If loading takes > 5 seconds, simple force-reset the flag.

### C. Work Log: "Not Scrolling to Bottom"
- **Diagnosis**: `ListView` rendering is "lazy". When we ask to scroll to "bottom" or a "key", the item might not exist in the DOM yet because Flet hasn't laid it out.
- **Why previous fixes failed**: `offset=-1` relies on the engine knowing the total height. `key` relying on the item being rendered.
- **Solution**: We need to "Anchor" the scroll. We will adding a dummy transparent `Container` at the end of the list with a fixed height and a known Key, and scroll to *that*.

## 3. Action Plan
1. **Router**: Update `cleanup_overlays` to explicitly clear `page.drawer` to prevent ghost drawers.
2. **Calendar**: Rewrite `open_drawer_safe` to be absolutely minimal.
3. **Chat**: Add a timeout breaker to the Loading Indicator.
4. **Work Log**: Add a physical "Anchor" element to the list and scroll to it.
