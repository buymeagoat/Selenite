# Component Interface Specifications

Complete specifications for all React components in Selenite. These define props, behavior, and visual states before implementation.

---
## Implementation Status (Nov 17 2025)
Implemented (Increments 10-18): Navbar, Sidebar, MobileNav, NewJobModal, JobDetailModal, ConfirmDialog, JobCard, JobList, JobFilters, ProgressBar, StatusBadge, FileDropzone, UploadOptions, TagInput, TagList, TagBadge, Button, Input, SearchBar, AudioPlayer (baseline), Login, Dashboard, Settings, responsive polish, progress polling integration.

E2E Focus Remaining: JobDetailModal export/action menus, TagInput create+assign flow validations, Settings password change interactions, cancel & restart job controls via JobCard/JobDetailModal, transcription progress visual consistency, transcript view/export navigation.

---

## Layout Components

### Navbar Component
**File**: `src/components/layout/Navbar.jsx`

**Purpose**: Top navigation bar with branding and user menu

**Props**:
```typescript
interface NavbarProps {
  user: {
    username: string;
    email: string;
  };
  onLogout: () => void;
}
```

**Visual Elements**:
- Left: "Selenite" logo/title with pine green color
- Right: User avatar (initials) + dropdown menu
- Dropdown items: Settings, Logout
- Background: White with subtle bottom border
- Sticky to top on scroll

**Responsive**:
- Desktop: Full navbar with text
- Mobile: Hamburger menu icon

---

### Sidebar Component
**File**: `src/components/layout/Sidebar.jsx`

**Purpose**: Left sidebar navigation (desktop only)

**Props**:
```typescript
interface SidebarProps {
  activeRoute: string;
  onNavigate: (route: string) => void;
}
```

**Navigation Items**:
- Dashboard (home icon)
- Settings (gear icon)
- Storage: XX GB used (info icon)

