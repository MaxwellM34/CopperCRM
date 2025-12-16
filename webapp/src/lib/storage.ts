const key = (name: string) => `copper:${name}`;

const defaultCloudApi =
  process.env.NEXT_PUBLIC_API_BASE ||
  "https://crm-api-468831678336.us-central1.run.app";

function runtimeDefaultApi() {
  if (typeof window === "undefined") return defaultCloudApi;
  const host = window.location.hostname;
  const isLocal = host === "localhost" || host === "127.0.0.1";
  return isLocal ? "http://127.0.0.1:8000" : defaultCloudApi;
}

const hasStorage = typeof window !== "undefined" && typeof window.localStorage !== "undefined";

export const storage = {
  getApiBaseUrl() {
    if (hasStorage) {
      return localStorage.getItem(key("apiBaseUrl")) || runtimeDefaultApi();
    }
    return runtimeDefaultApi();
  },
  setApiBaseUrl(url: string) {
    if (hasStorage) {
      localStorage.setItem(key("apiBaseUrl"), url);
    }
  },
  getToken() {
    if (hasStorage) {
      return localStorage.getItem(key("token")) || "";
    }
    return "";
  },
  setToken(token: string) {
    if (hasStorage) {
      localStorage.setItem(key("token"), token);
    }
  },
  clearToken() {
    if (hasStorage) {
      localStorage.removeItem(key("token"));
    }
  },
};
