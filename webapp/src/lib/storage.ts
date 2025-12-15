const key = (name: string) => `copper:${name}`;

export const storage = {
  getApiBaseUrl() {
    return (
      localStorage.getItem(key("apiBaseUrl")) ||
      process.env.NEXT_PUBLIC_API_BASE ||
      "http://127.0.0.1:8000"
    );
  },
  setApiBaseUrl(url: string) {
    localStorage.setItem(key("apiBaseUrl"), url);
  },
  getToken() {
    return localStorage.getItem(key("token")) || "";
  },
  setToken(token: string) {
    localStorage.setItem(key("token"), token);
  },
  clearToken() {
    localStorage.removeItem(key("token"));
  },
};
