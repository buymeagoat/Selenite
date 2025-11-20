```markdown
# Selenite Smoke Test

## Purpose
This document provides step-by-step instructions for manually validating the complete vertical slice of Selenite functionality, from file upload to transcript download.

## Prerequisites

### Backend
- Python 3.10+ installed
- Backend dependencies installed: `pip install -r requirements-minimal.txt`
- Database migrated and seeded:
  ```bash
  cd backend
  python -m alembic upgrade head
  python -m app.seed
  ```
- Backend server running in production mode:
  ```bash
  cd backend
  export DISABLE_FILE_LOGS=1
  export ENVIRONMENT=production
  export ALLOW_LOCALHOST_CORS=1
  uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir app
  ```
- Verify backend health: Navigate to http://localhost:8100/health
- Automated smoke test (optional but recommended):
  ```bash
  python scripts/smoke_test.py --base-url http://127.0.0.1:8100
  ```

### Frontend
- Node.js 18+ installed with npm
- Frontend dependencies installed: `npm install`
- Frontend production preview running: `npm run start:prod -- --host 127.0.0.1 --port 5173`
- `.env` file configured with `VITE_API_URL=http://localhost:8100`

### Test Data
- Prepare a small audio/video file (< 10MB recommended for quick testing)
  - Supported formats: mp3, wav, m4a, flac, ogg, mp4, avi, mov, mkv
  - Example: 30-second audio clip with clear speech

## Test Procedure

### 1. Login
**Expected Behavior:**
- Application loads without errors
- Login form is visible
- Default credentials work (admin/admin if using seed data)

**Steps:**
1. Open browser and navigate to http://localhost:5173 (or your frontend URL)
2. Enter credentials:
   - Username: `admin`
   - Password: `admin`
3. Click "Login" button

**Success Criteria:**
- ✅ Redirect to Dashboard page
- ✅ Navbar displays user menu
- ✅ No console errors

**Troubleshooting:**
- If 404 error: Ensure the frontend production preview server (`npm run start:prod`) is running
- If 401 error: Verify backend is running and credentials are correct
- If CORS error: Check backend CORS settings in `app/config.py`

---

### 2. Upload File
**Expected Behavior:**
- Modal opens with file dropzone
- File validation works (size, format)
- Upload button enables after file selection

**Steps:**
1. Click "+ New Job" button in Dashboard
2. In the modal:
   - Drag and drop test file, OR click to browse and select file
   - Select model: "small" (for faster testing)
   - Select language: "auto" or specific language
   - Ensure "Include timestamps" is checked
   - Ensure "Detect speakers" is checked
3. Click "Start Transcription" button

**Success Criteria:**
- ✅ Success toast appears: "Job created successfully: [filename]"
- ✅ Modal closes automatically
- ✅ New job appears in Dashboard immediately
- ✅ Job status is "queued" or "processing"

**Troubleshooting:**
- If 413 error: File too large (max 2GB)
- If 400 error: Invalid file format
- If 500 error: Check backend logs for errors
- If job doesn't appear: Check browser console and backend logs

---

### 3. Monitor Progress
**Expected Behavior:**
- Job card shows status updates every 2 seconds
- Progress bar updates with percentage
- Estimated time left displays and counts down
- Status transitions: queued → processing → completed

**Steps:**
1. Observe the job card in Dashboard
2. Watch for status changes
3. Note progress percentage and time estimates
4. Wait for job completion (small files should complete in 1-5 minutes)

**Success Criteria:**
- ✅ Job status updates automatically without page refresh
- ✅ Progress bar animates smoothly
- ✅ Progress stage shows: "transcribing" or similar
- ✅ Status changes to "completed" when done
- ✅ Completed job shows duration and tags

**Troubleshooting:**
- If stuck in "queued": Check backend worker started (check logs)
- If stuck in "processing": Check backend logs for transcription errors
- If status "failed": Click job to see error details
- If no updates: Check browser console for polling errors

---

### 4. View Job Details
**Expected Behavior:**
- Modal opens showing complete job information
- All metadata is populated
- Transcript preview is visible

**Steps:**
1. Click on completed job card
2. JobDetailModal opens
3. Review displayed information:
   - Filename
   - Duration
   - File size
   - Model used
   - Language detected
   - Speaker count
   - Timestamps (if enabled)
   - Tags (if any)
   - Transcript preview

**Success Criteria:**
- ✅ Modal displays without errors
- ✅ All fields populated with data
- ✅ Transcript text is visible
- ✅ Action buttons visible (Download, Restart, Delete)

**Troubleshooting:**
- If modal blank: Check browser console for errors
- If transcript missing: Check backend storage directory
- If metadata incomplete: Verify transcription completed successfully

---

### 5. Download Transcript
**Expected Behavior:**
- Download buttons trigger file downloads
- Files download with correct format
- Content matches expected transcript

