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
          this.abonoForm = {
            date: new Date().toISOString().split('T')[0],
            amount_original: credit.pending_balance_usd,
            currency: 'USD',
            account_id: this.accounts.length > 0 ? this.accounts[0].id : 1,
            reference_number: '',
            description: `Abono a ${credit.doc_type} #${credit.doc_number}`
          };
          this.showAbonoModal = true;
        },

        async submitAbono() {
          if (!this.selectedCreditObj) return;
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
