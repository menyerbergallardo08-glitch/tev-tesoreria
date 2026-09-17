import { ApiClient } from './api/client.js';
import { Store } from './state/store.js';
import { showToast } from './utils/toast.js';
import { formatUSD, formatVES } from './utils/formatters.js';
import { createPosController } from './modules/pos.js';
import { createExpensesController } from './modules/expenses.js';
import { createCxcController } from './modules/cxc.js';
import { createAccountsController } from './modules/accounts.js';

window.TEVApp = {
    ApiClient,
    Store,
    showToast,
    formatUSD,
    formatVES,
    createPosController,
    createExpensesController,
    createCxcController,
    createAccountsController
};

console.log("[TEV] Arquitectura Modular ES6 Inicializada con Éxito.");
