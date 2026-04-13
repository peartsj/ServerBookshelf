# Frontend Flow Notes

Upload-first flow is now scaffolded in `frontend/` and backed by API endpoints.

## Desired add-book UX

1. User logs in with username + password.
2. User lands on the library page.
3. User clicks `Add New Book` to open the modal.
4. User uploads ebook file first.
5. UI captures returned file path/id.
6. User fills metadata form (title, author, genres, etc.).
7. UI submits metadata + file reference to create the ebook entry.

Upload response now includes `checksum_sha256`, which the frontend forwards in the `files` payload when creating the ebook.
The upload panel now surfaces uploaded filename, size, and full SHA-256 checksum so users can verify file identity before metadata submit.
Current delivery scope is EPUB-only for uploads to reduce implementation surface.

## Backend implications for later

- Dedicated upload endpoint implemented: `POST /uploads/ebook-file`.
- Keep `has_adaptation` defaulting to false unless user explicitly sets it.
- Attach actions to the active user identity so each user only sees their library.

## Remaining polish work

- Add pagination or virtualized rendering for large libraries.
- Add toast-style success/error notifications.

Current list handling consumes the backend paginated envelope (`items`, `has_next`, `has_previous`, and related metadata) instead of a raw array.

## Completed in current milestone

- Upload progress feedback in frontend.
- Basic inline validation for metadata inputs.
- Edit/delete/category attach-detach controls in frontend list view.
- Backend staged integration test for upload -> create -> categorize.
- Staged flow persists upload checksum into ebook file metadata.
- Category field supports datalist autocomplete and quick-add chips from known/recent categories.
- UI trimmed for faster workflow: adaptation controls removed from main form/filter surface.
- Login and library are separated into different screens; backend URL input is no longer exposed.
