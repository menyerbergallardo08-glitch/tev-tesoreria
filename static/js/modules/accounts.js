import { ApiClient } from '../api/client.js';
import { showToast } from '../utils/toast.js';
import { parseDecimal } from '../utils/formatters.js';

export function createAccountsController(store) {
    return {
        newAccount: {
            name: '',
            currency: 'VES',
            account_type: 'BANCO',
            initial_balance: 0.0,
            only_income: false
        },

        async loadAllAccounts() {
            try {
                store.accounts = await ApiClient.get('/api/accounts?all=true');
            } catch (err) {
                showToast(err.message || "Error al cargar las cuentas.", "error");
            }
        },

        async createAccount() {
            if (!this.newAccount.name.trim()) {
                showToast("Debe ingresar un nombre para la cuenta.", "warning");
                return;
            }
            try {
                await ApiClient.post('/api/accounts', {
                    name: this.newAccount.name.trim(),
                    currency: this.newAccount.currency,
                    account_type: this.newAccount.account_type,
                    initial_balance: parseDecimal(this.newAccount.initial_balance),
                    only_income: this.newAccount.only_income
                });
                showToast("Cuenta / Caja creada exitosamente.", "success");
                this.newAccount.name = '';
                this.newAccount.initial_balance = 0.0;
                await this.loadAllAccounts();
            } catch (err) {
                showToast(err.message || "Error al crear la cuenta.", "error");
            }
        },

        async toggleStatus(account) {
            try {
                const res = await ApiClient.post(`/api/accounts/${account.id}/toggle-status`, {});
                showToast(res.message, "success");
                await this.loadAllAccounts();
            } catch (err) {
                showToast(err.message || "Error al cambiar el estado de la cuenta.", "error");
            }
        }
    };
}
