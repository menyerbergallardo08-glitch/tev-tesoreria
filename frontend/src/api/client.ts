const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

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
    return localStorage.getItem('tev_token');
  },

  setToken(token: string) {
    localStorage.setItem('tev_token', token);
  },

  clearToken() {
    localStorage.removeItem('tev_token');
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
    // Support full /api/ prefix or relative to API_BASE
    const url = cleanEndpoint.startsWith('/api') 
      ? cleanEndpoint 
      : `${API_BASE}${cleanEndpoint}`;

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      window.dispatchEvent(new CustomEvent('tev:unauthorized'));
    }

    let data: any;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const message = data?.detail || data?.message || `Error ${response.status}: ${response.statusText}`;
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

  delete<T>(endpoint: string) {
    return this.request<T>(endpoint, { method: 'DELETE' });
  },
};
