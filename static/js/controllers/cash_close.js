// Modulo TEV: TEVCashClose
window.TEVCashClose = {
        isAccountPOS() {
          const acc = this.accounts.find(a => a.id === this.form.account_id);
          if (!acc) return false;
          const name = acc.name.toUpperCase();
          return name.includes('BANCO') || name.includes('PUNTO') || name.includes('POS') || name.includes('BANESCO') || name.includes('BANCARIBE') || name.includes('VENEZUELA');
        },

        async loadCashCloseSummary() {
          try {
            const token = this.getToken();
            const res = await fetch(`/api/cash-close/summary?date=${this.cuadreDate}`, {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.cashCloseSummary = await res.json();
              if (this.cashCloseSummary.existing_close) {
                this.cuadreNotes = this.cashCloseSummary.existing_close.notes || '';
              }
            }
            await this.loadCashCloseHistory();
          } catch (e) {
            console.error('Error loading cash close summary:', e);
          }
        },

        async loadCashCloseHistory() {
          try {
            const token = this.getToken();
            const res = await fetch('/api/cash-close/history', {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.cashCloseHistory = await res.json();
            }
          } catch (e) {
            console.error('Error loading cash close history:', e);
          }
        },

        calculateCuadreDifference() {
          if (!this.cashCloseSummary) return 0;
          const netSales = this.cashCloseSummary.sales_summary?.net_sales_usd || 0;
          const collected = this.cashCloseSummary.collections_summary?.total_collected_real_usd || 0;
          return roundNumber(collected - netSales, 2);
        },

        async executeSaveDailyCashClose() {
          if (!this.cashCloseSummary) return;
          try {
            const token = this.getToken();
            const payload = {
              date: this.cuadreDate,
              cajero_name: this.currentUser?.full_name || 'Cajero',
              verified_by: 'Administración',
              status: this.calculateCuadreDifference() === 0 ? 'CUADRADO' : (this.calculateCuadreDifference() > 0 ? 'SOBRANTE' : 'FALTANTE'),
              profit_sales_total_usd: this.cashCloseSummary.sales_summary?.net_sales_usd || 0,
              sales_fiscal_iva_usd: this.cashCloseSummary.sales_summary?.fiscal_iva_usd || 0,
              sales_notes_credit_usd: this.cashCloseSummary.sales_summary?.notes_credit_usd || 0,
              sales_notes_collected_usd: this.cashCloseSummary.sales_summary?.notes_collected_usd || 0,
              returns_total_usd: this.cashCloseSummary.sales_summary?.returns_total_usd || 0,
              net_sales_usd: this.cashCloseSummary.sales_summary?.net_sales_usd || 0,
              cash_usd_physical: this.cashCloseSummary.collections_summary?.cash_usd_net || 0,
              cash_ves_physical: this.cashCloseSummary.collections_summary?.cash_ves_net || 0,
              pos_total_usd: this.cashCloseSummary.collections_summary?.pos_total_usd || 0,
              bank_transfers_usd: this.cashCloseSummary.collections_summary?.bank_transfers_usd || 0,
              cashea_usd: this.cashCloseSummary.collections_summary?.cashea_usd || 0,
              retentions_iva_usd: this.cashCloseSummary.collections_summary?.retentions_iva_usd || 0,
              retentions_islr_usd: this.cashCloseSummary.collections_summary?.retentions_islr_usd || 0,
              expenses_caja_usd: this.cashCloseSummary.collections_summary?.expenses_caja_usd || 0,
              total_collected_real_usd: this.cashCloseSummary.collections_summary?.total_collected_real_usd || 0,
              total_expected_usd: this.cashCloseSummary.sales_summary?.net_sales_usd || 0,
              difference_usd: this.calculateCuadreDifference(),
              notes: this.cuadreNotes
            };

            const res = await fetch('/api/cash-close', {
              method: 'POST',
              headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(payload)
            });

            if (res.ok) {
              const d = await res.json();
              this.showToast('success', 'Cuadre Guardado', d.message);
              await this.loadCashCloseSummary();
            } else {
              const err = await res.json();
              this.showToast('error', 'Error', err.detail || 'No se pudo guardar el cuadre');
            }
          } catch (e) {
            this.showToast('error', 'Error', 'Error de conexión');
          }
        },

        openCashCloseReceipt() {
          this.showCashCloseReceiptModal = true;
        },

        async loadSalesAccumulated() {
          try {
            const token = this.getToken();
            let url = `/api/sales/accumulated?filter_mode=${this.salesFilterMode}`;
            if (this.salesFilterMode === 'dia') {
              url += `&date=${this.salesFilterDate}`;
            } else {
              url += `&month=${this.filterMonth}`;
            }
            const res = await fetch(url, {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.salesAccumulatedData = await res.json();
            }
          } catch (e) {
            console.error('Error loading accumulated sales:', e);
          }
        },

        
        liveSyncInterval: null,

        
        saveSaleDraft() {
          try {
            localStorage.setItem('tev_draft_sale', JSON.stringify(this.liveSaleForm));
          } catch (e) {}
        },

        restoreSaleDraft() {
          try {
            const raw = localStorage.getItem('tev_draft_sale');
            if (raw) {
              const d = JSON.parse(raw);
              if (d && (d.doc_number || d.client_name || d.amount_original)) {
                this.liveSaleForm = Object.assign(this.liveSaleForm, d);
                this.showToast('info', 'Borrador Recuperado', 'Se restauraron los datos que estabas ingresando.');
              }
            }
          } catch (e) {}
        },

        clearSaleDraft() {
          try {
            localStorage.removeItem('tev_draft_sale');
          } catch (e) {}
        },


        calculatePhysicalVes() {
          return (
            (this.arqueoVES.b500 || 0) * 500 +
            (this.arqueoVES.b200 || 0) * 200 +
            (this.arqueoVES.b100 || 0) * 100 +
            (this.arqueoVES.b50 || 0) * 50 +
            (this.arqueoVES.b20 || 0) * 20 +
            (this.arqueoVES.b10 || 0) * 10
          );
        },

        calculateVesEquivalent() {
          const amt = parseFloat(this.form.amount_original) || 0;
          const rate = parseFloat(this.form.exchange_rate || this.bcvRate) || 827.74;
          return this.formatNumber(amt * rate);
        },

        checkDuplicateReference() {
          if (!this.form.reference_number || this.form.reference_number.trim().length < 3 || this.form.subtype === 'VENTA_DIARIA') {
            this.duplicateWarning = false;
            this.duplicateWarningMessage = '';
            return;
          }
          const ref = this.form.reference_number.trim().toLowerCase();
          const match = this.transactions.find(t => t.reference_number && t.reference_number.trim().toLowerCase() === ref && t.status !== 'ANULADO');
          if (match) {
            this.duplicateWarning = true;
            this.duplicateWarningMessage = 'La referencia "' + match.reference_number + '" ya fue registrada el ' + match.date + ' por $' + this.formatNumber(match.amount_usd) + ' (' + (match.beneficiary || match.subtype) + '). ¡Verifique antes de pagar!';
          } else {
            this.duplicateWarning = false;
            this.duplicateWarningMessage = '';
          }
        },

        calculatePhysicalUsd() {
          return (this.arqueo.b100 * 100) +
                 (this.arqueo.b50 * 50) +
                 (this.arqueo.b20 * 20) +
                 (this.arqueo.b10 * 10) +
                 (this.arqueo.b5 * 5) +
                 (this.arqueo.b1 * 1);
        },

        resetArqueo() {
          if (this.arqueoCurrency === 'USD') {
            this.arqueo = { b100: 0, b50: 0, b20: 0, b10: 0, b5: 0, b1: 0 };
          } else {
            this.arqueoVES = { b500: 0, b200: 0, b100: 0, b50: 0, b20: 0, b10: 0 };
          }
        },

        

        openArqueoReceiptModal() {
          this.showArqueoReceiptModal = true;
        },

        executePrintReceipt() {
          window.print();
        },

        async openOnePageReport() {
          this.showOnePageModal = true;
          this.onePageMode = 'mensual';
          if (!this.onePageDate) {
            this.onePageDate = new Date().toISOString().split('T')[0];
          }
          await this.loadDailyOnePage();
        },

        async loadDailyOnePage() {
          try {
            const token = this.getToken();
            const res = await fetch('/api/dashboard/daily-closing?date=' + this.onePageDate, {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.dailyOnePageData = await res.json();
            }
          } catch(e) { console.error(e); }
        },

        printArqueo() {
          this.showArqueoReceiptModal = true;
        },


};
