import {
  apiAttachCategoryToEbook,
  apiCreateCategory,
  apiCreateEbook,
  apiDownloadEbook,
  apiDeleteEbook,
  apiDetachCategoryFromEbook,
  apiGetEbookCover,
  apiListCategories,
  apiListEbooks,
  apiLogin,
  apiRegister,
  apiMe,
  apiUpdateEbook,
  apiUploadEbookFileWithProgress,
  getDefaultApiBase,
} from "./api.js";

const apiBase = getDefaultApiBase();

const authScreen = document.querySelector("#auth-screen");
const appScreen = document.querySelector("#app-screen");
const authTitle = document.querySelector("#auth-title");
const authSubhead = document.querySelector("#auth-subhead");
const loginForm = document.querySelector("#login-form");
const loginUsernameInput = document.querySelector("#login-username");
const loginPasswordInput = document.querySelector("#login-password");
const loginPasswordConfirmInput = document.querySelector("#login-password-confirm");
const registerConfirmField = document.querySelector("#register-confirm-field");
const authModeToggle = document.querySelector("#auth-mode-toggle");
const loginButton = document.querySelector("#login");
const loginStatus = document.querySelector("#login-status");

const authStatus = document.querySelector("#auth-status");
const loadLibraryButton = document.querySelector("#load-library");
const logoutButton = document.querySelector("#logout");
const openAddBookButton = document.querySelector("#open-add-book");
const closeAddBookButton = document.querySelector("#close-add-book");
const bookModal = document.querySelector("#book-modal");
const bookDetailModal = document.querySelector("#book-detail-modal");
const closeBookDetailButton = document.querySelector("#close-book-detail");

const detailTitle = document.querySelector("#detail-title");
const detailAuthor = document.querySelector("#detail-author");
const detailOwner = document.querySelector("#detail-owner");
const detailPublisher = document.querySelector("#detail-publisher");
const detailYear = document.querySelector("#detail-year");
const detailSeries = document.querySelector("#detail-series");
const detailSeriesPosition = document.querySelector("#detail-series-position");
const detailCategories = document.querySelector("#detail-categories");
const detailAdaptation = document.querySelector("#detail-adaptation");
const detailLanguage = document.querySelector("#detail-language");
const detailIsbn = document.querySelector("#detail-isbn");
const detailDescription = document.querySelector("#detail-description");
const detailFile = document.querySelector("#detail-file");
const detailStoragePath = document.querySelector("#detail-storage-path");

const clearFiltersButton = document.querySelector("#clear-filters");
const pageStatus = document.querySelector("#page-status");
const prevPageButton = document.querySelector("#prev-page");
const nextPageButton = document.querySelector("#next-page");

const filterTitleInput = document.querySelector("#filter-title");
const filterAuthorInput = document.querySelector("#filter-author");
const filterCategoryInput = document.querySelector("#filter-category");
const filterYearInput = document.querySelector("#filter-year");
const sortByInput = document.querySelector("#sort-by");
const sortDirInput = document.querySelector("#sort-dir");
const pageSizeInput = document.querySelector("#page-size");

const uploadForm = document.querySelector("#upload-form");
const metadataForm = document.querySelector("#metadata-form");
const ebookFileInput = document.querySelector("#ebook-file");
const uploadStatus = document.querySelector("#upload-status");
const uploadDetails = document.querySelector("#upload-details");
const uploadFileName = document.querySelector("#upload-file-name");
const uploadSize = document.querySelector("#upload-size");
const uploadChecksum = document.querySelector("#upload-checksum");
const formStatus = document.querySelector("#form-status");
const ebookList = document.querySelector("#ebooks-list");

const titleInput = document.querySelector("#title");
const authorInput = document.querySelector("#author");
const publisherInput = document.querySelector("#publisher");
const yearInput = document.querySelector("#year");
const seriesInput = document.querySelector("#series");
const seriesPositionInput = document.querySelector("#series-position");
const categoriesInput = document.querySelector("#categories");
const categorySuggestions = document.querySelector("#category-suggestions");
const quickCategories = document.querySelector("#quick-categories");
const clearCategoriesButton = document.querySelector("#clear-categories");
const descriptionInput = document.querySelector("#description");

