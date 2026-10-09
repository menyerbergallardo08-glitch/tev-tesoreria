// Modulo TEV: TEVReports
window.TEVReports = {
        async autoSyncBcvRate() {
          this.loadingBcv = true;
          try {
            const token = this.getToken();
            const headers = token ? { 'Authorization': 'Bearer ' + token } : {};
            const res = await fetch('/api/bcv-rate/sync', { headers });
            if (res.ok) {
              const data = await res.json();
              if (data && data.rate) {
                this.bcvRate = parseFloat(data.rate);
                this.newBcvRate = parseFloat(data.rate);
                if (this.form) this.form.exchange_rate = parseFloat(data.rate);
                if (this.transferForm) this.transferForm.exchange_rate = parseFloat(data.rate);
                this.showToast('success', 'Tasa BCV Sincronizada', `Bs. ${parseFloat(data.rate).toFixed(2)} (${data.policy || 'Oficial'})`);
              }
            }
          } catch (e) {
            console.error('Error in autoSyncBcvRate:', e);
          } finally {
            this.loadingBcv = false;
          }
        },

        startLiveSync() {
          if (this.liveSyncInterval) clearInterval(this.liveSyncInterval);
          this.liveSyncInterval = setInterval(async () => {
            if (this.currentUser) {
              if (this.activeTab === 'live_monitor') {
                await this.loadLiveMonitor();
              } else if (this.activeTab === 'cuadre') {
                await this.loadCashCloseSummary();
              } else if (this.activeTab === 'cxc') {
                await this.loadReceivables();
              }
            }
          }, 12000);
        },
        formatSubtype(st) {
          const map = {
            'GASTO_OPERATIVO': '💸 Gasto Operativo',
            'PAGO_PROVEEDOR': '📦 Pago a Proveedor',
            'VENTA_DIARIA': '💰 Cierre Venta Diaria',
            'COBRO_CXC': '📥 Cobro CxC',
            'TRASPASO_SALIDA': '🔄 Salida por Traspaso',
            'TRASPASO_ENTRADA': '🔄 Entrada por Traspaso'
          };
          return map[st] || st;
        },

        getRoleLabel(role) {
          const map = {
            'cajera': 'Cajera / Asistente',
            'administradora': 'Administradora',
            'directivo': 'Dirección General'
          };
          return map[role] || role;
        },

        calculateUsdEquivalent() {
          const amt = parseFloat(this.form.amount_original) || 0;
          if (this.selectedAccountCurrency === 'VES') {
            const rate = parseFloat(this.form.exchange_rate) || 1;
            return amt / rate;
          }
          return amt;
        },

        isRateWarning() {
          if (this.selectedAccountCurrency !== 'VES') return false;
          const rate = parseFloat(this.form.exchange_rate) || 0;
          return rate > 0 && (rate < 500 || rate > 1500);
        },

        getSelectedAccountName() {
          const a = this.accounts.find(x => x.id === this.form.account_id);
          return a ? `${a.name} (${a.currency})` : '';
        },

        openBcvRateModal() {
          this.newBcvRate = this.bcvRate;
          this.showBcvRateModal = true;
          this.fetchBcvRateLive(false);
        },

        async autoSyncBcvRate() {
          await this.fetchBcvRateLive(true);
        },

        async fetchBcvRateLive(sync = false) {
          this.loadingBcv = true;
          try {
            const token = this.getToken();
            const res = await fetch('/api/system/bcv-rate', {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              const data = await res.json();
              if (data.rate && data.rate > 0) {
                this.bcvRate = data.rate;
                this.newBcvRate = data.rate;
                if (this.selectedAccountCurrency === 'VES' && this.form.subtype !== 'CAMBIO_DIVISAS') {
                  this.form.exchange_rate = this.bcvRate;
                }
                if (sync) {
                  this.showToast('success', 'Tasa Sincronizada', 'Tasa BCV del día: Bs. ' + this.formatNumber(this.bcvRate));
                }
              }
            }
          } catch(e) {
            console.error(e);
          } finally {
            this.loadingBcv = false;
          }
        },

        async loadBcvRate() {
          await this.fetchBcvRateLive(false);
        },

        async submitManualBcvRate() {
          await this.updateBcvRate();
        },

        async updateBcvRate() {
          if (!this.newBcvRate || this.newBcvRate <= 0) {
            alert('Por favor ingrese una tasa válida.');
            return;
          }
          const token = this.getToken();
          const res = await fetch('/api/system/bcv-rate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ rate: parseFloat(this.newBcvRate) })
          });
          if (res.ok) {
            this.bcvRate = parseFloat(this.newBcvRate);
            if (this.selectedAccountCurrency === 'VES' && this.form.subtype !== 'CAMBIO_DIVISAS') {
              this.form.exchange_rate = this.bcvRate;
            }
            this.showBcvRateModal = false;
            this.showToast('success', 'Tasa Oficial Actualizada', 'La tasa BCV del día se fijó en Bs. ' + this.formatNumber(this.bcvRate));
          } else {
            const err = await res.json().catch(() => ({}));
            alert(err.detail || 'Error al actualizar tasa');
          }
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

        calculateTotalBudget() {
          return this.categories.reduce((acc, c) => acc + (c.monthly_budget_usd || 0), 0);
        },

        calculateTotalSpent() {
          return this.categories.reduce((acc, c) => acc + (c.spent_usd || 0), 0);
        },

        calculateTotalRemaining() {
          return this.calculateTotalBudget() - this.calculateTotalSpent();
        },

        calculateTotalPercentage() {
          const b = this.calculateTotalBudget();
          if (b <= 0) return '0.0';
          return ((this.calculateTotalSpent() / b) * 100).toFixed(1);
        },

        formatNumber(val) {
          if (val === undefined || val === null) return '0,00';
          return parseFloat(val).toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        },

        async resetSystemDemo() {
          const pass1 = confirm("⚠️ ATENCIÓN: RESETEO DE PRUEBAS A CERO ⚠️\n\n¿Está seguro de que desea reiniciar la herramienta?\n\n- Se ELIMINARÁN todos los movimientos y gastos de prueba.\n- Los saldos iniciales de todas las cajas volverán a 0.00.\n- Los usuarios, partidas y cuentas se conservarán intactos.");
          if (!pass1) return;

          const pass2 = prompt("🔒 CONFIRMACIÓN DE SEGURIDAD (DIRECCIÓN):\nEscriba la palabra 'RESETEAR' para confirmar la limpieza:");
          if (pass2 !== 'RESETEAR') {
            this.showToast('warning', 'Operación Cancelada', 'No se realizaron cambios en la base de datos.');
            return;
          }

          const token = this.getToken();
          try {
            const res = await fetch('/api/admin/reset-system-demo', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + token }
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al resetear');

            this.showToast('success', 'Sistema Limpio a Cero', data.message);
            await this.loadAccounts();
            await this.loadCategories();
            await this.loadTransactions();
            await this.loadCashFlowAll();
          } catch (err) {
            this.showToast('error', 'Error en Reseteo', err.message);
          }
        }
      };
    }

};
