# Calendar V2: Advanced Event Creation

## Goal Description
Upgrade the simple "Add Event" functionality to a full-featured event creation form. This includes "All Day" toggle, detailed time selection (when not all day), location, external link, color selection, and participant selection.

## User Review Required
> [!IMPORTANT]
> **Database Migration Required**: The existing `calendar_events` table needs new columns (`is_all_day`, `location`, `link`, `participant_ids`). I will provide a SQL script. If my attempt to auto-run it fails, **you will need to run it in your Supabase SQL Editor**.

## Proposed Changes

### Database Schema
#### [MODIFY] `calendar_events` table
- Add column `is_all_day` (boolean, default false)
- Add column `location` (text)
- Add column `link` (text)
- Add column `participant_ids` (jsonb array of user_ids)

### UI Components (`app_views.py`)
- **New Event Dialog**: Replace the simple DatePicker with a custom `AlertDialog` or `BottomSheet`.
    - **Title Field**: Standard text field.
    - **All Day Switch**: Toggle.
        - **Logic**: If ON -> Hide Time Picker rows. If OFF -> Show Start/End Date+Time Pickers.
    - **Time Selection**:
        - Separate Start Date / Start Time buttons (if not all day).
        - Logic to ensure End > Start.
    - **Color Selection**:
        - Row of circular color chips.
        - "Midnight Black" style theme options.
    - **Participants**:
        - Dropdown or MultiSelect using `profiles` table data.
        - Chip display of selected members.
    - **Bottom Sheet Features**:
        - Location Input
        - Link Input
        - "Memo" (Description) Input
    - **Actions**:
        - Save Button -> Inserts into DB.
        - Cancel Button.

### Backend/Logic
- Fetch `profiles` on dialog open to populate participants.
- Default to "All Day" OFF (as per screenshot request "toggle default off -> set time").

## Verification Plan
### Automated Tests
- None (UI heavy).

### Manual Verification
1. Open Calendar -> Click "Add".
2. Verify Dialog UI matches the mobile-style screenshot.
3. Test "All Day" toggle visibility change.
4. Save an event with all fields.
5. Verify event appears on calendar with correct color.
6. Verify "Participants" are saved (even if not fully utilized in view yet).
