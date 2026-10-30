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
          this.abonoForm = {
            date: new Date().toISOString().split('T')[0],
            amount_original: credit.pending_balance_usd,
            currency: 'USD',
            account_id: validAccounts.length > 0 ? validAccounts[0].id : 1,
            reference_number: '',
            description: `Abono a ${credit.doc_type} #${credit.doc_number}`,
            is_retention: false,
            tax_retention_proof: ''
          };
          this.showAbonoModal = true;
        },

        async submitAbono() {
          if (!this.selectedCreditObj) return;

          if (this.abonoForm.is_retention && (!this.abonoForm.tax_retention_proof || !this.abonoForm.tax_retention_proof.trim())) {
            this.showToast('error', 'Comprobante Requerido', 'Debe indicar el N° de comprobante de retención SENIAT.');
            return;
          }

          const opType = this.abonoForm.is_retention ? 'Retención SENIAT de Cliente' : 'Pago / Cobro Líquido';
          const confMsg = `¿Confirma registrar este abono de CxC?\n\n• Operación: ${opType}\n• Cliente: ${this.selectedCreditObj.client_name}\n• Documento: ${this.selectedCreditObj.doc_type} #${this.selectedCreditObj.doc_number}\n• Monto: $${this.abonoForm.amount_original}` + (this.abonoForm.is_retention ? `\n• N° Comprobante SENIAT: ${this.abonoForm.tax_retention_proof}` : '');
          if (!confirm(confMsg)) return;

          try {
            const token = this.getToken();
            const res = await fetch(`/api/receivables/${this.selectedCreditObj.id}/abono`, {
              method: 'POST',
              headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(this.abonoForm)
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