let uploadedFile = null;
let categoryCache = [];
let recentCategoryNames = loadRecentCategoryNames();
let coverObjectUrls = new Map();
let authToken = localStorage.getItem("bookshelf_auth_token");
let activeUsername = localStorage.getItem("bookshelf_active_username") || "";
let isRegisterMode = false;
let currentPage = 1;
let lastPageItemCount = 0;
let paginationMeta = {
  totalCount: 0,
  totalPages: 0,
  hasNext: false,
  hasPrevious: false,
};

function parseCategoryNames(raw) {
  const names = raw
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean);

  return [...new Set(names.map((name) => name.toLowerCase()))].map(
    (lowerName) => names.find((name) => name.toLowerCase() === lowerName) || lowerName
  );
}

function loadRecentCategoryNames() {
  try {
    const stored = localStorage.getItem("bookshelf_recent_categories");
    if (!stored) {
      return [];
    }
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .map((name) => (typeof name === "string" ? name.trim() : ""))
      .filter(Boolean)
      .slice(0, 12);
  } catch (_) {
    return [];
  }
}

function saveRecentCategoryNames(names) {
  try {
    localStorage.setItem("bookshelf_recent_categories", JSON.stringify(names.slice(0, 12)));
  } catch (_) {
    // Ignore storage failures.
  }
}

function getKnownCategoryNames() {
  const map = new Map();

  for (const name of recentCategoryNames) {
    const normalized = name.toLowerCase();
    if (!map.has(normalized)) {
      map.set(normalized, name);
    }
  }

  for (const category of categoryCache) {
    const name = category.name.trim();
    const normalized = name.toLowerCase();
    if (!map.has(normalized)) {
      map.set(normalized, name);
    }
  }

  return [...map.values()];
}

function recordRecentCategoryNames(names) {
  if (!names.length) {
    return;
  }

  const existing = getKnownCategoryNames();
  const map = new Map();

  for (const name of names) {
    const normalized = name.toLowerCase();
    if (!map.has(normalized)) {
      map.set(normalized, name);
    }
  }

  for (const name of existing) {
    const normalized = name.toLowerCase();
    if (!map.has(normalized)) {
      map.set(normalized, name);
    }
  }

  recentCategoryNames = [...map.values()].slice(0, 12);
  saveRecentCategoryNames(recentCategoryNames);
}

function addCategoryToInput(name) {
  const current = parseCategoryNames(categoriesInput.value);
  if (current.some((existing) => existing.toLowerCase() === name.toLowerCase())) {
    return;
  }
  current.push(name);
  categoriesInput.value = current.join(", ");
}

function updateCategorySuggestions() {
  categorySuggestions.innerHTML = "";
  const names = getKnownCategoryNames().slice(0, 20);
  for (const name of names) {
    const option = document.createElement("option");
    option.value = name;
    categorySuggestions.appendChild(option);
  }
}

function renderQuickCategoryButtons() {
  quickCategories.innerHTML = "";
  const names = getKnownCategoryNames().slice(0, 10);
  if (!names.length) {
    return;
  }

  const selected = new Set(parseCategoryNames(categoriesInput.value).map((name) => name.toLowerCase()));
  for (const name of names) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn small ghost";
    if (selected.has(name.toLowerCase())) {
      button.classList.add("active");
    }
    button.textContent = name;
    button.addEventListener("click", () => {
      addCategoryToInput(name);
      renderQuickCategoryButtons();
    });
    quickCategories.appendChild(button);
  }
}

function refreshCategoryAssistUi() {
  updateCategorySuggestions();
  renderQuickCategoryButtons();
}

function getLibraryFilters() {
  const filters = {};
  if (filterTitleInput.value.trim()) {
    filters.title = filterTitleInput.value.trim();
  }
  if (filterAuthorInput.value.trim()) {
    filters.author = filterAuthorInput.value.trim();
  }
  if (filterCategoryInput.value.trim()) {
    filters.category = filterCategoryInput.value.trim();
  }
  if (filterYearInput.value) {
    filters.publishing_year = Number(filterYearInput.value);
  }

  filters.page = currentPage;
  filters.page_size = Number(pageSizeInput.value);
  filters.sort_by = sortByInput.value;
  filters.sort_dir = sortDirInput.value;

  return filters;
}

