/**
 * TEV Tesorería - Cliente HTTP Centralizado (ES6)
 * Inyección automática de Bearer Token JWT y captura de 401 Unauthorized
 */
export class ApiClient {
    static getToken() {
        return localStorage.getItem('tev_token') || sessionStorage.getItem('tev_token');
    }

    static setToken(token, persist = true) {
        if (persist) {
            localStorage.setItem('tev_token', token);
        } else {
            sessionStorage.setItem('tev_token', token);
        }
    }

    static clearToken() {
        localStorage.removeItem('tev_token');
        sessionStorage.removeItem('tev_token');
        localStorage.removeItem('tev_user');
    }

    static async request(endpoint, options = {}) {
        const token = this.getToken();
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(options.headers || {})
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(endpoint, config);

            if (response.status === 401) {
                this.clearToken();
                window.location.reload();
                throw new Error("Sesión expirada o no autorizada. Redirigiendo al login...");
            }

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const errorMsg = data.detail || `Error HTTP ${response.status}: ${response.statusText}`;
                throw new Error(errorMsg);
            }

            return data;
        } catch (err) {
            console.error(`[API ERROR] ${endpoint}:`, err);
            throw err;
        }
    }

    static get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    static post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }

    static put(endpoint, body) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
    }

    static delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}
