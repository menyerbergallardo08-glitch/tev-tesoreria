const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export const api = {
  getToken(): string | null {
    return localStorage.getItem('tev_token') || sessionStorage.getItem('tev_token');
  },

  setToken(token: string) {
    localStorage.setItem('tev_token', token);
    sessionStorage.setItem('tev_token', token);
  },

  clearToken() {
    localStorage.removeItem('tev_token');
    sessionStorage.removeItem('tev_token');
  },

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    
    // Inject Bearer token
    const token = this.getToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    // Default to JSON Content-Type if body is present and not FormData
    if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    let url: string;
    if (API_BASE) {
      if (API_BASE.endsWith('/api') && cleanEndpoint.startsWith('/api')) {
        url = `${API_BASE}${cleanEndpoint.slice(4)}`;
      } else {
        url = `${API_BASE}${cleanEndpoint}`;
      }
    } else {
      url = cleanEndpoint;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      window.dispatchEvent(new CustomEvent('tev:unauthorized'));
    }

    let data: any;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const rawText = await response.text();
      if (!response.ok) {
        throw new ApiError(`Error ${response.status}: ${rawText.slice(0, 150)}`, response.status, rawText);
      }
      throw new ApiError(
        `El servidor devolvió una respuesta inesperada (${contentType || 'texto/HTML'}).`,
        response.status,
        rawText
      );
    }

    if (!response.ok) {
      let message = `Error ${response.status}: ${response.statusText}`;
      if (typeof data?.detail === 'string') {
        message = data.detail;
      } else if (Array.isArray(data?.detail)) {
        message = data.detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join('; ');
      } else if (typeof data?.message === 'string') {
        message = data.message;
      } else if (data?.detail && typeof data.detail === 'object') {
        message = JSON.stringify(data.detail);
      }
      throw new ApiError(message, response.status, data);
    }

    return data as T;
  },

  get<T>(endpoint: string) {
    return this.request<T>(endpoint, { method: 'GET' });
  },

  post<T>(endpoint: string, body?: any) {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  put<T>(endpoint: string, body?: any) {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(endpoint: string, body?: any) {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  delete<T>(endpoint: string) {
    return this.request<T>(endpoint, { method: 'DELETE' });
  },
};
