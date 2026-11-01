export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function fetchJSON(path, options) {
    const response = await fetch(`${API_URL}${path}`, options);
    const data = await response.json();
    if (!response.ok) {
        throw new Error(typeof data.detail === "string"
            ? data.detail : data.detail?.message || "Не удалось выполнить запрос");
    }
    return data;
}
