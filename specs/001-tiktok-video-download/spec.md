# Feature Specification: TikTok Video Download & Keyframe Extraction Integration in video-crawler

**Feature Branch**: `001-tiktok-video-download`
**Created**: Tuesday, September 30, 2025
**Status**: Draft
**Input**: User description: "tiktok video download and extract keyframes: PRD: TikTok Video Download & Keyframe Extraction Integration in video-crawler 1. Overview The video-crawler service currently supports TikTok search and metadata crawling. It lacks the ability to download TikTok videos and extract keyframes for downstream processing. This PRD specifies integration of yt-dlp for downloading and the existing keyframe_extractor module (already used for YouTube) to process TikTok videos post-download. 2. Goals & Objectives Extend TikTok crawler to support downloading videos from webViewUrl. Automatically extract keyframes from downloaded videos. Save keyframes metadata into the database using video_frame_crud from libs/common-py. Reuse the job/phase/event-driven model from YouTube integration. 3. Functional Requirements Video Download Add TikTokDownloader wrapping yt-dlp.  Store downloaded file in temp/videos/tiktok/. Keyframe Extraction After successful download, trigger keyframe_extractor (reuse length_adaptive_extractor.py). Extract representative frames (configurable interval/length adaptive). Save frames to temp/keyframes/tiktok/{video_id}/. Persist metadata (frame paths, timestamps) into DB via video_frame_crud. Data Model Changes Extend Video model (models/video.py): class Video(BaseModel): id: str url: str title: str | None uploader: str | None download_url: str | None local_path: str | None has_download: bool = False keyframes: list[str] | None # list of saved keyframe paths API & Contracts Extend videos_collections_completed.json and videos_keyframes_ready.json to include: has_keyframes: true/false keyframes_count keyframes_paths (relative paths in storage). Job Flow New job phases: video.download.started video.download.completed video.keyframes.ready On failure: video.download.failed or video.keyframes.failed. 4. Non-Functional Requirements Performance: Extract max 20 keyframes per video (configurable). Resilience: If extraction fails, still persist do... [truncated]

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies  
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
The `video-crawler` service needs to download TikTok videos from a `webViewUrl` and extract keyframes for further processing, similar to how YouTube videos are handled, to enable product-video matching for TikTok content.

### Test Video Link
- Test Video: https://www.tiktok.com/@lanxinx/video/7548644205690670337

### Acceptance Scenarios

1. **Given** TikTok video URLs are provided, **When** system processes them, **Then** videos are downloaded to DATA_ROOT_CONTAINER/videos/tiktok/ and keyframes extracted to DATA_ROOT_CONTAINER/keyframes/tiktok/{video_id}/.
2. **Given** videos and keyframes are processed, **When** job completes, **Then** metadata is persisted to database with video paths and keyframe information.
3. **Given** videos have been stored for 7 days, **When** cleanup process runs, **Then** video files are removed while keyframe files are kept permanently.
4. **Given** TikTok anti-bot measures block download, **When** download attempts fail, **Then** system logs specific error and continues processing with retry logic.
5. **Given** video cleanup fails, **When** cleanup process runs, **Then** system logs error but maintains normal operation.

### Edge Cases

## Anti-Bot Measures Handling
- **FR-011**: When TikTok anti-bot measures prevent downloading, the system MUST log the failure with specific error details and continue processing the next video in the queue.
- **FR-012**: The system MUST retry failed downloads up to 3 times with exponential backoff before marking them as permanently failed.

## Cleanup Failure Resilience
- **FR-013**: If video cleanup after 7 days fails, the system MUST log the error and continue normal operation, not impact video processing or matching functionality.

## Requirements *(mandatory)*

- **FR-001**: The `video-crawler` service MUST be able to download TikTok videos from a `webViewUrl`.
- **FR-002**: The system MUST extract keyframes from downloaded TikTok videos.
- **FR-003**: The system MUST store downloaded TikTok videos in the appropriate video directory (`DATA_ROOT_CONTAINER/videos/tiktok/`) like the YouTube counterpart.
- **FR-004**: The system MUST save extracted keyframes to the keyframe directory (`DATA_ROOT_CONTAINER/keyframes/tiktok/{video_id}/`) like the YouTube counterpart.
- **FR-005**: The system MUST persist keyframe metadata (paths, timestamps) into the database.
- **FR-006**: The system MUST extend the `Video` model to include `download_url`, `local_path`, `has_download`, and `keyframes`.
- **FR-007**: The system MUST implement cleanup logic to remove video files after 7 days (keyframe files are kept permanently).
- **FR-008**: The system MUST handle anti-bot measures by logging specific failure details and continuing processing.
- **FR-009**: The system MUST retry failed downloads up to 3 times with exponential backoff.
- **FR-010**: The system MUST maintain normal operation if cleanup fails, with error logging.
- **FR-011**: The system MUST log specific failure details and continue processing when anti-bot measures block downloads.
- **FR-012**: The system MUST retry failed downloads up to 3 times with exponential backoff before marking them as permanently failed.
- **FR-013**: The system MUST maintain normal operation if cleanup fails, with error logging and no impact on processing functionality.


### Key Entities *(include if feature involves data)*
- **Video**: Represents a TikTok video, including its ID, URL, title, uploader, download URL, local path, download status, and a list of keyframe paths.
- **Keyframe**: Represents an extracted image from a video, with associated metadata like path and timestamp.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
## Clarifications

### Session 2025-09-30

- Q: How should the system handle TikTok videos that are unavailable or restricted due to region/country restrictions when using yt-dlp? → A: Skip the video with a log entry and continue processing other videos
- Q: What should be the maximum file size limit for TikTok videos that the system will attempt to download? → A: 500 MB
- Q: How should the system handle TikTok videos that are age-restricted or marked as inappropriate content? → A: attempt to download best effort
- Q: What is the expected retry behavior when a TikTok video download fails due to network issues or temporary unavailability? → A: Retry up to 3 times with exponential backoff
- Q: Should the system validate the downloaded TikTok video file integrity before proceeding with keyframe extraction? → A: Yes, perform basic validation (file exists, non-zero size)

- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed

---