# Selenite User Guide

Welcome to Selenite! This guide will help you get started with transcribing your audio and video files using local AI-powered speech recognition.

## Table of Contents
- [Getting Started](#getting-started)
- [Logging In](#logging-in)
- [Dashboard Overview](#dashboard-overview)
- [Creating Transcription Jobs](#creating-transcription-jobs)
- [Managing Jobs](#managing-jobs)
- [Searching and Filtering](#searching-and-filtering)
- [Tag Management](#tag-management)
- [Settings](#settings)
- [Tips & Best Practices](#tips--best-practices)
- [Troubleshooting](#troubleshooting)

## Getting Started

Selenite is a personal transcription application that runs entirely on your computer. It uses OpenAI's Whisper models to convert speech to text without sending your files to external services.

**Key Features**:
- **Local Processing**: All transcription happens on your device
- **Multiple Formats**: Supports MP3, WAV, MP4, AVI, MOV, and more
- **Real-time Progress**: Watch transcription progress in real-time
- **Tag Organization**: Organize jobs with custom tags
- **Search & Filter**: Quickly find jobs by name, status, date, or tags
- **Multiple Models**: Choose speed vs. accuracy with different Whisper models

## Logging In

1. Open Selenite in your web browser (default: `http://localhost:5173`)
2. Enter your credentials:
   - **Username**: `admin` (default)
   - **Password**: Your configured password (change default on first login!)
3. Click **Sign In**

**First-time setup**: Navigate to Settings (⚙️) and change the default admin password immediately.

## Dashboard Overview

The dashboard is your main workspace. Here's what you'll see:

### Header
- **User Avatar**: Click to log out
- **Settings Icon** (⚙️): Access application settings
- **Mobile Menu** (☰): On small screens, access navigation

### Search & Filters Section
- **Search Bar**: Search jobs by filename
- **Filters Button**: Filter by status, date, and tags

### Job Cards
Each job card displays:
- **Filename**: Original file name
- **Status Badge**: Current state (In Progress, Completed, Failed)
- **Progress Bar**: Visual progress indicator (for active jobs)
- **Tags**: Colored tag badges for organization
- **Created Date**: When the job was created
- **Estimated Time**: Remaining time for processing jobs

Click any card to view detailed information.

### New Job Button
The floating **+** button (bottom-right) opens the upload modal.

## Creating Transcription Jobs

### 1. Upload Your File

Click the **+** button to open the New Job modal:

1. **Drag & Drop**: Drag files directly into the upload area
   - Or click "Browse files" to select from your computer

2. **Choose Whisper Model**:
   - **tiny**: Fastest, lowest accuracy (~1GB RAM)
   - **small**: Good balance (~2GB RAM)
   - **medium**: Best quality for most use cases (~5GB RAM) [Default]
   - **large-v3**: Highest accuracy, very slow (~10GB RAM)

3. **Select Language**:
   - **Auto-detect**: Automatically identifies language [Default]
   - Or choose from 90+ supported languages

4. **Transcription Options** (checkboxes):
   - ☑ **Detect speakers**: Enable speaker diarization (who said what)
   - ☑ **Add timestamps**: Include timestamps in transcript
   - ☑ **Translate to English**: Translate non-English audio to English

5. **Add Tags** (optional):
   - Type to search existing tags or create new ones
   - Press **Enter** to add tags
   - Click **X** on tag pills to remove

6. Click **Start Transcription**

### 2. Monitor Progress

After submission:
- Job card appears on dashboard with "In Progress" status
- Progress bar updates automatically every 2 seconds
- Estimated time remaining counts down

### 3. View Results

When complete:
- Status changes to "Completed"
- Click the card to view full transcript
- Download transcript as SRT, VTT, or TXT

## Managing Jobs

### Viewing Job Details

Click any job card to open the detail modal:

**Information Tab**:
- Full transcript text (scrollable)
- Metadata: Duration, file size, language detected, word count
- Created and completed timestamps

**Actions Available**:
- **Download Transcript**: Choose format (SRT, VTT, TXT)
- **Download Audio**: Get the original audio file
- **Restart Job**: Re-run transcription with same settings
- **Delete Job**: Permanently remove job and files

### Job Statuses

- **⏳ Queued**: Waiting for worker to become available
- **🔄 In Progress**: Currently transcribing (progress bar visible)
- **✅ Completed**: Transcription finished successfully
- **❌ Failed**: Error occurred (hover for details)

## Searching and Filtering

### Search Bar

Type in the search box to filter jobs by filename:
- Search is case-insensitive
- Results update after 300ms (debounced)
- Click **X** to clear search

### Filters

Click the **Filters** button to open the filter panel:

**Status Filter**:
- All
- In Progress (queued + processing)
- Completed
- Failed

**Date Filter**:
- All Time
- Today
- This Week
- This Month
- Custom Range (coming soon)

**Tag Filter**:
- Check tags to include jobs with ANY of the selected tags
- Selected tags appear as pills above dropdown
- Click **X** on pill to remove tag filter

**Reset Button**: Click to clear all active filters

### Filter Combinations

Filters work together (AND logic):
- Search + Status: Show only completed jobs matching "interview"
- Status + Tags: Show in-progress jobs tagged "podcast"
- All filters: Search for "meeting" in completed jobs from this week tagged "work"

## Tag Management

Tags help organize your transcription jobs into categories.

### Creating Tags

**From New Job Modal**:
1. In the Tags field, type a new tag name
2. Press **Enter** to create and add it
3. Choose a color (optional - auto-assigned if not specified)

**From Settings Page**:
1. Navigate to Settings (⚙️) → Tags section
2. Click **Expand** to view tag manager
3. Use the tag input to create new tags

### Viewing Tags

In the Tags section of Settings:
- **Tag List**: Table view (desktop) or cards (mobile)
- **Columns**: Color, Name, Job Count, Actions
- **Empty State**: Shows when no tags exist

### Editing Tags

1. Find the tag in Settings → Tags
2. Click the **Edit** icon (✏️)
3. Modify name or color
4. Save changes

### Deleting Tags

1. Find the tag in Settings → Tags
2. Click the **Delete** icon (🗑️)
3. Confirm deletion
4. Tag is removed from all associated jobs

**Note**: Deleting a tag does NOT delete the jobs using it.

## Settings

Access Settings via the gear icon (⚙️) in the navbar.

### Account Settings
- **Change Password**: Update your login password
- **Username**: Display only (cannot be changed)

### Transcription Options
Configure default settings for new jobs:
- **Whisper Model**: Default model (tiny/small/medium/large-v3)
- **Language**: Default language or auto-detect
- **Detect Speakers**: Enable speaker diarization by default
- **Add Timestamps**: Include timestamps by default
- **Translate to English**: Auto-translate by default

### Performance Settings
- **Max Concurrent Jobs**: Number of jobs to process simultaneously
  - Slider: 1-5 jobs
  - Higher = faster throughput, more resource usage
  - Recommendation: Start with 3, decrease if system slows down

### Storage Management
- **Storage Usage**: Visual progress bar showing disk usage
- **Used / Total**: Exact storage numbers
- **Clear Cache** (coming soon): Remove temporary files

### Tag Management
- **Expand/Collapse**: Toggle tag list visibility
- **Create, edit, delete tags**: See [Tag Management](#tag-management)

### System Settings
- **Restart Application**: Restart backend services
- **Shutdown**: Stop the application

**Important**: Restart and Shutdown require confirmation before executing.

## Tips & Best Practices

### Choosing the Right Model

| Model | Speed | Accuracy | RAM | Best For |
|-------|-------|----------|-----|----------|
| tiny | ⚡⚡⚡⚡⚡ | ⭐⭐ | ~1GB | Quick drafts, low-resource systems |
| small | ⚡⚡⚡⚡ | ⭐⭐⭐ | ~2GB | Good balance for most users |
| medium | ⚡⚡⚡ | ⭐⭐⭐⭐ | ~5GB | **Recommended** - best quality/speed |
| large-v3 | ⚡ | ⭐⭐⭐⭐⭐ | ~10GB | Critical accuracy, professional work |

### Audio Quality Tips

For best transcription results:
- **Quiet Environment**: Minimize background noise
- **Clear Speech**: Speak directly into microphone
- **Good Equipment**: Use quality recording devices
- **Supported Formats**: MP3, WAV, FLAC for audio; MP4, AVI, MOV for video
- **File Size**: Large files take longer; consider splitting 2+ hour recordings

### Performance Optimization

**If transcription is slow**:
1. Use a smaller model (tiny or small)
2. Reduce Max Concurrent Jobs to 1-2
3. Close other memory-intensive applications
4. Ensure sufficient RAM available

**If system becomes unresponsive**:
1. Lower Max Concurrent Jobs in Settings
2. Pause other CPU-intensive tasks during transcription
3. Consider upgrading RAM for larger models

### Organization Best Practices

**Tagging Strategy**:
- **By Type**: meetings, interviews, podcasts, lectures
- **By Project**: project-alpha, client-xyz, research-2024
- **By Status**: needs-review, ready-to-publish, archived
- **By Language**: english, spanish, french

**Naming Conventions**:
- Use descriptive filenames before upload: `2024-01-15_team-meeting.mp3`
- Include dates for chronological sorting
- Avoid special characters that may cause issues

### Backup Your Transcripts

- Download important transcripts immediately after completion
- Store backups in multiple locations (cloud storage, external drive)
- Transcripts are stored in: `storage/transcripts/` directory

## Troubleshooting

### Common Issues

#### "Login Failed" Error
**Solution**:
- Verify username and password are correct
- Check that backend server is running
- Confirm network connectivity

#### Job Stuck at "In Progress"
**Solution**:
- Wait - large files take time (check estimated time)
- Check backend logs for errors
- Restart the job from detail modal
- If persistent, check system resources (CPU/RAM)

#### "Upload Failed" Error
**Solutions**:
- Verify file format is supported (MP3, WAV, MP4, etc.)
- Check file isn't corrupted (play it first)
- Ensure sufficient disk space
- Reduce file size if very large (>2GB)

#### Transcription Quality is Poor
**Solutions**:
- Use a larger model (medium or large-v3)
- Ensure audio quality is good (test playback)
- Try different language settings if auto-detect is wrong
- Check for background noise in original recording

#### Application is Slow
**Solutions**:
- Reduce Max Concurrent Jobs in Settings
- Close unnecessary applications
- Upgrade RAM for larger models
- Use smaller Whisper model

#### Can't Find a Job
**Solutions**:
- Check active filters (Status, Date, Tags)
- Click "Reset" to clear all filters
- Use search bar to search by filename
- Verify job wasn't accidentally deleted

### Error Messages

| Message | Meaning | Solution |
|---------|---------|----------|
| "Authentication required" | Not logged in | Log in again |
| "File too large" | Exceeds size limit | Split file or compress |
| "Unsupported format" | File type not recognized | Convert to MP3/WAV/MP4 |
| "Insufficient storage" | Disk full | Delete old jobs or free up space |
| "Model not found" | Whisper model missing | Download model in Settings |

### Getting Help

If you encounter issues not covered here:

1. **Check Logs**:
   - Backend: `backend/logs/selenite.log`
   - Browser console: F12 → Console tab

2. **GitHub Issues**:
   - Report bugs: https://github.com/yourusername/Selenite/issues
   - Search existing issues first

3. **Community Support**:
   - Discussions: https://github.com/yourusername/Selenite/discussions

4. **Documentation**:
   - `docs/API_CONTRACTS.md`: API reference
   - `docs/DEPLOYMENT.md`: Deployment guide
   - `docs/COMPONENT_SPECS.md`: Technical specs

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Open search |
| `N` | New job (when on dashboard) |
| `Esc` | Close modal |
| `Enter` | Submit form/search |
| `Ctrl/Cmd + /` | Open settings |

## Privacy & Security

- **Local Processing**: All transcription happens on your computer - files never leave your device
- **No Tracking**: Selenite does not collect usage data or analytics
- **Open Source**: Audit the code yourself on GitHub
- **Secure Storage**: Files stored locally in `storage/` directory
- **Password Protection**: Application requires login credentials

## Updates & Maintenance

### Updating Selenite

```bash
# Pull latest code
git pull origin main

# Update backend dependencies
cd backend
pip install --upgrade -r requirements.txt

# Update frontend dependencies
cd ../frontend
npm install
npm run build
```

### Database Backups

Your data is stored in `backend/selenite.db` (SQLite):

```bash
# Backup database
cp backend/selenite.db backend/selenite.db.backup

# Restore from backup
cp backend/selenite.db.backup backend/selenite.db
```

### Clearing Storage

To free up disk space:

1. Delete old jobs from the UI
2. Or manually remove files from:
   - `storage/media/` - original audio/video files
   - `storage/transcripts/` - generated transcripts

---

**Enjoy using Selenite!** 🌙✨

For technical documentation, see:
- `DEPLOYMENT.md` - Production deployment guide
- `API_CONTRACTS.md` - API reference
- `COMPONENT_SPECS.md` - Component specifications