**Steps:**
1. In JobDetailModal, locate download buttons
2. Click "Download TXT" (or other format)
3. Verify file downloads
4. Open downloaded file
5. Verify content:
   - Text matches audio content
   - Timestamps present (if enabled)
   - Speaker labels present (if enabled)
   - Formatting is correct

**Success Criteria:**
- ✅ File downloads successfully
- ✅ Filename includes job ID and format
- ✅ Transcript content is accurate
- ✅ Timestamps formatted correctly (if enabled)
- ✅ Multiple formats work (TXT, MD, SRT, VTT, JSON, DOCX)

**Troubleshooting:**
- If 404 on download: Check transcript file exists in backend storage
- If empty file: Check transcription completed without errors
- If corrupt file: Check backend logs during download
- If wrong content: Verify correct job ID in URL

---

### 6. Additional Validation (Optional)

#### Test Job Restart
1. Click "Restart" button in JobDetailModal
2. Confirm restart action
3. Verify job status returns to "queued"
4. Watch job process again

**Success Criteria:**
- ✅ Job re-processes successfully
- ✅ New transcript generated
- ✅ Original transcript preserved or versioned

#### Test Job Deletion
1. Select a completed job
2. Click "Delete" button
3. Confirm deletion
4. Verify job removed from list

**Success Criteria:**
- ✅ Job disappears from Dashboard
- ✅ Confirmation dialog appears before deletion
- ✅ No errors in console

#### Test Search and Filters
1. Type filename in search bar
2. Verify job appears/disappears based on query
3. Apply status filter (completed, processing, etc.)
4. Verify filtered results correct

**Success Criteria:**
- ✅ Search works on filename
- ✅ Filters work correctly
- ✅ Clear/reset filter works

---

## Success Summary

✅ **All Tests Passed** - The vertical slice is working correctly:
- Login authentication successful
- File upload and job creation working
- Real-time progress monitoring functional
- Job details display correctly
- Transcript download working for all formats
- Core workflow complete: Upload → Process → View → Download

❌ **Test Failed** - Document failure details:
- Step that failed: _______
- Error message: _______
- Screenshot/logs: _______
- Next steps: _______

---

## Common Issues and Solutions

### Backend Not Running
**Symptoms:** Connection refused, 404 errors on API calls  
**Solution:** Start backend with `ENVIRONMENT=production uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir app`

### Frontend Not Running
**Symptoms:** Cannot access http://localhost:5173  
**Solution:** Start frontend with `npm run start:prod -- --host 127.0.0.1 --port 5173` in the frontend directory

### CORS Errors
**Symptoms:** Console shows CORS policy errors  
**Solution:** Check backend `app/config.py` includes frontend URL in `CORS_ORIGINS`

### JWT Token Issues
**Symptoms:** 401 Unauthorized on API calls  
**Solution:** 
- Clear localStorage and re-login
- Check token expiration (default 24 hours)
- Verify backend auth configuration

### File Upload Failures
**Symptoms:** 400 Bad Request on upload  
**Solution:**
- Check file size < 2GB
- Verify file format is supported
- Check backend storage directory permissions

### Transcription Stuck
**Symptoms:** Job stays in "processing" indefinitely  
**Solution:**
- Check backend logs for errors
- Verify Whisper model downloaded (first run downloads models)
- Check system resources (CPU, memory)
- Check MAX_CONCURRENT_JOBS setting

### Missing Transcript
**Symptoms:** Download fails or file empty  
**Solution:**
- Check backend storage directory exists: `backend/storage/transcripts/`
- Verify transcription completed without errors
- Check file permissions

---

## Performance Benchmarks

Expected processing times (approximate):
- **Tiny model**: 1x real-time (10min audio = 10min processing)
- **Base model**: 1.5x real-time (10min audio = 15min processing)
- **Small model**: 2x real-time (10min audio = 20min processing)
- **Medium model**: 4x real-time (10min audio = 40min processing)
- **Large model**: 8x real-time (10min audio = 80min processing)

*Note: Times vary based on CPU performance. GPU acceleration significantly faster.*

---

## Test Evidence

Document your test run:

**Date:** _______  
**Tester:** _______  
**Environment:**
- OS: _______
- Python version: _______
- Node version: _______
- Browser: _______

**Test File:**
- Filename: _______
- Size: _______
- Duration: _______
- Format: _______

**Results:**
- Upload time: _______
- Processing time: _______
- Model used: _______
- Transcript accuracy: _______
- All steps completed: ✅ / ❌

**Notes:** _______

---

## Next Steps

After successful smoke test:
1. Run automated test suites (`pytest` for backend, `npm test` for frontend)
2. Set up CI/CD pipeline (CI-001)
3. Deploy to staging environment
4. Conduct user acceptance testing
5. Address remaining Sprint 0 tasks (TEST-004)

```