function updatePageControls() {
  pageStatus.textContent = `Page ${currentPage} of ${paginationMeta.totalPages || 0} (${paginationMeta.totalCount} total, ${lastPageItemCount} on page)`;
  prevPageButton.disabled = !paginationMeta.hasPrevious;
  nextPageButton.disabled = !paginationMeta.hasNext;
}

function setLoginStatus(message) {
  loginStatus.textContent = message;
}

function setAuthMode(registerMode) {
  isRegisterMode = registerMode;

  authTitle.textContent = registerMode ? "Create Your Account" : "Bookshelf Login";
  authSubhead.textContent = registerMode
    ? "Register with a username and password."
    : "Sign in to access your library.";
  loginButton.textContent = registerMode ? "Register" : "Login";
  authModeToggle.textContent = registerMode ? "Back to login" : "Create account";

  registerConfirmField.classList.toggle("hidden", !registerMode);
  loginPasswordConfirmInput.required = registerMode;
  loginPasswordInput.autocomplete = registerMode ? "new-password" : "current-password";
  setLoginStatus("");
}

function setAuthStatus(message) {
  authStatus.textContent = message;
}

function setUploadStatus(message) {
  uploadStatus.textContent = message;
}

function setFormStatus(message) {
  formStatus.textContent = message;
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return "unknown";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function showUploadDetails(upload) {
  if (!upload) {
    uploadDetails.classList.add("hidden");
    uploadFileName.textContent = "-";
    uploadSize.textContent = "-";
    uploadChecksum.textContent = "-";
    return;
  }

  uploadFileName.textContent = upload.original_filename || upload.stored_filename || "unknown";
  uploadSize.textContent = formatBytes(upload.size_bytes);
  uploadChecksum.textContent = upload.checksum_sha256 || "not provided";
  uploadDetails.classList.remove("hidden");
}

function fillDetailField(target, value) {
  target.textContent = value === null || value === undefined || value === "" ? "-" : String(value);
}

function openBookDetailModal(ebook) {
  const primaryFile = ebook.files.find((file) => file.media_type === "ebook") || ebook.files[0] || null;

  fillDetailField(detailTitle, ebook.title);
  fillDetailField(detailAuthor, ebook.author_name);
  fillDetailField(detailOwner, ebook.owner_username);
  fillDetailField(detailPublisher, ebook.publisher_name);
  fillDetailField(detailYear, ebook.publishing_year);
  fillDetailField(detailSeries, ebook.series_name);
  fillDetailField(detailSeriesPosition, ebook.series_position);
  fillDetailField(detailCategories, ebook.genre_names.join(", "));
  fillDetailField(detailAdaptation, ebook.has_adaptation ? "Yes" : "No");
  fillDetailField(detailLanguage, ebook.language_code);
  fillDetailField(detailIsbn, ebook.isbn_13);
  fillDetailField(detailDescription, ebook.description);
  fillDetailField(
    detailFile,
    primaryFile
      ? `${primaryFile.file_format}${primaryFile.file_size_bytes ? ` (${formatBytes(primaryFile.file_size_bytes)})` : ""}`
      : null
  );
  fillDetailField(detailStoragePath, primaryFile?.storage_path || null);

  bookDetailModal.classList.remove("hidden");
}

function clearCoverObjectUrls() {
  for (const url of coverObjectUrls.values()) {
    URL.revokeObjectURL(url);
  }
  coverObjectUrls.clear();
}

async function loadEbookCoverThumbnail(ebookId, imageElement, fallbackElement) {
  try {
    const coverBlob = await apiGetEbookCover(apiBase, ebookId, requireAuthToken());
    if (!coverBlob) {
      imageElement.classList.add("hidden");
      fallbackElement.classList.remove("hidden");
      return;
    }

    const existing = coverObjectUrls.get(ebookId);
    if (existing) {
      URL.revokeObjectURL(existing);
    }

    const objectUrl = URL.createObjectURL(coverBlob);
    coverObjectUrls.set(ebookId, objectUrl);

    if (!document.body.contains(imageElement)) {
      URL.revokeObjectURL(objectUrl);
      coverObjectUrls.delete(ebookId);
      return;
    }

    imageElement.src = objectUrl;
    imageElement.classList.remove("hidden");
    fallbackElement.classList.add("hidden");
  } catch (_) {
    imageElement.classList.add("hidden");
    fallbackElement.classList.remove("hidden");
  }
}

function clearBookForm() {
  titleInput.value = "";
  authorInput.value = "";
  publisherInput.value = "";
  yearInput.value = "";
  seriesInput.value = "";
  seriesPositionInput.value = "";
  categoriesInput.value = "";
  descriptionInput.value = "";
  uploadedFile = null;
  ebookFileInput.value = "";
  setUploadStatus("No file uploaded yet.");
  setFormStatus("");
  showUploadDetails(null);
  refreshCategoryAssistUi();
}

function setButtonLoading(button, loading, loadingText) {
  if (!button) {
    return;
  }
  if (!button.dataset.originalText) {
    button.dataset.originalText = button.textContent;
  }
  button.disabled = loading;
  button.textContent = loading ? loadingText : button.dataset.originalText;
}

function sanitizeFilenameBase(value) {
  const cleaned = String(value || "")
    .replace(/[^a-zA-Z0-9 _.-]/g, "_")
    .trim()
    .replace(/\s+/g, "_");
  return cleaned || "ebook";
}

function triggerBlobDownload(blob, fileName) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

function requireAuthToken() {
  if (!authToken) {
    throw new Error("Login required");
  }
  return authToken;
}

function showAppScreen() {
  authScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
  setAuthStatus(`Signed in as ${activeUsername}`);
}

function showAuthScreen() {
  appScreen.classList.add("hidden");
  authScreen.classList.remove("hidden");
  bookModal.classList.add("hidden");
  clearCoverObjectUrls();
}

function logout() {
  authToken = null;
  activeUsername = "";
  localStorage.removeItem("bookshelf_auth_token");
  localStorage.removeItem("bookshelf_active_username");
  loginPasswordInput.value = "";
  loginPasswordConfirmInput.value = "";
  clearBookForm();
  clearCoverObjectUrls();
  ebookList.innerHTML = "";
  bookDetailModal.classList.add("hidden");
  showAuthScreen();
}

async function ensureSession() {
  if (!authToken) {
    showAuthScreen();
    return false;
  }

  try {
    const me = await apiMe(apiBase, authToken);
    activeUsername = me.username;
    localStorage.setItem("bookshelf_active_username", activeUsername);
    showAppScreen();
    return true;
  } catch (_) {
    logout();
    setLoginStatus("Session expired. Please login again.");
    return false;
  }
}

function validateMetadataInputs() {
  if (!uploadedFile) {
    return "Upload a file before submitting metadata.";
  }

  if (!titleInput.value.trim()) {
    return "Title is required.";
  }

  if (!authorInput.value.trim()) {
    return "Author is required.";
  }

  if (yearInput.value) {
    const year = Number(yearInput.value);
    if (!Number.isInteger(year) || year < 0 || year > 3000) {
      return "Publishing year must be between 0 and 3000.";
    }
  }

  if (seriesPositionInput.value) {
    const seriesPosition = Number(seriesPositionInput.value);
    if (!Number.isInteger(seriesPosition) || seriesPosition < 0) {
      return "Series position must be a non-negative integer.";
    }
  }

  return null;
}

function buildEditForm(ebook) {
  const form = document.createElement("form");
  form.className = "inline-form hidden";
  form.innerHTML = `
    <div class="row">
      <div class="field">
        <label>Title</label>
        <input name="title" value="${ebook.title}" required />
      </div>
      <div class="field">
        <label>Author</label>
        <input name="author" value="${ebook.author_name}" required />
      </div>
    </div>
    <div class="row">
      <div class="field">
        <label>Publishing Year</label>
        <input name="publishing_year" type="number" min="0" max="3000" value="${ebook.publishing_year ?? ""}" />
      </div>
      <div class="field">
        <label>Description</label>
        <textarea name="description" rows="2">${ebook.description ?? ""}</textarea>
      </div>
    </div>
    <div class="inline-actions">
      <button type="submit" class="btn small">Save</button>
      <button type="button" class="btn small ghost cancel-edit">Cancel</button>
    </div>
  `;

  return form;
}

function renderEbooks(ebooks) {
  clearCoverObjectUrls();
  ebookList.innerHTML = "";
  if (!ebooks.length) {
    const empty = document.createElement("li");
    empty.textContent = "No books in this library yet.";
    ebookList.appendChild(empty);
    return;
  }

  ebooks.forEach((ebook) => {
    const item = document.createElement("li");
    item.className = "ebook-item";

    const itemLayout = document.createElement("div");
    itemLayout.className = "ebook-layout";

    const main = document.createElement("div");
    main.className = "ebook-main";

    const header = document.createElement("div");
    header.className = "ebook-header";

    const title = document.createElement("strong");
    title.textContent = `${ebook.title} by ${ebook.author_name}`;

    const owner = document.createElement("span");
    owner.textContent = `owner: ${ebook.owner_username}`;

    header.appendChild(title);
    header.appendChild(owner);

    const meta = document.createElement("div");
    meta.className = "ebook-meta";
    const primaryFile = ebook.files.find((file) => file.media_type === "ebook") || ebook.files[0] || null;
    const fileMeta = primaryFile
      ? ` | file: ${primaryFile.file_format}${primaryFile.file_size_bytes ? ` (${formatBytes(primaryFile.file_size_bytes)})` : ""}`
      : "";
    meta.textContent = `Categories: ${ebook.genre_names.join(", ") || "none"}${ebook.publishing_year ? ` | year: ${ebook.publishing_year}` : ""}${fileMeta}`;

    const categoryControls = document.createElement("div");
    categoryControls.className = "inline-actions";

    const addCategoryInput = document.createElement("input");
    addCategoryInput.placeholder = "Add category";

    const addCategoryButton = document.createElement("button");
    addCategoryButton.className = "btn small ghost";
    addCategoryButton.type = "button";
    addCategoryButton.textContent = "Attach Category";

    categoryControls.appendChild(addCategoryInput);
    categoryControls.appendChild(addCategoryButton);

    const detachControls = document.createElement("div");
    detachControls.className = "inline-actions";
    ebook.genre_names.forEach((genreName) => {
      const removeButton = document.createElement("button");
      removeButton.className = "btn small ghost";
      removeButton.type = "button";
      removeButton.textContent = `Remove ${genreName}`;
      removeButton.addEventListener("click", async () => {
        const category = categoryCache.find((entry) => entry.name.toLowerCase() === genreName.toLowerCase()) || null;
        if (!category) {
          setFormStatus(`Could not find category id for ${genreName}. Refresh and try again.`);
          return;
        }

        try {
          await apiDetachCategoryFromEbook(apiBase, ebook.id, category.id, requireAuthToken());
          await refreshLibrary();
          setFormStatus(`Removed category ${genreName} from ${ebook.title}.`);
        } catch (error) {
          setFormStatus(`Detach failed: ${error.message}`);
        }
      });
      detachControls.appendChild(removeButton);
    });

    addCategoryButton.addEventListener("click", async () => {
      const categoryName = addCategoryInput.value.trim();
      if (!categoryName) {
        return;
      }

      try {
        const category = await apiCreateCategory(apiBase, categoryName, requireAuthToken());
        await apiAttachCategoryToEbook(apiBase, ebook.id, category.id, requireAuthToken());
        addCategoryInput.value = "";
        recordRecentCategoryNames([category.name]);
        refreshCategoryAssistUi();
        await refreshLibrary();
        setFormStatus(`Attached category ${category.name} to ${ebook.title}.`);
      } catch (error) {
        setFormStatus(`Attach failed: ${error.message}`);
      }
    });

    const actionRow = document.createElement("div");
    actionRow.className = "ebook-actions";
    const detailsButton = document.createElement("button");
    detailsButton.className = "btn small ghost";
    detailsButton.type = "button";
    detailsButton.textContent = "Details";

    const editButton = document.createElement("button");
    editButton.className = "btn small";
    editButton.type = "button";
    editButton.textContent = "Edit";

    const deleteButton = document.createElement("button");
    deleteButton.className = "btn small ghost";
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";

    const downloadButton = document.createElement("button");
    downloadButton.className = "btn small ghost";
    downloadButton.type = "button";
    downloadButton.textContent = "Download";

    actionRow.appendChild(detailsButton);
    actionRow.appendChild(editButton);
    actionRow.appendChild(downloadButton);
    actionRow.appendChild(deleteButton);

    const editForm = buildEditForm(ebook);

    detailsButton.addEventListener("click", () => {
      openBookDetailModal(ebook);
    });

    editButton.addEventListener("click", () => {
      editForm.classList.toggle("hidden");
    });

    editForm.querySelector(".cancel-edit")?.addEventListener("click", () => {
      editForm.classList.add("hidden");
    });

    editForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(editForm);

      const updates = {
        title: String(formData.get("title") || "").trim(),
        author_name: String(formData.get("author") || "").trim(),
        publishing_year: formData.get("publishing_year") ? Number(formData.get("publishing_year")) : null,
        description: String(formData.get("description") || "").trim() || null,
      };

      try {
        await apiUpdateEbook(apiBase, ebook.id, updates, requireAuthToken());
        editForm.classList.add("hidden");
        await refreshLibrary();
        setFormStatus(`Updated ${ebook.title}.`);
      } catch (error) {
        setFormStatus(`Update failed: ${error.message}`);
      }
    });

    deleteButton.addEventListener("click", async () => {
      const shouldDelete = confirm(`Delete ${ebook.title}?`);
      if (!shouldDelete) {
        return;
      }

      try {
        await apiDeleteEbook(apiBase, ebook.id, requireAuthToken());
        await refreshLibrary();
        setFormStatus(`Deleted ${ebook.title}.`);
      } catch (error) {
        setFormStatus(`Delete failed: ${error.message}`);
      }
    });

    downloadButton.addEventListener("click", async () => {
      setButtonLoading(downloadButton, true, "Downloading...");
      try {
        const response = await apiDownloadEbook(apiBase, ebook.id, requireAuthToken());
        const fallbackExt = primaryFile?.file_format ? `.${primaryFile.file_format}` : "";
        const fallbackName = `${sanitizeFilenameBase(ebook.title)}${fallbackExt}`;
        triggerBlobDownload(response.blob, response.filename || fallbackName);
        setFormStatus(`Downloaded ${ebook.title}.`);
      } catch (error) {
        setFormStatus(`Download failed: ${error.message}`);
      } finally {
        setButtonLoading(downloadButton, false, "Downloading...");
      }
    });

    const coverWrap = document.createElement("div");
    coverWrap.className = "ebook-cover-wrap";

    const coverImage = document.createElement("img");
    coverImage.className = "ebook-cover hidden";
    coverImage.alt = `Cover image for ${ebook.title}`;
    coverImage.loading = "lazy";

    const coverFallback = document.createElement("div");
    coverFallback.className = "ebook-cover-fallback";
    coverFallback.textContent = "No cover";

    coverWrap.appendChild(coverImage);
    coverWrap.appendChild(coverFallback);

    if (ebook.cover_art_path) {
      loadEbookCoverThumbnail(ebook.id, coverImage, coverFallback);
    }

    main.appendChild(header);
    main.appendChild(meta);
    main.appendChild(actionRow);
    main.appendChild(categoryControls);
    main.appendChild(detachControls);
    main.appendChild(editForm);

    itemLayout.appendChild(main);
    itemLayout.appendChild(coverWrap);
    item.appendChild(itemLayout);
    ebookList.appendChild(item);
  });
}

