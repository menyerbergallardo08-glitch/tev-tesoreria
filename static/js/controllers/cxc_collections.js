// Modulo TEV: TEVCxcCollections
window.TEVCxcCollections = {
        async loadReceivables() {
          try {
            const token = this.getToken();
            const params = new URLSearchParams();
            if (this.cxcStatusFilter) params.append('status_filter', this.cxcStatusFilter);
            if (this.cxcSearch) params.append('search', this.cxcSearch);

            const res = await fetch(`/api/receivables?${params.toString()}`, {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.receivablesList = await res.json();
            }
          } catch (e) {
            console.error('Error loading receivables:', e);
          }
        },

        openAbonoModal(credit) {
          this.selectedCreditObj = credit;
          const validAccounts = (this.accounts || []).filter(a => a.is_active && a.account_type !== 'CXC' && a.account_type !== 'RETENCION_CLIENTE');
          const firstAcc = validAccounts.length > 0 ? validAccounts[0] : null;
          this.abonoForm = {
            date: new Date().toISOString().split('T')[0],
            amount_original: credit.pending_balance_usd,
            currency: 'USD',
            account_id: firstAcc ? firstAcc.id : 1,
            reference_number: '',
            description: `Abono a ${credit.doc_type} #${credit.doc_number}`,
            is_retention: false,
            tax_retention_proof: '',
            is_mixed: false,
            payments: [
              {
                account_id: firstAcc ? firstAcc.id : 1,
                amount_original: credit.pending_balance_usd,
                currency: firstAcc ? firstAcc.currency : 'USD',
                reference_number: ''
              }
            ]
          };
          this.showAbonoModal = true;
        },

        toggleAbonoMixed() {
          this.abonoForm.is_mixed = !this.abonoForm.is_mixed;
        },

        addAbonoPaymentLine() {
          const validAccounts = (this.accounts || []).filter(a => a.is_active && a.account_type !== 'CXC' && a.account_type !== 'RETENCION_CLIENTE');
          const firstAcc = validAccounts.length > 0 ? validAccounts[0] : null;
          this.abonoForm.payments.push({
            account_id: firstAcc ? firstAcc.id : 1,
            amount_original: 0,
            currency: firstAcc ? firstAcc.currency : 'USD',
            reference_number: ''
          });
        },

        removeAbonoPaymentLine(idx) {
          if (this.abonoForm.payments.length > 1) {
            this.abonoForm.payments.splice(idx, 1);
          }
        },

        onAbonoAccountChange(p) {
          const accObj = (this.accounts || []).find(a => a.id === p.account_id);
          if (accObj) {
            p.currency = accObj.currency;
          }
        },

        getAbonoMixedTotalUsd() {
          if (!this.abonoForm || !this.abonoForm.payments) return 0;
          const bcv = this.bcvRate || 881.0;
          return this.abonoForm.payments.reduce((acc, p) => {
            const accObj = (this.accounts || []).find(a => a.id === p.account_id);
            const curr = accObj ? accObj.currency : (p.currency || 'USD');
            const amt = parseFloat(p.amount_original || 0);
            if (curr === 'VES') {
              return acc + (amt / bcv);
            }
            return acc + amt;
          }, 0);
        },

        async submitAbono() {
          if (!this.selectedCreditObj) return;

          if (this.abonoForm.is_retention && (!this.abonoForm.tax_retention_proof || !this.abonoForm.tax_retention_proof.trim())) {
            this.showToast('error', 'Comprobante Requerido', 'Debe indicar el N° de comprobante de retención SENIAT.');
            return;
          }

          let payload = { ...this.abonoForm };
          let totalUsdToPay = this.abonoForm.amount_original;

          if (this.abonoForm.is_mixed && !this.abonoForm.is_retention) {
            totalUsdToPay = roundNumber(this.getAbonoMixedTotalUsd(), 2);
            if (totalUsdToPay <= 0) {
              this.showToast('error', 'Monto Inválido', 'Debe ingresar un monto válido en el pago mixto.');
              return;
            }
            if (totalUsdToPay > (this.selectedCreditObj.pending_balance_usd + 0.05)) {
              this.showToast('error', 'Monto Excedido', `El total mixto ($${totalUsdToPay}) no puede superar el saldo pendiente ($${this.selectedCreditObj.pending_balance_usd}).`);
              return;
            }
            payload.payments = this.abonoForm.payments;
          }

          const opType = this.abonoForm.is_retention ? 'Retención SENIAT de Cliente' : (this.abonoForm.is_mixed ? 'Cobro Mixto (Multipago)' : 'Pago / Cobro Líquido');
          const confMsg = `¿Confirma registrar este abono de CxC?\n\n• Operación: ${opType}\n• Cliente: ${this.selectedCreditObj.client_name}\n• Documento: ${this.selectedCreditObj.doc_type} #${this.selectedCreditObj.doc_number}\n• Monto: $${totalUsdToPay}` + (this.abonoForm.is_retention ? `\n• N° Comprobante SENIAT: ${this.abonoForm.tax_retention_proof}` : '');
          if (!confirm(confMsg)) return;

          try {
            const token = this.getToken();
            const res = await fetch(`/api/receivables/${this.selectedCreditObj.id}/abono`, {
              method: 'POST',
              headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(payload)
            });

            if (res.ok) {
              const d = await res.json();
              this.showToast('success', 'Abono Registrado', d.message);
              this.showAbonoModal = false;
              await this.loadReceivables();
              await this.loadInitialData();
            } else {
              const err = await res.json();
              this.showToast('error', 'Error', err.detail || 'No se pudo registrar el abono');
            }
          } catch (e) {
            this.showToast('error', 'Error', 'Error de conexión');
          }
        },

};
