
# Refactoring Plan: ProductsPanel & VideosPanel

The `ProductsPanel` files and `VideosPanel` files share a lot of duplicated structure and logic. Please  **refactor them following the DRY (Don't Repeat Yourself) principle** .

---

## Step 1: Testing Before Refactoring

* Write **simple Jest tests** for both panels to capture current behavior.
* Make sure all tests pass  **before any refactoring work** .
* These tests will serve as a safety net to ensure functionality remains unchanged.

---

## Step 2: Identify Commonality

* Locate **shared components, hooks, and utilities** in `ProductsPanel` and `VideosPanel`.
* Examples may include:
  * Layout structure
  * Data-fetching hooks
  * Status display logic
  * Rendering patterns for item lists

---

## Step 3: Extract Shared Logic

* Create a new folder: `src/components/CommonPanel/`
* Move reusable pieces into this folder:
  * `CommonPanelLayout.tsx`
  * `usePanelData.ts`
  * Shared utility functions (formatting, filtering, etc.)
* Ensure code is **generic** enough to be reused across panels.

---

## Step 4: Keep Specific Logic Separate

* Maintain **panel-specific code** in:
  * `ProductsPanel`
  * `VideosPanel`
* These should import from `CommonPanel` where possible.

---

## Step 5: Validate After Refactoring

* Run the Jest test suite again to confirm no regressions.
* Verify that:
  * Props remain consistent
  * API calls are unchanged
  * UI rendering matches pre-refactor state

---

## Step 6: Future-Proofing

* Structure the `CommonPanel` so it’s easy to extend for future panels (e.g. `UsersPanel`, `OrdersPanel`).
* Goal: **minimal duplication** +  **maximum reusability** .

---

✅ Deliverable: Cleaner, DRY-compliant panel structure with passing Jest tests and no loss of functionality.