async function refreshLibrary() {
  const token = requireAuthToken();
  const filters = getLibraryFilters();
  const [ebookResponse, categories] = await Promise.all([
    apiListEbooks(apiBase, filters, token),
    apiListCategories(apiBase, token),
  ]);

  const ebooks = ebookResponse.items || [];
  lastPageItemCount = ebooks.length;
  paginationMeta = {
    totalCount: ebookResponse.total_count ?? ebooks.length,
    totalPages: ebookResponse.total_pages ?? 0,
    hasNext: Boolean(ebookResponse.has_next),
    hasPrevious: Boolean(ebookResponse.has_previous),
  };
  if (typeof ebookResponse.page === "number") {
    currentPage = ebookResponse.page;
  }

  categoryCache = categories;
  refreshCategoryAssistUi();
  renderEbooks(ebooks);
  updatePageControls();
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = loginUsernameInput.value.trim();
  const password = loginPasswordInput.value;
  const passwordConfirmation = loginPasswordConfirmInput.value;

  if (!username || !password) {
    setLoginStatus("Username and password are required.");
    return;
  }

  if (isRegisterMode && !passwordConfirmation) {
    setLoginStatus("Password confirmation is required.");
    return;
  }

  if (isRegisterMode && password !== passwordConfirmation) {
    setLoginStatus("Password confirmation does not match.");
    return;
  }

  const loadingText = isRegisterMode ? "Registering..." : "Logging in...";
  setButtonLoading(loginButton, true, loadingText);
  setLoginStatus("");

  try {
    const auth = isRegisterMode
      ? await apiRegister(apiBase, username, password, passwordConfirmation)
      : await apiLogin(apiBase, username, password);
    authToken = auth.access_token;
    activeUsername = auth.username;
    localStorage.setItem("bookshelf_auth_token", authToken);
    localStorage.setItem("bookshelf_active_username", activeUsername);
    if (isRegisterMode) {
      setLoginStatus("Registration successful.");
    }
    showAppScreen();
    await refreshLibrary();
    clearBookForm();
    loginPasswordInput.value = "";
    loginPasswordConfirmInput.value = "";
  } catch (error) {
    const action = isRegisterMode ? "Registration" : "Login";
    setLoginStatus(`${action} failed: ${error.message}`);
  } finally {
    setButtonLoading(loginButton, false, loadingText);
  }
});

