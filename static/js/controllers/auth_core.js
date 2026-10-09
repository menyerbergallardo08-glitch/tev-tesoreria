// Modulo TEV: TEVAuthCore
window.TEVAuthCore = {
        async initApp() {
          // Clear any legacy localStorage token to prevent auto-login as directivo
          localStorage.removeItem('tev_token');
          const token = this.getToken();
          if (token) {
            try {
              const res = await fetch('/api/auth/me', {
                headers: { 'Authorization': 'Bearer ' + token }
              });
              if (res.ok) {
                this.currentUser = await res.json();
                await this.loadInitialData();
                this.restoreSaleDraft();
                await this.autoSyncBcvRate();
                this.startLiveSync();
              } else {
                sessionStorage.removeItem('tev_token');
              }
            } catch (e) {
              console.error(e);
            }
          }
        },

        async handleLogin() {
          this.loading = true;
          this.loginError = '';
          try {
            const res = await fetch('/api/auth/login', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(this.loginForm)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al iniciar sesión');

            sessionStorage.setItem('tev_token', data.access_token);
            this.currentUser = data.user;
            await this.loadInitialData();
            this.startLiveSync();
            this.showToast('success', 'Bienvenido(a)', 'Ha ingresado como ' + this.currentUser.full_name);
          } catch (err) {
            this.loginError = err.message;
          } finally {
            this.loading = false;
          }
        },

        logout() {
          localStorage.removeItem('tev_token');
          sessionStorage.removeItem('tev_token');
          this.currentUser = null;
          this.activeTab = 'registro';
          this.loginForm = { username: '', password: '' };
        },

        async loadInitialData() {
          await this.loadAccounts();
          await this.loadCategories();
          await this.loadTransactions();
          if (this.currentUser?.role === 'administradora' || this.currentUser?.role === 'directivo') {
            await this.loadCashFlowAll();
          }
          await this.loadBcvRate();
          await this.loadSuppliers();
          if (this.currentUser?.role === 'directivo') {
            await this.loadUsers();
          }
        },

        filterAccountStatus: 'active',
        async loadAccounts() {
          const token = this.getToken();
          const includeAll = (this.filterAccountStatus === 'all' || this.filterAccountStatus === 'inactive');
          const res = await fetch('/api/accounts' + (includeAll ? '?all=true' : ''), {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            this.accounts = await res.json();
            if (this.accounts.length > 0 && !this.form.account_id) {
              const firstActive = this.accounts.find(a => a.is_active);
              this.form.account_id = firstActive ? firstActive.id : this.accounts[0].id;
              this.onAccountChange();
            }
          }
        },

        async loadCategories() {
          const token = this.getToken();
          let url = '/api/categories?month=' + this.filterMonth;
          // Si estamos en la pestaña de presupuesto o filtrando todas/inactivas, incluimos las inactivas
          if (this.filterCategoryStatus === 'all' || this.filterCategoryStatus === 'inactive') {
            url += '&include_inactive=true';
          }
          const res = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            let data = await res.json();
            if (this.filterCategoryStatus === 'active') {
              this.categories = data.filter(c => c.is_active);
            } else if (this.filterCategoryStatus === 'inactive') {
              this.categories = data.filter(c => !c.is_active);
            } else {
              this.categories = data;
            }
          }
        },

        async loadTransactions() {
          const token = this.getToken();
          let url = '/api/transactions?';
          if (this.filterDate) {
            url += 'date=' + this.filterDate;
          } else {
            url += 'month=' + this.filterMonth;
          }
          if (this.filterType) url += '&movement_type=' + this.filterType;

          const res = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            const data = await res.json();
            this.transactions = data.items;
          }
        },

        async loadCashFlowAll() {
          await this.loadCashFlow();
          await this.loadAnnualCashFlow();
          await this.loadDailyCashFlow();
        },

        async loadCashFlow() {
          const token = this.getToken();
          const res = await fetch('/api/dashboard/cash-flow?month=' + this.filterMonth, {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            this.cashFlowData = await res.json();
          }
        },

        async loadAnnualCashFlow() {
          const token = this.getToken();
          const res = await fetch('/api/dashboard/cash-flow-annual?year=2026', {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            this.annualCashFlow = await res.json();
          }
        },

        async loadDailyCashFlow() {
          const token = this.getToken();
          const res = await fetch('/api/dashboard/cash-flow-daily?month=' + this.filterMonth, {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            const data = await res.json();
            this.dailyCashFlow = data.days;
            this.dailyCashFlowTotals = data.totals || {};
          }
        },

        async loadUsers() {
          const token = this.getToken();
          const res = await fetch('/api/auth/users', {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            this.usersList = await res.json();
          }
        },

        openTransferModal() {
          this.transferForm.amount_origin = '';
          this.transferForm.amount_destination = '';
          this.transferForm.reference_number = '';
          this.transferForm.description = '';
          this.showTransferModal = true;
        },

        onTransferAccountsChange() {
          this.recalcTransfer('origin');
        },

        getAccountCurrency(accId) {
          const a = this.accounts.find(x => x.id === accId);
          return a ? a.currency : '';
        },

        // CALCULADORA BIDIRECCIONAL DE TRASPASOS (IMAGEN 1)
        recalcTransfer(source) {
          const origCurr = this.getAccountCurrency(this.transferForm.origin_account_id);
          const destCurr = this.getAccountCurrency(this.transferForm.destination_account_id);
          const rate = parseFloat(this.transferForm.exchange_rate) || 1.0;

          if (origCurr === destCurr) {
            if (source === 'origin') {
              this.transferForm.amount_destination = this.transferForm.amount_origin;
            } else if (source === 'dest') {
              this.transferForm.amount_origin = this.transferForm.amount_destination;
            }
            return;
          }

          // Si sale VES y entra USD/USDT
          if (origCurr === 'VES' && (destCurr === 'USD' || destCurr === 'USDT')) {
            if (source === 'origin' || source === 'rate') {
              const orig = parseFloat(this.transferForm.amount_origin) || 0;
              this.transferForm.amount_destination = rate > 0 ? (orig / rate).toFixed(2) : 0;
            } else if (source === 'dest') {
              const dest = parseFloat(this.transferForm.amount_destination) || 0;
              this.transferForm.amount_origin = (dest * rate).toFixed(2);
            }
          }
          // Si sale USD/USDT y entra VES
          else if ((origCurr === 'USD' || origCurr === 'USDT') && destCurr === 'VES') {
            if (source === 'origin' || source === 'rate') {
              const orig = parseFloat(this.transferForm.amount_origin) || 0;
              this.transferForm.amount_destination = (orig * rate).toFixed(2);
            } else if (source === 'dest') {
              const dest = parseFloat(this.transferForm.amount_destination) || 0;
              this.transferForm.amount_origin = rate > 0 ? (dest / rate).toFixed(2) : 0;
            }
          }
        },

        openOnePageReport() {
          this.showOnePageModal = true;
        },

        printReport() {
          window.print();
        },

        sumAnnual(prop) {
          if (!this.annualCashFlow?.months) return 0;
          return this.annualCashFlow.months.reduce((acc, m) => acc + (m[prop] || 0), 0);
        },

        async openInitialBalancesModal() {
          const token = this.getToken();
          const res = await fetch('/api/accounts/monthly-balances?month=' + this.filterMonth, {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (res.ok) {
            const data = await res.json();
            this.monthlyBalancesForm = data.balances;
            this.showInitialBalancesModal = true;
          }
        },

        async saveInitialBalances() {
          const token = this.getToken();
          try {
            const payload = {
              month: this.filterMonth,
              balances: this.monthlyBalancesForm.map(b => ({
                account_id: b.account_id,
                initial_balance: parseFloat(b.initial_balance) || 0.0
              }))
            };
            const res = await fetch('/api/accounts/monthly-balances', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(payload)
            });
            if (res.ok) {
              this.showInitialBalancesModal = false;
              this.showToast('success', 'Saldos Actualizados', 'Los saldos iniciales fueron guardados.');
              await this.loadCashFlowAll();
              await this.loadAccounts();
            }
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        async changeOwnPassword() {
          const token = this.getToken();
          try {
            const res = await fetch('/api/auth/change-password', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(this.changePasswordForm)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al cambiar contraseña');

            this.showChangePasswordModal = false;
            this.changePasswordForm = { old_password: '', new_password: '' };
            this.showToast('success', 'Éxito', 'Su contraseña ha sido cambiada.');
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        async createUser() {
          const token = this.getToken();
          try {
            const res = await fetch('/api/auth/users', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(this.newUserForm)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al crear usuario');

            this.showNewUserModal = false;
            this.newUserForm = { full_name: '', username: '', role: 'cajera', password: '' };
            this.showToast('success', 'Usuario Creado', 'El nuevo usuario fue registrado con éxito.');
            await this.loadUsers();
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        openResetPasswordModal(user) {
          this.selectedUserForReset = user;
          this.resetPasswordForm.new_password = '';
          this.showResetPasswordModal = true;
        },

        async resetUserPassword() {
          const token = this.getToken();
          try {
            const res = await fetch('/api/auth/users/' + this.selectedUserForReset.id + '/password', {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(this.resetPasswordForm)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al restablecer');

            this.showResetPasswordModal = false;
            this.showToast('success', 'Clave Restablecida', 'La clave fue actualizada.');
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        async toggleUserStatus(userId) {
          const token = this.getToken();
          try {
            const res = await fetch('/api/auth/users/' + userId + '/toggle-status', {
              method: 'PATCH',
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.showToast('success', 'Estado Actualizado', 'El estado del usuario fue modificado.');
              await this.loadUsers();
            }
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        openEditUserModal(user) {
          this.editUserForm = {
            id: user.id,
            full_name: user.full_name,
            username: user.username,
            role: user.role,
            password: ''
          };
          this.showEditUserModal = true;
        },

        async saveEditUser() {
          const token = this.getToken();
          try {
            const payload = {
              full_name: this.editUserForm.full_name,
              username: this.editUserForm.username,
              role: this.editUserForm.role
            };
            if (this.editUserForm.password && this.editUserForm.password.trim().length >= 4) {
              payload.password = this.editUserForm.password.trim();
            }

            const res = await fetch('/api/auth/users/' + this.editUserForm.id, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al actualizar usuario');

            this.showEditUserModal = false;
            this.showToast('success', 'Usuario Actualizado', 'Los datos del usuario se guardaron con éxito.');
            await this.loadUsers();
          } catch (err) {
            this.showToast('error', 'Error al editar', err.message);
          }
        },

        async deleteUser(user) {
          if (!confirm(`¿Está seguro de eliminar definitivamente al usuario "${user.username}" (${user.full_name})? Esta acción no se puede deshacer.`)) {
            return;
          }
          const token = this.getToken();
          try {
            const res = await fetch('/api/auth/users/' + user.id, {
              method: 'DELETE',
              headers: { 'Authorization': 'Bearer ' + token }
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al eliminar usuario');

            this.showToast('success', 'Usuario Eliminado', data.message || 'Usuario eliminado con éxito.');
            await this.loadUsers();
          } catch (err) {
            this.showToast('error', 'Error al eliminar', err.message);
          }
        },


        async purgeTestUsers() {
          if (!confirm('¿Desea eliminar TODOS los usuarios de prueba existentes y dejar únicamente la cuenta Master/Directivo?')) {
            return;
          }
          const token = this.getToken();
          try {
            const res = await fetch('/api/users/purge-test-users', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + token }
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al purgar usuarios');

            this.showToast('success', 'Limpieza Completa', data.message);
            await this.loadUsers();
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        async loadAuditLogs() {
          const token = this.getToken();
          try {
            let url = '/api/audit-logs?limit=150';
            if (this.auditFilterAction) url += '&action=' + encodeURIComponent(this.auditFilterAction);
            if (this.auditFilterUser) url += '&username=' + encodeURIComponent(this.auditFilterUser);
            const res = await fetch(url, {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.auditLogs = await res.json();
            }
          } catch (err) {
            console.error('Error al cargar pistas de auditoria:', err);
          }
        },

        viewAuditDetail(log) {
          this.selectedAuditDetail = log;
          this.showAuditDetailModal = true;
        },

        formatJsonPayload(jsonStr) {
          if (!jsonStr) return '{}';
          try {
            const parsed = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
            return JSON.stringify(parsed, null, 2);
          } catch (e) {
            return String(jsonStr);
          }
        },

};
