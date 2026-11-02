export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

let csrfToken;

export async function fetchJSON(path, options = {}) {
    if (options.method && !["GET", "HEAD"].includes(options.method.toUpperCase()) && !csrfToken) {
        const session = await fetchJSON("/auth/session");
        csrfToken = session.csrf_token;
    }
    const response = await fetch(`${API_URL}${path}`, {
        ...options, credentials: "include",
        headers: { ...options.headers, ...(options.method && csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
    });
    const data = await response.json();
    if (response.status === 403) csrfToken = null;
    if (!response.ok) {
        throw new Error(typeof data.detail === "string"
            ? data.detail : data.detail?.message || "Не удалось выполнить запрос");
    }
    if (data.csrf_token) csrfToken = data.csrf_token;
    if (path === "/auth/logout" || path === "/auth/password" || path === "/auth/reset-password" || response.status === 403) csrfToken = null;
    return data;
}
