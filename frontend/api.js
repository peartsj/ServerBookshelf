const defaultBase = "http://localhost:4408";

export function getDefaultApiBase() {
  const fromEnv = globalThis.__APP_CONFIG__?.API_BASE_URL;
  if (fromEnv && typeof fromEnv === "string") {
    return fromEnv;
  }
  return defaultBase;
}

function buildUrl(baseUrl, path, params = {}) {
  const url = new URL(path, baseUrl || getDefaultApiBase());
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url;
}

function buildAuthHeaders(authToken, includeJson = false) {
  const headers = {};
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function parseApiError(response) {
  let message = `Request failed (${response.status})`;
  try {
    const payload = await response.json();
    if (payload && payload.detail) {
      message = payload.detail;
    }
  } catch (_) {
    // Keep default fallback if the response body is not JSON.
  }
  throw new Error(message);
}

function parseContentDispositionFilename(headerValue) {
  if (!headerValue) {
    return null;
  }

  const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim());
    } catch (_) {
      return utf8Match[1].trim();
    }
  }

  const quotedMatch = headerValue.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1].trim();
  }

  const plainMatch = headerValue.match(/filename=([^;]+)/i);
  if (plainMatch?.[1]) {
    return plainMatch[1].trim();
  }

  return null;
}

export async function apiUploadEbookFile(baseUrl, file, authToken) {
  return apiUploadEbookFileWithProgress(baseUrl, file, authToken);
}

export function apiUploadEbookFileWithProgress(baseUrl, file, authToken, onProgress) {
  const url = buildUrl(baseUrl, "/uploads/ebook-file");
  const formData = new FormData();
  formData.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url.toString());
    if (authToken) {
      xhr.setRequestHeader("Authorization", `Bearer ${authToken}`);
    }

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onerror = () => reject(new Error("Upload request failed"));
    xhr.onload = () => {
      let payload = null;
      try {
        payload = JSON.parse(xhr.responseText || "{}");
      } catch (_) {
        payload = null;
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload);
        return;
      }

      const message = payload?.detail || `Request failed (${xhr.status})`;
      reject(new Error(message));
    };

    xhr.send(formData);
  });
}

export async function apiCreateEbook(baseUrl, payload, authToken) {
  const response = await fetch(buildUrl(baseUrl, "/ebooks"), {
    method: "POST",
    headers: buildAuthHeaders(authToken, true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    await parseApiError(response);
  }
  return response.json();
}

export async function apiListEbooks(baseUrl, filters = {}, authToken = null) {
  const response = await fetch(buildUrl(baseUrl, "/ebooks", filters), {
    headers: buildAuthHeaders(authToken),
  });
  if (!response.ok) {
    await parseApiError(response);
  }
  return response.json();
}

export async function apiUpdateEbook(baseUrl, ebookId, payload, authToken) {
  const response = await fetch(buildUrl(baseUrl, `/ebooks/${ebookId}`), {
    method: "PATCH",
    headers: buildAuthHeaders(authToken, true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    await parseApiError(response);
  }
  return response.json();
}

export async function apiDeleteEbook(baseUrl, ebookId, authToken) {
  const response = await fetch(buildUrl(baseUrl, `/ebooks/${ebookId}`), {
    method: "DELETE",
    headers: buildAuthHeaders(authToken),
  });

  if (!response.ok) {
    await parseApiError(response);
  }
}

export async function apiCreateCategory(baseUrl, name, authToken) {
  const response = await fetch(buildUrl(baseUrl, "/categories"), {
    method: "POST",
    headers: buildAuthHeaders(authToken, true),
    body: JSON.stringify({ name }),
  });

  if (!response.ok) {
    await parseApiError(response);
  }
  return response.json();
}

export async function apiListCategories(baseUrl, authToken) {
  const response = await fetch(buildUrl(baseUrl, "/categories"), {
    headers: buildAuthHeaders(authToken),
  });

  if (!response.ok) {
    await parseApiError(response);
  }
  return response.json();
}

export async function apiAttachCategoryToEbook(baseUrl, ebookId, categoryId, authToken) {
  const response = await fetch(buildUrl(baseUrl, `/ebooks/${ebookId}/categories/${categoryId}`), {
    method: "POST",
    headers: buildAuthHeaders(authToken),
  });

  if (!response.ok) {
    await parseApiError(response);
  }
}

export async function apiDetachCategoryFromEbook(baseUrl, ebookId, categoryId, authToken) {
  const response = await fetch(buildUrl(baseUrl, `/ebooks/${ebookId}/categories/${categoryId}`), {
    method: "DELETE",
    headers: buildAuthHeaders(authToken),
  });

  if (!response.ok) {
    await parseApiError(response);
  }
}

export async function apiLogin(baseUrl, username, password) {
  const response = await fetch(buildUrl(baseUrl, "/auth/login"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    await parseApiError(response);
  }

  return response.json();
}

export async function apiRegister(baseUrl, username, password, passwordConfirmation) {
  const response = await fetch(buildUrl(baseUrl, "/auth/register"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      password,
      password_confirmation: passwordConfirmation,
    }),
  });

  if (!response.ok) {
    await parseApiError(response);
  }

  return response.json();
}

export async function apiMe(baseUrl, authToken) {
  const response = await fetch(buildUrl(baseUrl, "/auth/me"), {
    headers: buildAuthHeaders(authToken),
  });

  if (!response.ok) {
    await parseApiError(response);
  }

  return response.json();
}

export async function apiGetEbookCover(baseUrl, ebookId, authToken) {
  const response = await fetch(buildUrl(baseUrl, `/ebooks/${ebookId}/cover`), {
    headers: buildAuthHeaders(authToken),
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    await parseApiError(response);
  }

  return response.blob();
}

export async function apiDownloadEbook(baseUrl, ebookId, authToken) {
  const response = await fetch(buildUrl(baseUrl, `/ebooks/${ebookId}/download`), {
    headers: buildAuthHeaders(authToken),
  });

  if (!response.ok) {
    await parseApiError(response);
  }

  const blob = await response.blob();
  const filename = parseContentDispositionFilename(response.headers.get("content-disposition"));
  return { blob, filename };
}
