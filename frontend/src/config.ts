/**
 * Configuración Institucional Centralizada (White-Label / Multi-Empresa)
 * Permite adaptar el sistema a cualquier empresa cliente modificando
 * únicamente variables de entorno VITE_*.
 */

export const APP_CONFIG = {
  companyName: import.meta.env.VITE_COMPANY_NAME || 'Todo Eléctrico Valencia, C.A.',
  companyShortName: import.meta.env.VITE_COMPANY_SHORT_NAME || 'TODO ELÉCTRICO VALENCIA',
  companyRif: import.meta.env.VITE_COMPANY_RIF || 'J-30798687-3',
  systemSlogan: import.meta.env.VITE_SYSTEM_SLOGAN || 'Tesorería, Gastos y Flujo de Caja',
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  primaryCurrency: import.meta.env.VITE_PRIMARY_CURRENCY || 'USD',
  secondaryCurrency: import.meta.env.VITE_SECONDARY_CURRENCY || 'VES',
  logoUrl: import.meta.env.VITE_LOGO_URL || '/logo.jpg',
};
