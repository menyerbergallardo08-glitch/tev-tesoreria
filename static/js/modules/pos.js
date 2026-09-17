import { ApiClient } from '../api/client.js';
import { showToast } from '../utils/toast.js';
import { parseDecimal } from '../utils/formatters.js';
import { filterAccountsByOperation } from '../utils/bankRules.js';

export function createPosController(store) {
    return {
        isSubmitting: false,
        form: {
            date: new Date().toISOString().split('T')[0],
            doc_type: 'NOTA_ENTREGA',
            doc_number: '',
            client_name: '',
            client_rif: '',
            amount_usd: '',
            payment_method: 'EFECTIVO_USD',
            account_id: '',
            is_credit: false,
            abono_usd: '',
            abono_account_id: '',
            abono_payment_method: 'EFECTIVO_USD',
            pos_terminal: '',
            pos_lot_number: '',
            reference_number: '',
            description: ''
        },

        get filteredAccounts() {
            return filterAccountsByOperation(
                store.accounts,
                'SALE',
                this.form.doc_type,
                this.form.payment_method
            );
        },

        get filteredAbonoAccounts() {
            return filterAccountsByOperation(
                store.accounts,
                'SALE',
                this.form.doc_type,
                this.form.abono_payment_method
            );
        },

        async submitSale() {
            if (this.isSubmitting) return;

            const amount = parseDecimal(this.form.amount_usd);
            if (amount <= 0) {
                showToast("Por favor ingrese un monto de venta válido mayor a $0.00.", "warning");
                return;
            }

            if (!this.form.account_id && !this.form.is_credit) {
                showToast("Debe seleccionar la cuenta o caja donde ingresa el dinero.", "warning");
                return;
            }

            const abono = this.form.is_credit ? parseDecimal(this.form.abono_usd) : 0;
            if (this.form.is_credit && abono > amount) {
                showToast("El abono inicial no puede ser mayor que el monto total de la venta.", "warning");
                return;
            }

            if (this.form.is_credit && abono > 0 && !this.form.abono_account_id) {
                showToast("Debe seleccionar la cuenta donde se cobró el abono inicial.", "warning");
                return;
            }

            this.isSubmitting = true;
            try {
                const payload = {
                    date: this.form.date,
                    doc_type: this.form.doc_type,
                    doc_number: this.form.doc_number.trim(),
                    client_name: this.form.client_name.trim() || 'Cliente Mostrador',
                    client_rif: this.form.client_rif.trim() || null,
                    amount_usd: amount,
                    payment_method: this.form.payment_method,
                    account_id: parseInt(this.form.account_id) || parseInt(this.form.abono_account_id) || store.accounts[0]?.id,
                    exchange_rate: store.bcvRate,
                    is_credit: this.form.is_credit,
                    abono_usd: abono,
                    abono_account_id: this.form.abono_account_id ? parseInt(this.form.abono_account_id) : null,
                    abono_payment_method: this.form.abono_payment_method,
                    pos_terminal: this.form.pos_terminal || null,
                    pos_lot_number: this.form.pos_lot_number || null,
                    reference_number: this.form.reference_number || null,
                    description: this.form.description || ''
                };

                const res = await ApiClient.post('/api/sales', payload);
                showToast(`¡Venta registrada con éxito! Comprobante #${res.id}`, "success");
                this.resetForm();
            } catch (err) {
                showToast(err.message || "Error al procesar la venta.", "error");
            } finally {
                this.isSubmitting = false;
            }
        },

        resetForm() {
            this.form.doc_number = '';
            this.form.client_name = '';
            this.form.client_rif = '';
            this.form.amount_usd = '';
            this.form.is_credit = false;
            this.form.abono_usd = '';
            this.form.abono_account_id = '';
            this.form.reference_number = '';
            this.form.pos_lot_number = '';
            this.form.description = '';
        }
    };
}
