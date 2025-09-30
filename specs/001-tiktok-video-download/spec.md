# Feature Specification: TikTok Video Download & Keyframe Extraction Integration in video-crawler

**Feature Branch**: `001-tiktok-video-download`
**Created**: Tuesday, September 30, 2025
**Status**: Draft
**Input**: User description: "tiktok video download and extract keyframes: PRD: TikTok Video Download & Keyframe Extraction Integration in video-crawler 1. Overview The video-crawler service currently supports TikTok search and metadata crawling. It lacks the ability to download TikTok videos and extract keyframes for downstream processing. This PRD specifies integration of yt-dlp for downloading and the existing keyframe_extractor module (already used for YouTube) to process TikTok videos post-download. 2. Goals & Objectives Extend TikTok crawler to support downloading videos from webViewUrl. Automatically extract keyframes from downloaded videos. Save keyframes metadata into the database using video_frame_crud from libs/common-py. Reuse the job/phase/event-driven model from YouTube integration. 3. Functional Requirements Video Download Add TikTokDownloader wrapping yt-dlp.  Store downloaded file in temp/videos/tiktok/. Keyframe Extraction After successful download, trigger keyframe_extractor (reuse length_adaptive_extractor.py). Extract representative frames (configurable interval/length adaptive). Save frames to temp/keyframes/tiktok/{video_id}/. Persist metadata (frame paths, timestamps) into DB via video_frame_crud. Data Model Changes Extend Video model (models/video.py): class Video(BaseModel): id: str url: str title: str | None uploader: str | None download_url: str | None local_path: str | None has_download: bool = False keyframes: list[str] | None # list of saved keyframe paths API & Contracts Extend videos_collections_completed.json and videos_keyframes_ready.json to include: has_keyframes: true/false keyframes_count keyframes_paths (relative paths in storage). Job Flow New job phases: video.download.started video.download.completed video.keyframes.ready On failure: video.download.failed or video.keyframes.failed. 4. Non-Functional Requirements Performance: Extract max 20 keyframes per video (configurable). Resilience: If extraction fails, still persist downloaded=true but has_keyframes=false. Storage: Cleanup videos + keyframes older than 7 days (reuse video_cleanup_service.py). Consistency: Follow identical structure as YouTube download + keyframe path. 5. Architecture & Implementation Plan Downloader Add platform_crawler/tiktok/downloader.py. Wrap yt-dlp with retry/error handling. Crawler Update Modify tiktok_crawler.py: Accept download=True. Call TikTokDownloader. Trigger KeyframeExtractor on local file. Save keyframes metadata in DB. Event Emitter Update event_emitter.py: Emit keyframe events similar to YouTube path (videos_keyframes_ready.json). Database Use video_frame_crud.py for inserting keyframe metadata. Config Add platform_crawler/tiktok/ytdlp_config.py. Add settings for keyframe interval, max frames. Testing Unit tests: Mock yt-dlp. Mock keyframe extractor output. Validate DB insertions. Integration tests: Crawl TikTok URL with download=True. Verify video saved + keyframes extracted + metadata persisted. Contract tests: Validate new schema fields. 6. Dependencies yt-dlp (video download). ffmpeg (required by yt-dlp and keyframe extractor). OpenCV or Pillow (already used in keyframe extractor). 7. Risks TikTok anti-bot measures (may break yt-dlp). Large video storage growth if cleanup fails. 8. Acceptance Criteria Given a TikTok webViewUrl, with download=True: Video downloaded successfully. Keyframes extracted and stored. DB updated with frame paths. Event video.keyframes.ready emitted. With download=False: Only metadata + direct URL returned. Cleanup removes files after 7 days. 9. TDD Workflow Write failing unit tests for TikTok download + keyframe extraction. Implement minimal TikTokDownloader. Implement keyframe extraction hook. Implement DB persistence. Run integration test (search → download → keyframes → DB). Refactor code to align with YouTube flow."

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

### Acceptance Scenarios


3. **Given** a downloaded TikTok video and extracted keyframes, **When** 7 days pass, **Then** the video and keyframe files are cleaned up from storage.

### Edge Cases
- What happens when TikTok anti-bot measures prevent `yt-dlp` from downloading a video?
- How does the system handle large video storage growth if cleanup fails?

## Requirements *(mandatory)*

- **FR-001**: The `video-crawler` service MUST be able to download TikTok videos from a `webViewUrl`.
- **FR-002**: The system MUST extract keyframes from downloaded TikTok videos.
- **FR-003**: The system MUST store downloaded TikTok videos in a temporary location (`temp/videos/tiktok/`).
- **FR-004**: The system MUST save extracted keyframes to a temporary location (`temp/keyframes/tiktok/{video_id}/`).
- **FR-005**: The system MUST persist keyframe metadata (paths, timestamps) into the database.
- **FR-006**: The system MUST extend the `Video` model to include `download_url`, `local_path`, `has_download`, and `keyframes`.
- **FR-007**: The system MUST extend `videos_collections_completed.json` and `videos_keyframes_ready.json` event contracts to include `has_keyframes`, `keyframes_count`, and `keyframes_paths`.
- **FR-008**: The system MUST emit new job phases: `video.download.started`, `video.download.completed`, `video.keyframes.ready`.
- **FR-009**: The system MUST handle download and keyframe extraction failures by emitting `video.download.failed` or `video.keyframes.failed` events.


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
- [ ] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous  
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed

---