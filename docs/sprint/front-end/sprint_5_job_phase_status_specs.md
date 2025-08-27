# Job Phase Status Line Specifications

This document specifies how the **status line** should be displayed in the front end based on the backend `phase` values.

---

## Supported Phases

- `unknown`
- `collection`
- `feature_extraction`
- `matching`
- `evidence`
- `completed`
- `failed`

---

## Phase Details

### 1. `unknown`

- **Text:** "Status unknown."
- **Icon/Effect:** none or neutral placeholder.
- **Color:** gray.

### 2. `collection`

- **Text:** "Collecting products and videos…"
- **Effects:**
  - Spinner animation
  - Animated dots ( … )
  - Indeterminate progress bar
- **Color:** blue.
- **Optional badges:**
  - Show "✔ Products done" once `products.collections.completed` event is received.
  - Show "✔ Videos done" once `videos.collections.completed` event is received.
  - When both are done, still remain in `collection` until backend transitions to `feature_extraction`, but display a badge "Collection finished".

### 3. `feature_extraction`

- **Text:** "Extracting features (images / video frames)…"
- **Effect:** indeterminate progress bar.
- **Color:** yellow.
- **Backend condition:** waits for all embedding & keypoint events to complete before moving to `matching`.

### 4. `matching`

- **Text:** "Matching products with videos…"
- **Effect:** spinner.
- **Color:** purple.
- **Backend condition:** waits for `matchings.process.completed` event to move to `evidence`.

### 5. `evidence`

- **Text:** "Generating visual evidence…"
- **Effect:** indeterminate progress bar.
- **Color:** orange.
- **Backend condition:** waits for `evidences.generation.completed` to move to `completed`.

### 6. `completed`

- **Text:** "✅ Completed!"
- **Effect:** none.
- **Color:** green.
- **Behavior:** stop polling.

### 7. `failed`

- **Text:** "❌ Job failed."
- **Effect:** none.
- **Color:** red.
- **Behavior:** stop polling.

---

## Test driven development

Write playwright test firsts to ensure functionality. Make them fail only then develop the codebase

## Additional Notes

- Always wrap the status line in `aria-live="polite"` for accessibility.
- Poll `/status/{job_id}` every 5 seconds (or based on `shouldPoll`).
- Stop polling when entering `completed` or `failed`.
- Optionally map each phase to a progress percentage: `unknown=0%`, `collection=20%`, `feature_extraction=50%`, `matching=80%`, `evidence=90%`, `completed=100%`, `failed=0%`.
