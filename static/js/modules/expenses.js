import { ApiClient } from '../api/client.js';
import { showToast } from '../utils/toast.js';
import { parseDecimal } from '../utils/formatters.js';

export function createExpensesController(store) {
    return {
        isSubmitting: false,
        form: {
            date: new Date().toISOString().split('T')[0],
            category_id: '',
            account_id: '',
            amount_usd: '',
            currency: 'USD',
            exchange_rate: store.bcvRate,
            subtype: 'GASTO_OPERATIVO',
            beneficiary: '',
            reference_number: '',
            doc_number: '',
            description: '',
            tax_retention_amount: '',
            tax_retention_proof: ''
        },

        async submitExpense() {
            if (this.isSubmitting) return;

            const amount = parseDecimal(this.form.amount_usd);
            if (amount <= 0) {
                showToast("Ingrese un monto de egreso válido.", "warning");
                return;
            }
            if (!this.form.account_id) {
                showToast("Seleccione la cuenta bancaria o caja de origen del pago.", "warning");
                return;
            }
            if (!this.form.beneficiary.trim()) {
                showToast("Indique el beneficiario o proveedor del pago.", "warning");
                return;
            }

            this.isSubmitting = true;
            try {
                const payload = {
                    date: this.form.date,
                    category_id: parseInt(this.form.category_id),
                    account_id: parseInt(this.form.account_id),
                    amount_usd: amount,
                    currency: this.form.currency,
                    exchange_rate: parseDecimal(this.form.exchange_rate) || store.bcvRate,
                    subtype: this.form.subtype,
                    beneficiary: this.form.beneficiary.trim(),
                    reference_number: this.form.reference_number.trim() || null,
                    doc_number: this.form.doc_number.trim() || null,
                    description: this.form.description || '',
                    tax_retention_amount: parseDecimal(this.form.tax_retention_amount) || 0.0,
                    tax_retention_proof: this.form.tax_retention_proof.trim() || null
                };

                const res = await ApiClient.post('/api/expenses', payload);
                showToast(`Egreso registrado correctamente (ID #${res.id}).`, "success");
                this.resetForm();
            } catch (err) {
                showToast(err.message || "Error al registrar el egreso.", "error");
            } finally {
                this.isSubmitting = false;
            }
        },

        async addPostRetention(transactionId, amount, proof) {
            try {
                const res = await ApiClient.post(`/api/expenses/${transactionId}/retention`, {
                    tax_retention_amount: parseDecimal(amount),
                    tax_retention_proof: proof
                });
                showToast("Comprobante de retención SENIAT asociado exitosamente.", "success");
                return res;
            } catch (err) {
                showToast(err.message || "Error al asociar retención.", "error");
                throw err;
            }
        },

        resetForm() {
            this.form.amount_usd = '';
            this.form.beneficiary = '';
            this.form.reference_number = '';
            this.form.doc_number = '';
            this.form.description = '';
            this.form.tax_retention_amount = '';
            this.form.tax_retention_proof = '';
        }
    };
}
