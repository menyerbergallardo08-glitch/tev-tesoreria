// Orquestador Maestro Modular TEV Tesoreria
// Fusiona los controladores especializados en el ambito de Alpine.js
function roundNumber(num, dec) { 
  return Math.round(num * Math.pow(10, dec)) / Math.pow(10, dec); 
}

function formatDate(val) {
  if (!val) return '';
  const str = String(val).trim();
  const m = str.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) {
    return `${m[3]}/${m[2]}/${m[1]}`;
  }
  if (/^\d{2}\/\d{2}\/\d{4}/.test(str)) {
    return str;
  }
  const d = new Date(str);
  if (isNaN(d.getTime())) return str;
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
}
window.formatDate = formatDate;

function app() {
  return {
    ...(window.TEVState || {}),
    ...(window.TEVAuthCore || {}),
    ...(window.TEVPosSales || {}),
    ...(window.TEVCxcCollections || {}),
    ...(window.TEVCashClose || {}),
    ...(window.TEVExpenses || {}),
    ...(window.TEVReports || {})
  };
}

console.log('[TEV] Arquitectura Frontend Modular (<600 lineas) lista y operativa.');
