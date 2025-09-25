# Feature Specification: TikTok Platform Crawler

**Feature Branch**: `feat/tiktok-crawler`
**Created**: Thursday 25 September 2025
**Status**: Draft
**Input**: User description: "use the server in http://localhost:5680/, endpoint /tiktok/search as above in microservice video-crawler to make a tiktok platform crawler. branch name should be feat/tiktok-crawler"

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
As a system operator, I want to use the existing TikTok search API to crawl TikTok content, so that I can integrate TikTok data into the product-video matching system.
### Important Notes
- **PHASE 1 SCOPE**: This implementation focuses on searching and retrieving TikTok video metadata from the existing server at `http://localhost:5680/tiktok/search`.
- **OUT OF SCOPE**: Video downloading functionality is NOT part of this sprint but infrastructure will be prepared for future implementation.


### Acceptance Scenarios
1. **Given** the TikTok Search API is accessible at `http://localhost:5680/tiktok/search`, **When** a request is made to crawl TikTok content for a specific query, **Then** the system should successfully retrieve a list of TikTok videos.
2. **Given** the TikTok Search API is accessible, **When** a request is made to crawl TikTok content with `numVideos` specified, **Then** the system should attempt to retrieve the specified number of videos (up to 50).
3. **Given** the TikTok Search API is accessible, **When** a request is made to crawl TikTok content with `force_headful` set to `true`, **Then** the system should attempt to use headful browser mode for the search.

### Edge Cases
- What happens when the TikTok Search API is unavailable or returns an error?
- How does the system handle rate limits or API usage quotas from the TikTok Search API?
- What happens if the `numVideos` requested exceeds the API's limit (50)?

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The system MUST integrate with the external TikTok Search API at `http://localhost:5680/tiktok/search`.
- **FR-002**: The system MUST be able to send search queries to the TikTok Search API.
- **FR-003**: The system MUST be able to specify the number of videos to retrieve (`numVideos`) when making a search request.
- **FR-004**: The system MUST be able to control the browser execution mode (`force_headful`) for TikTok searches.
- **FR-005**: The system MUST process the `TikTokSearchResponse` and extract relevant video information (id, caption, authorHandle, likeCount, uploadTime, webViewUrl) from the results array.
- **FR-006**: The system MUST handle potential errors and unavailability of the TikTok Search API gracefully.
- **FR-007**: The system MUST be implemented within the `video-crawler` microservice.
- **FR-008**: The system MUST stream search results in real-time as videos are found, rather than waiting for batch completion.
- **FR-009**: The system MUST provide public API access without authentication, implementing appropriate rate limiting to prevent abuse.

### Non-Functional Requirements
- **NFR-001**: The system MUST provide real-time streaming updates as TikTok videos are discovered and processed.
- **NFR-002**: The system MUST implement retry logic with exponential backoff when the TikTok Search API fails, attempting up to 3 retries with 15-second intervals.
- **NFR-003**: The system MUST support medium-scale operations handling 100-1000 videos per day with moderate query frequency.

### Key Entities *(include if feature involves data)*
- **TikTokVideo**: Represents a single video retrieved from TikTok, containing attributes:
  - `id` (string): Unique video identifier
  - `caption` (string): Video caption/text content (may be empty)
  - `authorHandle` (string): TikTok username/author handle
  - `likeCount` (number): Number of likes on the video
  - `uploadTime` (string): Video upload timestamp
  - `webViewUrl` (string): Direct URL to view the video on TikTok

**Response Schema**:
- `results` (array): Array of TikTokVideo objects
- `totalResults` (number): Total number of results available
- `query` (string): Original search query executed
- `search_metadata` (object): Execution metadata containing `executed_path`, `execution_time`, and `request_hash`
---
- Q: What is the scope of this TikTok crawler implementation? → A: PHASE 1: Search and metadata retrieval only (video downloading deferred to Phase 2)

## Clarifications

### Session 2025-09-25

- Q: What should be the primary data processing model for the TikTok crawler? → A: Real-time streaming of results as videos are found
- Q: When the TikTok Search API fails, what should happen? → A: B with 3 attempts, 15 seconds apart
- Q: What level of access should different users have to the TikTok crawler functionality? → A: D
- Q: How long should TikTok video data be retained in the system? → A: B, similar to youtube platform
- Q: What is the expected maximum scale for TikTok crawling operations? → A: B
- **NFR-004**: The system MUST retain TikTok video data for short-term (7 days) similar to YouTube platform data retention policy.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---