authModeToggle.addEventListener("click", () => {
  setAuthMode(!isRegisterMode);
  loginPasswordInput.value = "";
  loginPasswordConfirmInput.value = "";
  loginPasswordInput.focus();
});

logoutButton.addEventListener("click", () => {
  logout();
});

loadLibraryButton.addEventListener("click", async () => {
  try {
    await refreshLibrary();
  } catch (error) {
    if (String(error.message).includes("401")) {
      logout();
      setLoginStatus("Session expired. Please login again.");
      return;
    }
    setFormStatus(`Could not load library: ${error.message}`);
  }
});

openAddBookButton.addEventListener("click", () => {
  clearBookForm();
  bookModal.classList.remove("hidden");
});

closeAddBookButton.addEventListener("click", () => {
  bookModal.classList.add("hidden");
});

bookModal.addEventListener("click", (event) => {
  if (event.target === bookModal) {
    bookModal.classList.add("hidden");
  }
});

closeBookDetailButton.addEventListener("click", () => {
  bookDetailModal.classList.add("hidden");
});

bookDetailModal.addEventListener("click", (event) => {
  if (event.target === bookDetailModal) {
    bookDetailModal.classList.add("hidden");
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = uploadForm.querySelector('button[type="submit"]');
  setButtonLoading(submitButton, true, "Uploading...");
  setUploadStatus("Uploading file...");

  const selectedFile = ebookFileInput.files?.[0];
  if (!selectedFile) {
    setUploadStatus("Select a file first.");
    setButtonLoading(submitButton, false, "Uploading...");
    return;
  }

  try {
    uploadedFile = await apiUploadEbookFileWithProgress(apiBase, selectedFile, requireAuthToken(), (percent) => {
      setUploadStatus(`Uploading file... ${percent}%`);
    });
    setUploadStatus(`Uploaded: ${uploadedFile.storage_path}`);
    showUploadDetails(uploadedFile);
  } catch (error) {
    setUploadStatus(`Upload failed: ${error.message}`);
    showUploadDetails(null);
  } finally {
    setButtonLoading(submitButton, false, "Uploading...");
  }
});

metadataForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = metadataForm.querySelector('button[type="submit"]');
  setButtonLoading(submitButton, true, "Saving...");
  setFormStatus("Creating book...");

  const validationError = validateMetadataInputs();
  if (validationError) {
    setFormStatus(validationError);
    setButtonLoading(submitButton, false, "Saving...");
    return;
  }

  try {
    const categoryNames = parseCategoryNames(categoriesInput.value);

    const payload = {
      title: titleInput.value.trim(),
      author_name: authorInput.value.trim(),
      publisher_name: publisherInput.value || null,
      genre_names: [],
      description: descriptionInput.value || null,
      publishing_year: yearInput.value ? Number(yearInput.value) : null,
      series_name: seriesInput.value || null,
      series_position: seriesPositionInput.value ? Number(seriesPositionInput.value) : null,
      files: [
        {
          media_type: "ebook",
          file_format: uploadedFile.file_format,
          storage_path: uploadedFile.storage_path,
          file_size_bytes: uploadedFile.size_bytes,
          checksum_sha256: uploadedFile.checksum_sha256 || null,
        },
      ],
    };

    const created = await apiCreateEbook(apiBase, payload, requireAuthToken());

    for (const categoryName of categoryNames) {
      const category = await apiCreateCategory(apiBase, categoryName, requireAuthToken());
      await apiAttachCategoryToEbook(apiBase, created.id, category.id, requireAuthToken());
    }

    recordRecentCategoryNames(categoryNames);
    refreshCategoryAssistUi();

    setFormStatus("Book created successfully.");
    bookModal.classList.add("hidden");
    clearBookForm();
    await refreshLibrary();
  } catch (error) {
    setFormStatus(`Create failed: ${error.message}`);
  } finally {
    setButtonLoading(submitButton, false, "Saving...");
  }
});

