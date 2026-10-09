// Orquestador Maestro Modular TEV Tesoreria
// Fusiona los controladores especializados en el ambito de Alpine.js
function roundNumber(num, dec) { 
  return Math.round(num * Math.pow(10, dec)) / Math.pow(10, dec); 
}

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
