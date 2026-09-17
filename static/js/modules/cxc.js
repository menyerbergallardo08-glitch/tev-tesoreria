import { ApiClient } from '../api/client.js';
import { showToast } from '../utils/toast.js';
import { parseDecimal } from '../utils/formatters.js';

export function createCxcController(store) {
    return {
        debts: [],
        isLoading: false,
        historicalForm: {
            client_name: '',
            client_rif: '',
            doc_type: 'NOTA_ENTREGA',
            doc_number: '',
            emission_date: new Date().toISOString().split('T')[0],
            amount_usd: '',
            notes: ''
        },
        paymentModal: {
            isOpen: false,
            debt: null,
            amount_usd: '',
            account_id: '',
            payment_method: 'PAGO_MOVIL',
            reference_number: '',
            description: ''
        },

        async loadDebts(status = 'ALL') {
            this.isLoading = true;
            try {
                this.debts = await ApiClient.get(`/api/cxc/debts?status=${status}`);
            } catch (err) {
                showToast(err.message || "Error cargando cuentas por cobrar.", "error");
            } finally {
                this.isLoading = false;
            }
        },

        async submitHistoricalDebt() {
            const amount = parseDecimal(this.historicalForm.amount_usd);
            if (amount <= 0 || !this.historicalForm.client_name.trim() || !this.historicalForm.doc_number.trim()) {
                showToast("Por favor complete los campos obligatorios del cliente y monto.", "warning");
                return;
            }

            try {
                await ApiClient.post('/api/cxc/historical-debt', {
                    client_name: this.historicalForm.client_name.trim(),
                    client_rif: this.historicalForm.client_rif.trim() || null,
                    doc_type: this.historicalForm.doc_type,
                    doc_number: this.historicalForm.doc_number.trim(),
                    emission_date: this.historicalForm.emission_date,
                    amount_usd: amount,
                    notes: this.historicalForm.notes || ''
                });
                showToast("Deuda histórica registrada exitosamente sin alterar ventas de hoy.", "success");
                this.historicalForm.doc_number = '';
                this.historicalForm.amount_usd = '';
                this.historicalForm.notes = '';
                await this.loadDebts();
            } catch (err) {
                showToast(err.message || "Error al registrar deuda histórica.", "error");
            }
        },

        openPaymentModal(debt) {
            this.paymentModal.debt = debt;
            this.paymentModal.amount_usd = debt.credit_balance_pending_usd;
            this.paymentModal.account_id = store.accounts[0]?.id || '';
            this.paymentModal.isOpen = true;
        },

        async submitPayment() {
            const amount = parseDecimal(this.paymentModal.amount_usd);
            if (amount <= 0 || !this.paymentModal.account_id) {
                showToast("Indique un monto y la cuenta donde se recibió el cobro.", "warning");
                return;
            }

            try {
                await ApiClient.post('/api/cxc/payments', {
                    transaction_id: this.paymentModal.debt.id,
                    amount_usd: amount,
                    account_id: parseInt(this.paymentModal.account_id),
                    payment_method: this.paymentModal.payment_method,
                    exchange_rate: store.bcvRate,
                    reference_number: this.paymentModal.reference_number || null,
                    description: this.paymentModal.description || ''
                });
                showToast("Cobro de CxC asentado exitosamente en caja/banco.", "success");
                this.paymentModal.isOpen = false;
                await this.loadDebts();
            } catch (err) {
                showToast(err.message || "Error al procesar el cobro.", "error");
            }
        }
    };
}