clearFiltersButton.addEventListener("click", async () => {
  filterTitleInput.value = "";
  filterAuthorInput.value = "";
  filterCategoryInput.value = "";
  filterYearInput.value = "";
  sortByInput.value = "created_at";
  sortDirInput.value = "desc";
  pageSizeInput.value = "20";
  currentPage = 1;

  try {
    await refreshLibrary();
  } catch (error) {
    setFormStatus(`Could not load library: ${error.message}`);
  }
});

prevPageButton.addEventListener("click", async () => {
  if (currentPage <= 1) {
    return;
  }
  currentPage -= 1;
  try {
    await refreshLibrary();
  } catch (error) {
    setFormStatus(`Could not load library: ${error.message}`);
  }
});

nextPageButton.addEventListener("click", async () => {
  if (!paginationMeta.hasNext) {
    return;
  }
  currentPage += 1;
  try {
    await refreshLibrary();
  } catch (error) {
    setFormStatus(`Could not load library: ${error.message}`);
  }
});

for (const control of [
  filterTitleInput,
  filterAuthorInput,
  filterCategoryInput,
  filterYearInput,
  sortByInput,
  sortDirInput,
  pageSizeInput,
]) {
  control.addEventListener("change", () => {
    currentPage = 1;
  });
}

ebookFileInput.addEventListener("change", () => {
  if (!ebookFileInput.files?.[0]) {
    showUploadDetails(null);
    return;
  }
  setUploadStatus(`Selected file: ${ebookFileInput.files[0].name}. Click Upload File to continue.`);
  showUploadDetails(null);
});

categoriesInput.addEventListener("input", () => {
  renderQuickCategoryButtons();
});

clearCategoriesButton.addEventListener("click", () => {
  categoriesInput.value = "";
  renderQuickCategoryButtons();
});

refreshCategoryAssistUi();
setAuthMode(false);

ensureSession().then(async (active) => {
  if (!active) {
    return;
  }
  try {
    await refreshLibrary();
  } catch (error) {
    setFormStatus(`Could not load library: ${error.message}`);
  }
});