**Visual**:
- Width: 240px
- Background: Light sage (#F8F9F5)
- Active item: Forest green background
- Fixed position on left

**Responsive**:
- Hidden on mobile (<768px)
- Visible on tablet and desktop (>=768px)

---

### MobileNav Component
**File**: `src/components/layout/MobileNav.jsx`

**Purpose**: Bottom navigation bar (mobile only)

**Props**:
```typescript
interface MobileNavProps {
  activeRoute: string;
  onNavigate: (route: string) => void;
}
```

**Navigation Items**:
- Dashboard icon
- New job (+ icon, larger)
- Settings icon

**Visual**:
- Fixed bottom position
- White background with top shadow
- Icons centered, 56px tap targets

**Responsive**:
- Visible only on mobile (<768px)

---

## Modal Components

### NewJobModal Component
**File**: `src/components/modals/NewJobModal.tsx`

**Purpose**: Modal for creating new transcription job

**Props**:
```typescript
interface NewJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (jobData: {
    file: File;
    provider?: string;
    model: string;
    language: string;
    enableTimestamps: boolean;
    enableSpeakerDetection: boolean;
    diarizer?: string;
    speakerCount?: number;
  }) => Promise<void>;
  defaultAsrProvider?: string;
  defaultModel?: string;
  defaultLanguage?: string;
  defaultDiarizerProvider?: string;
  defaultDiarizer?: string;
}
```

**Form Fields**:
1. File upload dropzone (react-dropzone)
   - Drag and drop area
   - "Click to browse" button
   - Accepted formats: audio/*, video/*
   - Max size: 2GB
   - Shows selected filename when file chosen

2. ASR model dropdown
   - Options: registry-provided model sets (e.g., whisper)
   - Disabled models shown as "<name> (disabled)"

3. ASR weight dropdown
   - Options: registry-provided weights for selected model
   - Disabled weights shown as "<weight> (disabled)"

4. Language dropdown
   - Default: "Auto-detect"
   - Options: English, Spanish, French, German, etc.

5. Options checkboxes
   - [x] Include timestamps (default checked)
   - [x] Detect speakers (default checked)

6. Diarizer dropdowns (when enabled)
   - Diarizer model set dropdown
   - Diarizer weight dropdown filtered by set

7. Action buttons
   - Cancel (secondary)
   - Start Transcription (primary, disabled if no file)

**States**:
- Default: Empty dropzone
- File selected: Shows filename, enable submit
- Submitting: Loading spinner, buttons disabled
- Error: Red error message above buttons

**Visual**:
- Max width: 600px
- Centered on screen
- Semi-transparent backdrop (rgba(0,0,0,0.5))
- White card with rounded corners (8px)
- Close X button in top-right

---

### JobDetailModal Component
**File**: `src/components/modals/JobDetailModal.jsx`

**Purpose**: View job details and perform actions

**Props**:
```typescript
interface JobDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: {
    id: string;
    original_filename: string;
    file_size: number;
    duration: number;
    status: string;
    model_used: string;
    language_detected: string;
    speaker_count: number;
    tags: Array<{id: number; name: string; color: string}>;
    created_at: string;
    completed_at: string;
  };
  onPlay: (jobId: string) => void;
  onDownload: (jobId: string, format: string) => void;
  onRestart: (jobId: string) => void;
  onDelete: (jobId: string) => void;
  onUpdateTags: (jobId: string, tagIds: number[]) => void;
}
```

**Sections**:
1. Header
   - Filename (large, bold)
   - Status badge
   - Close X button

2. Metadata Grid (2 columns)
   - Duration: "30:34"
   - Date: "Nov 15, 2025 at 10:30 AM"
   - Model: "medium"
   - Language: "English"
   - Speakers: "2 detected"
   - File size: "15 MB"

3. Tags Section
   - Current tags as colored pills
   - Edit button opens tag selector

4. Audio Player (if audio job)
   - Standard HTML5 audio controls
   - Waveform visualization (optional)

5. Action Buttons (grid layout)
   - Play Media
   - View Transcript (opens new tab)
   - Download Transcript (dropdown: txt, md, srt, vtt, json, docx)
   - Restart Transcription
   - Delete Job (red, requires confirmation)

**Visual**:
- Max width: 800px
- Centered on screen
- Scrollable if content overflows
- Action buttons with icons from lucide-react

**States**:
- Loading: Skeleton UI while fetching job details
- Loaded: Full content displayed
- Deleting: Confirmation dialog overlay
- Error: Error message in place of content

---

### ConfirmDialog Component
**File**: `src/components/modals/ConfirmDialog.jsx`

**Purpose**: Reusable confirmation dialog for destructive actions

**Props**:
```typescript
interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;  // default: "Confirm"
  cancelText?: string;   // default: "Cancel"
  variant?: 'danger' | 'warning' | 'info';  // default: 'warning'
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
}
```

**Visual**:
- Max width: 400px
- Centered on screen
- Icon based on variant (AlertCircle, AlertTriangle, Info)
- Title in bold
- Message in regular text
- Two buttons: Cancel (secondary) and Confirm (primary or danger)

**Example Usage**:
```jsx
<ConfirmDialog
  isOpen={showDeleteConfirm}
  title="Delete Job?"
  message="This will permanently delete the job and all associated files. This action cannot be undone."
  confirmText="Delete"
  variant="danger"
  onConfirm={handleDeleteJob}
  onCancel={() => setShowDeleteConfirm(false)}
/>
```

---

## Job Components

### JobCard Component
**File**: `src/components/jobs/JobCard.jsx`

**Purpose**: Display summary of a single job in list view

**Props**:
```typescript
interface JobCardProps {
  job: {
    id: string;
    original_filename: string;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    created_at: string;
    duration?: number;
    progress_percent?: number;
    progress_stage?: string;
    estimated_time_left?: number;
    tags: Array<{id: number; name: string; color: string}>;
  };
  onClick: (jobId: string) => void;
  onQuickAction?: (jobId: string, action: string) => void;
}
```

**Visual Layout**:
```
+-----------------------------------------+
| interview.mp3                 [Completed] |
| Nov 15, 2025 at 10:30 AM   Duration: 30:34 |
| #interviews #important                    |
| ----------------------------------------- |
| [Play] [Download] [View]                  |
+-----------------------------------------+
```

**States**:
- **Queued**: Gray status badge, no progress bar
- **Processing**: Blue/sage animated badge, progress bar showing percent, stage text, time estimate
- **Completed**: Green badge, shows duration, action buttons visible
- **Failed**: Red badge with error icon, shows error message, Retry button

**Visual Styling**:
- Background: White
- Border: 1px solid light gray
- Border-radius: 8px
- Shadow: 0 2px 4px rgba(0,0,0,0.1)
- Hover: Shadow elevates to 0 4px 8px
- Click: Navigates to detail modal
- Quick action buttons: Icon only, show on hover (desktop) or always (mobile)

**Responsive**:
- Mobile: Stacked layout, full-width buttons
- Tablet: 2-column grid
- Desktop: 3-column grid

---

### JobList Component
**File**: `src/components/jobs/JobList.jsx`

**Purpose**: Container for job cards with loading/empty states

**Props**:
```typescript
interface JobListProps {
  jobs: Array<Job>;
  isLoading: boolean;
  onJobClick: (jobId: string) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
}
```

**States**:
- Loading: Shows 6 skeleton cards
- Empty: "No jobs found" message with icon, "Create New Job" button
- Loaded: Grid of JobCard components
- Load More: Button at bottom if hasMore is true

**Visual**:
- Grid layout: 1 column (mobile), 2 columns (tablet), 3 columns (desktop)
- Gap: 16px between cards

---

### JobFilters Component
**File**: `src/components/jobs/JobFilters.jsx`

**Purpose**: Filter controls for job list

**Props**:
```typescript
interface JobFiltersProps {
  currentFilters: {
    status?: string;
    dateRange?: string;
    tags?: number[];
  };
  availableTags: Array<{id: number; name: string; color: string}>;
  onFilterChange: (filters: JobFilters) => void;
  onReset: () => void;
}
```

**Filter Controls**:
1. Status dropdown
   - Options: All, In Progress, Completed, Failed
   
2. Date range dropdown
   - Options: All Time, Today, This Week, This Month, Custom Range
   - Custom Range opens date picker modal

3. Tag multi-select
   - Dropdown with checkboxes
   - Shows selected tags as pills
   - "Clear all" button

4. Reset button
   - Clears all filters
   - Only visible when filters applied

**Visual**:
- Horizontal layout on desktop
- Stacked on mobile
- Each filter is a dropdown button
- Active filters show count badge

---

### ProgressBar Component
**File**: `src/components/jobs/ProgressBar.jsx`

**Purpose**: Animated progress bar for processing jobs

**Props**:
```typescript
interface ProgressBarProps {
  percent: number;  // 0-100
  stage?: string;   // "loading_model", "transcribing", etc.
  estimatedTimeLeft?: number;  // seconds
  variant?: 'default' | 'success' | 'error';
}
```

**Visual**:
- Height: 8px (thin bar) or 24px (with labels)
- Track: Light sage (#95D5B2)
- Fill: Forest green (#2D6A4F)
- Animated shimmer effect while processing
- Rounded ends (border-radius: 4px)

**With Labels**:
```
Transcribing... 45%  (~7 minutes remaining)
[===================>        ]
```

**States**:
- Active: Animated shimmer
- Paused: No animation
- Complete: Success variant (bright sage)
- Error: Error variant (terracotta)

---

### StatusBadge Component
**File**: `src/components/jobs/StatusBadge.jsx`

**Purpose**: Colored pill showing job status

**Props**:
```typescript
interface StatusBadgeProps {
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  size?: 'sm' | 'md' | 'lg';
}
```

**Visual Styles**:
- **queued**: Gray background, "Queued" text
- **processing**: Sage background, pulsing animation, "Processing" text
- **completed**: Green background, check icon, "Completed" text
- **failed**: Terracotta background, X icon, "Failed" text
- **cancelled**: Gray background, slash icon, "Cancelled" text

**Size**:
- sm: 16px height, 10px font
- md: 20px height, 12px font (default)
- lg: 24px height, 14px font

**Shape**: Pill (fully rounded ends)

---

## Upload Components

### FileDropzone Component
**File**: `src/components/upload/FileDropzone.jsx`

**Purpose**: Drag-and-drop file upload area

**Props**:
```typescript
interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  accept: string;  // e.g., "audio/*,video/*"
  maxSize: number;  // bytes
  selectedFile?: File | null;
}
```

**Visual States**:
1. **Default**: Dashed border, upload icon, "Drag & drop file here, or click to browse"
2. **Drag over**: Solid border, highlight background, "Drop file here"
3. **File selected**: Shows filename, file size, type, small thumbnail/icon, "Change file" link
4. **Error**: Red border, error icon, error message

**Styling**:
- Border: 2px dashed #D4D4D4
- Border-radius: 8px
- Padding: 32px
- Min-height: 200px
- Centered content
- Upload icon from lucide-react

---

### UploadOptions Component
**File**: `src/components/upload/UploadOptions.jsx`

**Purpose**: Transcription options form

**Props**:
```typescript
interface UploadOptionsProps {
  options: {
    model: string;
    language: string;
    enableTimestamps: boolean;
    enableSpeakerDetection: boolean;
  };
  availableModels: string[];
  onChange: (options: UploadOptions) => void;
}
```

**Form Fields**:
1. Model dropdown with descriptions
   - tiny: "Fastest, lowest accuracy (75MB)"
   - base: "Fast, moderate accuracy (142MB)"
   - small: "Balanced speed and accuracy (466MB)"
   - medium: "High accuracy, slower (1.5GB)" <- default
   - large: "Highest accuracy, slowest (2.9GB)"

2. Language dropdown
   - Auto-detect (default)
   - List of common languages

3. Checkboxes
   - Include timestamps
   - Detect speakers (note: "Basic detection, 1 speaker by default")

**Visual**:
- Vertical stack
- Labels above inputs
- Helper text below checkboxes

---

## Tag Components

### TagInput Component
**File**: `src/components/tags/TagInput.jsx`

**Purpose**: Input with autocomplete for selecting/creating tags

**Props**:
```typescript
interface TagInputProps {
  availableTags: Array<{id: number; name: string; color: string}>;
  selectedTags: number[];
  onChange: (tagIds: number[]) => void;
  onCreate: (tagName: string) => Promise<{id: number; name: string; color: string}>;
  placeholder?: string;
}
```

**Behavior**:
1. User types in input
2. Dropdown shows matching tags (autocomplete)
3. If no match and user presses Enter, create new tag
4. Selected tags shown as pills below input with X to remove

**Visual**:
- Input: Standard text input with tag icon
- Dropdown: List of tags with color dots
- Selected tags: Pills with tag color as background, white text
- "Create new tag: {name}" option at bottom of dropdown if no match

---

### TagList Component
**File**: `src/components/tags/TagList.jsx`

**Purpose**: Display list of tags (settings page)

**Props**:
```typescript
interface TagListProps {
  tags: Array<{id: number; name: string; color: string; job_count: number}>;
  onEdit: (tagId: number) => void;
  onDelete: (tagId: number) => void;
}
```

**Visual**:
- Table layout on desktop
- Cards on mobile
- Columns: Color dot, Name, Job count, Actions (edit, delete icons)
- Empty state: "No tags created yet"

---

### TagBadge Component
**File**: `src/components/tags/TagBadge.jsx`

**Purpose**: Small colored tag pill

**Props**:
```typescript
interface TagBadgeProps {
  tag: {
    id: number;
    name: string;
    color: string;
  };
  size?: 'sm' | 'md';
  onRemove?: (tagId: number) => void;  // if provided, shows X button
  onClick?: (tagId: number) => void;  // if provided, clickable
}
```

**Visual**:
- Background: tag.color
- Text: White (or black if color is light)
- Border-radius: 4px
- Padding: 4px 8px (sm) or 6px 12px (md)
- Optional X button on right (hover to show on desktop)

---

## Common Components

### Button Component
**File**: `src/components/common/Button.jsx`

**Purpose**: Reusable button with variants

**Props**:
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  isLoading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  children: ReactNode;
}
```

**Variants**:
- **primary**: Forest green background, white text
- **secondary**: White background, forest green border and text
- **danger**: Terracotta background, white text
- **ghost**: No background, forest green text, hover shows light tint

**Sizes**:
- sm: 32px height, 12px text
- md: 40px height, 14px text (default)
- lg: 48px height, 16px text

**States**:
- Default: Defined by variant
- Hover: Darken background or show background tint
- Active: Scale down slightly (transform: scale(0.98))
- Disabled: Opacity 0.5, cursor not-allowed
- Loading: Show spinner, disable interaction

---

### Input Component
**File**: `src/components/common/Input.jsx`

**Purpose**: Reusable text input with label and error

**Props**:
```typescript
interface InputProps {
  label?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  type?: 'text' | 'password' | 'email' | 'number';
  error?: string;
  helperText?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  disabled?: boolean;
  required?: boolean;
}
```

**Visual**:
- Label: 14px, bold, above input
- Input: 40px height, border, rounded corners
- Error: Red text below input
- Helper text: Gray text below input
- Focus: Forest green border
- Error state: Red border

---

### SearchBar Component
**File**: `src/components/common/SearchBar.jsx`

**Purpose**: Search input with icon and clear button

**Props**:
```typescript
interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onClear?: () => void;
  isLoading?: boolean;
}
```

**Visual**:
- Search icon on left
- Clear X button on right (only when value not empty)
- Loading spinner replaces clear button when isLoading
- Full width on mobile, max 400px on desktop

**Behavior**:
- Debounced input (300ms delay before onChange called)
- Clear button clears value and calls onClear

---

### AudioPlayer Component
**File**: `src/components/common/AudioPlayer.jsx`

**Purpose**: Custom audio player with timeline

**Props**:
```typescript
interface AudioPlayerProps {
  src: string;  // URL to audio file
  filename: string;
  duration: number;  // seconds
  onTimeUpdate?: (currentTime: number) => void;
}
```

**Visual Elements**:
- Play/Pause button
- Current time / Total time
- Seek bar (clickable timeline)
- Volume control
- Download button
- Speed selector (1x, 1.25x, 1.5x, 2x)

**Styling**:
- Use HTML5 audio element with custom controls
- Forest green accents
- Responsive: Simplified controls on mobile

---

## Page Components

### Login Page
**File**: `src/pages/Login.jsx`

**Purpose**: Authentication page

**Elements**:
- Centered card on pine forest gradient background
- Selenite logo/title
- Username input
- Password input
- "Login" button
- Error message area

**Visual**:
- Max width: 400px
- White card with shadow
- Pine forest background gradient

---

### Dashboard Page
**File**: `src/pages/Dashboard.jsx`

**Purpose**: Main application page

**Layout**:
- Header: "Transcriptions" title + "New Job" button
- Search bar
- Filters bar
- Job list (grid of job cards)
- Pagination or infinite scroll

**States**:
- Loading: Skeleton UI
- Empty: Empty state with call to action
- Loaded: Job cards displayed

---

### Settings Page
**File**: `src/pages/Settings.tsx`

**Purpose**: Application settings

**Sections**:
1. **Account**
   - Change password form

2. **Default Transcription Options**
   - ASR model dropdown
   - ASR weight dropdown (filtered by model)
   - Language dropdown
   - Checkboxes for timestamps and diarization

3. **Performance**
   - Max concurrent jobs slider (1-5)

4. **Storage**
   - Used space: XX GB / YY GB
   - Location: /storage (read-only)

5. **Tags** (expandable section)
   - TagList component

6. **System**
   - Restart Server button (admin only)
   - Shutdown Server button (admin only)

**Visual**:
- Sections separated by borders
- Save button at bottom of each section

---

### Admin Page
**File**: `src/pages/Admin.tsx`

**Purpose**: Admin-only controls for model registry, defaults, system settings, and hygiene.

**Sections**:
1. **Model Registry**
   - Tabs: ASR / Diarizer
   - Model set selector (recalls last selected set)
   - Model set form (name, description, path; enable/disable with reason)
   - Model weights list and form (name, description, path, checksum; enable/disable with reason)
   - Path inputs support both manual entry and browse UI (file browser rooted at app root)
   - "Rescan availability" button (refreshes registry/capabilities)

2. **Administration**
   - ASR defaults (model set + weight; defaults shown separately from last-selected state)
   - Diarizer defaults (model set + weight)
   - Throughput controls (max concurrent jobs)
   - Storage summary (read-only)
   - System actions (restart/shutdown if enabled)

**Visual**:
- Cards with clear section headings
- Disabled states show inline help (e.g., disabled toggles when weights missing)

---

### TranscriptView Page
**File**: `src/pages/TranscriptView.jsx`

**Purpose**: Full-page transcript viewer

**Props**:
```typescript
interface TranscriptViewProps {
  jobId: string;  // from URL params
}
```

**Layout**:
- Header: Job filename, back button, download button
- Transcript text (formatted based on timestamps)
- Sidebar: Metadata, tags (collapsible on mobile)

**Features**:
- Syntax highlighting for speaker labels
- Timestamps as clickable links (if audio playing)
- Search within transcript (Ctrl+F works naturally)

---

## Component Interaction Patterns

### Job Creation Flow
1. User clicks "New Transcription" button
2. `NewJobModal` opens
3. User selects file via `FileDropzone`
4. User configures options via `UploadOptions`
5. User clicks "Start Transcription"
6. Modal calls `onSubmit` prop with job data
7. Parent component calls API
8. Modal closes, Dashboard shows new job in "queued" state

### Job Progress Monitoring
1. Dashboard renders `JobCard` for processing job
2. `JobCard` shows `ProgressBar` with current percent
3. Dashboard uses `usePolling` hook to fetch status every 2 seconds
4. Job state updates, `ProgressBar` animates to new percent
5. When status changes to "completed", polling stops

### Tag Assignment
1. User clicks job card
2. `JobDetailModal` opens
3. User clicks "Edit Tags" in modal
4. `TagInput` component renders
5. User types, autocomplete shows matching tags
6. User selects tag or creates new one
7. Selected tags shown as `TagBadge` pills
8. User clicks "Save"
9. Modal calls `onUpdateTags` prop
10. API updated, job refetched, modal updates

---

**These component specifications are the blueprint for frontend implementation. All components must match these interfaces and behaviors.**
