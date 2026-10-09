    function roundNumber(num, dec) { return Math.round(num * Math.pow(10, dec)) / Math.pow(10, dec); }

    function app() {
      return {
        currentUser: null,
        activeTab: 'registro',
        cashFlowSubTab: 'resumen',
        loading: false,
        loginError: '',
        loginForm: { username: '', password: '' },

        accounts: [],
        categories: [],
        transactions: [],
        usersList: [],
        filterMonth: '2026-09',
        salesFilterMode: 'mes',
        salesFilterDate: new Date().toISOString().split('T')[0],
        filterType: '',
        filterCategoryStatus: 'all',

        selectedAccountCurrency: 'USD',

        form: {
          date: new Date().toISOString().split('T')[0],
          movement_type: 'EGRESO',
          subtype: 'GASTO_OPERATIVO',
          account_id: 1,
          category_id: '',
          amount_original: '',
          currency: 'USD',
          exchange_rate: 756.71,
          amount_usd: 0,
          reference_number: '',
          beneficiary: '',
          description: ''
        },

        cashFlowData: {
          initial_balance_usd: 0,
          total_inflows_usd: 0,
          total_outflows_usd: 0,
          fx_differential_usd: 0,
          net_cash_flow_usd: 0,
          final_balance_usd: 0,
          accounts_detail: [],
          inflows_breakdown: {},
          outflows_breakdown: {}
        },

        annualCashFlow: { year: 2026, months: [] },
        dailyCashFlow: [],
        dailyCashFlowTotals: {},
        dailyViewMode: 'matriz',

        activeTab: 'pos_caliente',
        
        paymentMethod: 'EFECTIVO_USD',
        digitalChannel: 'CASHEA',
        hasRetention: false,
        hasCasheaDownpayment: false,
        isSubmittingSale: false,
        loadingBcv: false,

        
        setDocumentType(type) {
          if (type === 'CASHEA') {
            this.liveSaleForm.doc_type = 'FACTURA_FISCAL';
            this.setPaymentMethod('CASHEA');
          } else if (type === 'DEVOLUCION') {
            this.liveSaleForm.doc_type = 'DEVOLUCION';
            this.paymentMethod = 'EFECTIVO_USD';
          } else {
            this.liveSaleForm.doc_type = type;
            if (this.paymentMethod === 'CASHEA') {
              this.setPaymentMethod('EFECTIVO_USD');
            }
          }
        },

        setPaymentMethod(method) {
          this.paymentMethod = method;
          if (method === 'EFECTIVO_USD') {
            const acc = this.accounts.find(a => a.name.includes('Efectivo USD') && a.currency === 'USD') || this.accounts.find(a => a.currency === 'USD');
            if (acc) this.liveSaleForm.account_id = acc.id;
            this.liveSaleForm.pos_terminal = '';
            this.liveSaleForm.pos_lot_number = '';
          } else if (method === 'EFECTIVO_VES') {
            const acc = this.accounts.find(a => a.name.includes('Efectivo VES') && a.currency === 'VES') || this.accounts.find(a => a.currency === 'VES');
            if (acc) this.liveSaleForm.account_id = acc.id;
            this.liveSaleForm.pos_terminal = '';
            this.liveSaleForm.pos_lot_number = '';
          } else if (method === 'POS') {
            if (!this.liveSaleForm.pos_terminal) this.liveSaleForm.pos_terminal = 'POS Banesco';
            this.onPosTerminalChange();
          } else if (method === 'PAGO_MOVIL') {
            const acc = this.accounts.find(a => a.name.includes('Pago Móvil')) || this.accounts.find(a => a.currency === 'VES');
            if (acc) this.liveSaleForm.account_id = acc.id;
            this.liveSaleForm.pos_terminal = '';
            this.liveSaleForm.pos_lot_number = '';
          } else if (method === 'CASHEA') {
            const acc = this.accounts.find(a => a.name.includes('Cashea')) || this.accounts.find(a => a.name.includes('BNC')) || (this.accounts.length > 0 ? this.accounts[0] : null);
            if (acc) this.liveSaleForm.account_id = acc.id;
            this.liveSaleForm.pos_terminal = '';
            this.liveSaleForm.pos_lot_number = '';
          } else if (method === 'NOTA_CREDITO') {
            this.liveSaleForm.account_id = null;
            this.liveSaleForm.is_credit = true;
            this.liveSaleForm.pos_terminal = '';
            this.liveSaleForm.pos_lot_number = '';
          } else if (method === 'DIGITAL') {
            this.onDigitalChannelChange();
          }
        },

        onPosTerminalChange() {
          const t = this.liveSaleForm.pos_terminal || 'POS Banesco';
          let match = null;
          if (t.includes('Banesco')) match = this.accounts.find(a => a.name.includes('Banesco'));
          else if (t.includes('Bancaribe')) match = this.accounts.find(a => a.name.includes('Bancaribe'));
          else if (t.includes('Venezuela')) match = this.accounts.find(a => a.name.includes('Venezuela'));
          else if (t.includes('BNC')) match = this.accounts.find(a => a.name.includes('BNC'));
          
          if (match) this.liveSaleForm.account_id = match.id;
          else if (this.accounts.length > 0) this.liveSaleForm.account_id = this.accounts[0].id;
        },

        onDigitalChannelChange() {
          let match = null;
          if (this.digitalChannel === 'CASHEA') match = this.accounts.find(a => a.name.includes('Cashea'));
          else if (this.digitalChannel === 'ZELLE') match = this.accounts.find(a => a.name.includes('Zelle'));
          else if (this.digitalChannel === 'BINANCE') match = this.accounts.find(a => a.name.includes('Binance') || a.currency === 'USDT');
          
          if (match) this.liveSaleForm.account_id = match.id;
        },

        getSelectedAccountNameForLive() {
          const acc = this.accounts.find(a => a.id === this.liveSaleForm.account_id);
          return acc ? `${acc.name} (${acc.currency})` : 'Caja Principal';
        },

        liveSaleForm: {
          date: new Date().toISOString().split('T')[0],
          doc_type: 'FACTURA_FISCAL',
          doc_number: '',
          client_name: '',
          client_rif: '',
          is_credit: false,
          amount_original: '',
          currency: 'USD',
          account_id: 1,
          pos_terminal: '',
          pos_lot_number: '',
          tax_retention_amount: 0,
          tax_retention_proof: '',
          reference_number: '',
          description: ''
        },
        liveMonitorData: null,
        receivablesList: [],
        cxcSearch: '',
        cxcStatusFilter: '',
        showAbonoModal: false,
        selectedCreditObj: null,
        abonoForm: {
          date: new Date().toISOString().split('T')[0],
          amount_original: '',
          currency: 'USD',
          account_id: 1,
          reference_number: '',
          description: ''
        },
        cuadreDate: new Date().toISOString().split('T')[0],
        cashCloseSummary: null,
        cashCloseHistory: [],
        salesAccumulatedData: null,
        showCashCloseReceiptModal: false,
        cuadreNotes: '',

        arqueo: {
          b100: 0, b50: 0, b20: 0, b10: 0, b5: 0, b1: 0
        },
        arqueoVES: {
          b500: 0, b200: 0, b100: 0, b50: 0, b20: 0, b10: 0
        },
        arqueoCurrency: 'USD',
        showArqueoVesReceiptModal: false,
        duplicateWarning: false,
        duplicateWarningMessage: '',

        bcvRate: parseFloat(localStorage.getItem('tev_bcv_rate')) || 827.74,
        newBcvRate: parseFloat(localStorage.getItem('tev_bcv_rate')) || 827.74,
        showBcvRateModal: false,
        suppliers: [],
        selectedSupplierId: '',
        selectedSupplierObj: null,
        showSupplierModal: false,
        newSupplierForm: { name: '', rif: '', phone: '', bank_details: '' },
        filterDate: '',
        showArqueoReceiptModal: false,
        onePageMode: 'mensual',
        onePageDate: new Date().toISOString().split('T')[0],
        dailyOnePageData: null,

        showConfirmModal: false,
        showTransferModal: false,
        showEditCatModal: false,
        showNewCatModal: false,
        showNewAccountModal: false,
        showEditAccountModal: false,
        showInitialBalancesModal: false,
        showChangePasswordModal: false,
        showNewUserModal: false,
        showEditUserModal: false,
        showResetPasswordModal: false,
        showOnePageModal: false,
        showAuditDetailModal: false,
        auditLogs: [],
        auditFilterAction: '',
        auditFilterUser: '',
        selectedAuditDetail: null,
        companyRif: 'J-50248654-2',

        editingCat: {},
        newCatForm: { code: null, name: '', monthly_budget_usd: 0 },
        editingAccount: {},
        newAccountForm: { name: '', currency: 'USD', account_type: 'Caja Operativa', initial_balance: 0 },
        selectedUserForReset: null,

        changePasswordForm: { old_password: '', new_password: '' },
        newUserForm: { full_name: '', username: '', role: 'cajera', password: '' },
        editUserForm: { id: null, full_name: '', username: '', role: 'cajera', password: '' },
        resetPasswordForm: { new_password: '' },
        monthlyBalancesForm: [],

        transferForm: {
          date: new Date().toISOString().split('T')[0],
          origin_account_id: 3, // Banco Banesco VES
          destination_account_id: 1, // Efectivo USD
          amount_origin: '',
          amount_destination: '',
          exchange_rate: 756.71,
          reference_number: '',
          description: ''
        },

        showManualsModal: false,
        showManualReaderModal: false,
        currentManual: { role: '', title: '', content: '' },

        openManualsModal() {
          this.showManualsModal = true;
        },

        async openManualReader(role) {
          try {
            const token = this.getToken();
            const res = await fetch(`/api/manuals/${role}`, {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              const data = await res.json();
              const roleTitles = {
                'cajera': '👩‍💼 Manual Operativo: Cajera (Punto de Venta y Arqueo)',
                'administradora': '👩‍💻 Manual de Gestión: Administradora (Tesorería Central)',
                'directivo': '👔 Manual Estratégico: Directivo (Gerencia y Finanzas)'
              };
              this.currentManual = {
                role: role,
                title: roleTitles[role] || 'Manual de Usuario',
                content: data.content
              };
              this.showManualReaderModal = true;
            } else {
              this.showToast('error', 'Error al cargar', 'No se pudo cargar el manual seleccionado.');
            }
          } catch (e) {
            this.showToast('error', 'Error de Conexión', 'Verifique su conexión con el servidor.');
          }
        },

        printManual() {
          window.print();
        },

        toast: { show: false, type: 'success', title: '', message: '' },

        showToast(type, title, message) {
          this.toast = { show: true, type, title, message };
          setTimeout(() => { this.toast.show = false; }, 4000);
        },

        getToken() {
          return sessionStorage.getItem('tev_token');
        },

        async quickLogin(user, pass) {
          this.loginForm.username = user;
          this.loginForm.password = pass;
          await this.handleLogin();
        },

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

        onAccountChange() {
          const acc = this.accounts.find(a => a.id === this.form.account_id);
          if (acc) {
            this.selectedAccountCurrency = acc.currency;
            this.form.currency = acc.currency;
            if (acc.currency === 'VES') {
              if (this.form.subtype !== 'CAMBIO_DIVISAS') {
                this.form.exchange_rate = this.bcvRate || 827.74;
              }
            } else {
              this.form.exchange_rate = 1.0;
            }
          }
        },

        setFormType(movType, subType) {
          this.form.movement_type = movType;
          this.form.subtype = subType;
          if (subType === 'VENTA_DIARIA') {
            this.form.beneficiary = 'Ventas Mostrador - Tienda Valencia';
            this.form.description = 'Cierre de ventas total de la jornada';
          }
        },

        getFormTitle() {
          const map = {
            'GASTO_OPERATIVO': 'Registro de Gasto Operativo (Partida)',
            'PAGO_PROVEEDOR': 'Registro de Pago a Proveedor',
            'VENTA_DIARIA': 'Cierre de Venta Diaria (Total del Día / Z)',
            'COBRO_CXC': 'Registro de Cobro de Cuenta por Cobrar'
          };
          return map[this.form.subtype] || 'Registro de Movimiento';
        },

        formatRetentionInput(targetForm) {
          if (!this[targetForm]) return;
          let val = (this[targetForm].tax_retention_proof || '').trim();
          if (!val) return;
          let digits = val.replace(/\D/g, '');
          
          if (digits.length === 14) {
            this[targetForm].tax_retention_proof = digits;
            return;
          }
          
          let parts = val.split(/[-/.\s]+/);
          if (parts.length === 3) {
            let yr = parseInt(parts[0], 10);
            let mo = parseInt(parts[1], 10);
            let seq = parseInt(parts[2], 10);
            if (!isNaN(yr) && !isNaN(mo) && !isNaN(seq) && yr >= 2000 && yr <= 2099 && mo >= 1 && mo <= 12) {
              this[targetForm].tax_retention_proof = `${yr.toString().padStart(4, '0')}${mo.toString().padStart(2, '0')}${seq.toString().padStart(8, '0')}`;
              return;
            }
          }
          
          if (digits.length >= 7 && digits.length < 14) {
            let yr = parseInt(digits.substring(0, 4), 10);
            let mo = parseInt(digits.substring(4, 6), 10);
            let seq = parseInt(digits.substring(6), 10);
            if (!isNaN(yr) && !isNaN(mo) && !isNaN(seq) && yr >= 2000 && yr <= 2099 && mo >= 1 && mo <= 12) {
              this[targetForm].tax_retention_proof = `${yr.toString().padStart(4, '0')}${mo.toString().padStart(2, '0')}${seq.toString().padStart(8, '0')}`;
              return;
            }
          }
        },

        getRetentionValidationStatus(proof) {
          if (!proof || !proof.trim()) {
            return { valid: false, message: 'Estructura oficial SENIAT: AAAAMM + 8 dígitos (ej: 20260900000001)' };
          }
          let clean = proof.replace(/\D/g, '');
          if (clean.length === 14) {
            let yr = parseInt(clean.substring(0, 4), 10);
            let mo = parseInt(clean.substring(4, 6), 10);
            let seq = clean.substring(6);
            if (yr < 2000 || yr > 2099) return { valid: false, message: `Año fiscal ${yr} fuera de rango (2000-2099)` };
            if (mo < 1 || mo > 12) return { valid: false, message: `Mes ${mo} inválido (debe ser 01 a 12)` };
            return { valid: true, message: `✓ Comprobante Válido: Año ${yr} | Mes ${mo.toString().padStart(2, '0')} | N° ${seq}` };
          }
          return { valid: false, message: `${clean.length}/14 dígitos ingresados (Faltan ${14 - clean.length} dígitos para cumplir Providencia SNAT/2015/0049)` };
        },

        applyRetentionPreset(type) {
          const total = parseFloat(this.liveSaleForm.amount_original || 0);
          if (total <= 0) {
            this.showToast('warning', 'Monto Requerido', 'Ingrese primero el monto total de la Factura Fiscal para calcular la retención.');
            return;
          }
          const base = total / 1.16;
          const iva = base * 0.16;
          if (type === '75_IVA') {
            this.liveSaleForm.tax_retention_amount = parseFloat((iva * 0.75).toFixed(2));
            this.showToast('info', 'Retención Aplicada', `75% del IVA: $${this.liveSaleForm.tax_retention_amount.toFixed(2)} USD`);
          } else if (type === '100_IVA') {
            this.liveSaleForm.tax_retention_amount = parseFloat((iva * 1.00).toFixed(2));
            this.showToast('info', 'Retención Aplicada', `100% del IVA: $${this.liveSaleForm.tax_retention_amount.toFixed(2)} USD`);
          } else if (type === '2_ISLR') {
            this.liveSaleForm.tax_retention_amount = parseFloat((base * 0.02).toFixed(2));
            this.showToast('info', 'Retención Aplicada', `2% ISLR sobre Base: $${this.liveSaleForm.tax_retention_amount.toFixed(2)} USD`);
          } else if (type === '5_ISLR') {
            this.liveSaleForm.tax_retention_amount = parseFloat((base * 0.05).toFixed(2));
            this.showToast('info', 'Retención Aplicada', `5% ISLR sobre Base: $${this.liveSaleForm.tax_retention_amount.toFixed(2)} USD`);
          }
        },

        getRetentionCalculations() {
          const total = parseFloat(this.liveSaleForm.amount_original || 0);
          const retAmt = parseFloat(this.liveSaleForm.tax_retention_amount || 0);
          if (total <= 0) return { base: '0.00', iva: '0.00', pctIva: '0.0', pctTotal: '0.0', netToPay: 0 };
          const base = total / 1.16;
          const iva = base * 0.16;
          const pctIva = iva > 0 ? ((retAmt / iva) * 100) : 0;
          const pctTotal = (retAmt / total) * 100;
          const netToPay = Math.max(0, total - retAmt);
          return {
            base: base.toFixed(2),
            iva: iva.toFixed(2),
            pctIva: pctIva.toFixed(1),
            pctTotal: pctTotal.toFixed(1),
            netToPay: netToPay
          };
        },

        async submitLiveSale() {
          if (this.isSubmittingSale) return;

          const rawAmt = String(this.liveSaleForm.amount_original || '').replace(',', '.').trim();
          const amt = parseFloat(rawAmt);
          if (isNaN(amt) || amt <= 0) {
            this.showToast('warning', 'Monto Inválido', 'Por favor ingrese un monto mayor a $0.00 a cobrar.');
            return;
          }
          this.liveSaleForm.amount_original = amt;

          if (!this.liveSaleForm.doc_number || !this.liveSaleForm.doc_number.trim()) {
            this.showToast('warning', 'N° Documento Requerido', 'Por favor ingrese el número de Factura o Nota de Entrega.');
            return;
          }
          if (!this.liveSaleForm.client_name || !this.liveSaleForm.client_name.trim()) {
            this.showToast('warning', 'Cliente Requerido', 'Por favor ingrese el nombre del cliente o empresa.');
            return;
          }

          // Asegurar cuenta de destino para la forma de pago seleccionada
          if (!this.liveSaleForm.is_credit && !this.liveSaleForm.account_id) {
            this.setPaymentMethod(this.paymentMethod || 'EFECTIVO_USD');
          }

          // Normalizar abono inicial de Cashea o Crédito si aplica
          if (this.liveSaleForm.is_credit || this.hasCasheaDownpayment) {
            const rawDown = String(this.liveSaleForm.initial_downpayment_amount || '0').replace(',', '.').trim();
            this.liveSaleForm.initial_downpayment_amount = parseFloat(rawDown) || 0;
          } else {
            this.liveSaleForm.initial_downpayment_amount = 0;
          }

          // Validación Estricta de Retención SENIAT (Exclusivo Facturas Fiscales)
          if (this.liveSaleForm.doc_type === 'FACTURA_FISCAL' && this.hasRetention) {
            const rawRet = String(this.liveSaleForm.tax_retention_amount || '0').replace(',', '.').trim();
            const retAmt = parseFloat(rawRet);
            this.liveSaleForm.tax_retention_amount = isNaN(retAmt) ? 0 : retAmt;
            this.formatRetentionInput('liveSaleForm');
            const proofVal = (this.liveSaleForm.tax_retention_proof || '').trim();

            if (isNaN(retAmt) || retAmt <= 0) {
              this.showToast('warning', 'Monto de Retención Inválido', 'El monto de retención debe ser mayor a $0.00.');
              return;
            }
            if (retAmt >= amt) {
              this.showToast('error', 'Retención Excesiva', `El monto retenido ($${retAmt.toFixed(2)}) no puede ser mayor o igual al total de la venta ($${amt.toFixed(2)}).`);
              return;
            }
            if (!proofVal) {
              this.showToast('warning', 'Comprobante Requerido', 'Debe indicar el Número de Comprobante SENIAT de 14 dígitos si aplicó una retención.');
              return;
            }
            const status = this.getRetentionValidationStatus(proofVal);
            if (!status.valid) {
              this.showToast('error', 'Comprobante Inválido', status.message || 'El comprobante debe tener exactamente 14 dígitos (AAAAMM00000000).');
              return;
            }
          } else {
            this.liveSaleForm.tax_retention_amount = 0;
            this.liveSaleForm.tax_retention_proof = '';
          }

          const token = this.getToken();
          if (!token) {
            this.showToast('error', 'Sesión Expirada', 'Su sesión ha expirado. Por favor cierre sesión e ingrese nuevamente.');
            return;
          }

          this.isSubmittingSale = true;
          try {
            const res = await fetch('/api/sales/live', {
              method: 'POST',
              headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(this.liveSaleForm)
            });

            let d = null;
            try {
              d = await res.json();
            } catch (jsonErr) {
              if (!res.ok) {
                this.showToast('error', 'Error del Servidor', `El servidor respondió con código ${res.status}.`);
                return;
              }
            }

            if (res.ok && d) {
              this.showToast('success', '¡Venta Registrada Exitosamente!', d.message || 'Cobro registrado correctamente.');
              this.clearSaleDraft();
              this.liveSaleForm.doc_number = '';
              this.liveSaleForm.client_name = '';
              this.liveSaleForm.amount_original = '';
              this.liveSaleForm.reference_number = '';
              this.liveSaleForm.pos_lot_number = '';
              this.liveSaleForm.initial_downpayment_amount = 0;
              this.liveSaleForm.tax_retention_amount = 0;
              this.liveSaleForm.tax_retention_proof = '';
              this.hasRetention = false;
              this.hasCasheaDownpayment = false;
              await this.loadInitialData();
            } else {
              this.showToast('error', 'No se pudo registrar', (d && d.detail) ? d.detail : 'Ocurrió un error en la validación.');
            }
          } catch (e) {
            this.showToast('error', 'Error al procesar', e.message || 'Verifique la conexión con el servidor.');
          } finally {
            this.isSubmittingSale = false;
          }
        },

        async loadLiveMonitor() {
          try {
            const token = this.getToken();
            const res = await fetch(`/api/sales/live-monitor?date=${this.cuadreDate}`, {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.liveMonitorData = await res.json();
            }
          } catch (e) {
            console.error('Error loading live monitor:', e);
          }
        },

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

        async submitMovement() {
          const rawAmt = String(this.form.amount_original || '').replace(',', '.').trim();
          const amt = parseFloat(rawAmt);
          if (isNaN(amt) || amt <= 0) {
            this.showToast('warning', 'Monto Inválido', 'Por favor ingrese un monto mayor a cero.');
            return;
          }
          this.form.amount_original = amt;
          
          if (this.form.movement_type === 'TRANSFERENCIA') {
            if (!this.form.destination_account_id) {
              this.showToast('warning', 'Cuenta Destino Requerida', 'Por favor seleccione la cuenta bancaria o caja destino.');
              return;
            }
            this.transferForm.source_account_id = this.form.account_id;
            this.transferForm.destination_account_id = this.form.destination_account_id;
            this.transferForm.source_amount = this.form.amount_original;
            this.transferForm.date = this.form.date;
            this.transferForm.reference_number = this.form.reference_number;
            this.transferForm.description = this.form.description || 'Traspaso entre cuentas';
            await this.executeTransfer();
            this.form.amount_original = '';
            this.form.reference_number = '';
            this.form.description = '';
            return;
          }

          if (this.form.subtype === 'GASTO_OPERATIVO' && !this.form.category_id) {
            this.showToast('warning', 'Partida Requerida', 'Por favor seleccione la Partida Presupuestaria del gasto.');
            return;
          }
          
          await this.executeSubmitTransaction();
        },

        prepareSubmitTransaction() {
          this.submitMovement();
        },

        async executeSubmitTransaction() {
          this.showConfirmModal = false;
          const token = this.getToken();
          try {
            const payload = {
              date: this.form.date,
              movement_type: this.form.movement_type,
              subtype: this.form.subtype,
              account_id: this.form.account_id,
              category_id: this.form.category_id ? parseInt(this.form.category_id) : null,
              amount_original: parseFloat(this.form.amount_original),
              currency: this.selectedAccountCurrency,
              exchange_rate: parseFloat(this.form.exchange_rate) || 1.0,
              reference_number: this.form.reference_number || '',
              beneficiary: this.form.beneficiary || '',
              description: this.form.description || ''
            };

            const res = await fetch('/api/transactions', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al guardar');

            this.showToast('success', '¡Guardado Exitoso!', 'El movimiento fue registrado correctamente.');
            this.form.amount_original = '';
            this.form.reference_number = '';
            this.form.beneficiary = '';
            this.form.description = '';

            await this.loadAccounts();
            await this.loadCategories();
            await this.loadTransactions();
            if (this.currentUser?.role === 'administradora' || this.currentUser?.role === 'directivo') {
              await this.loadCashFlowAll();
            }
          } catch (err) {
            this.showToast('error', 'Error en Registro', err.message);
          }
        },

        async executeTransfer() {
          const token = this.getToken();
          try {
            const res = await fetch('/api/transactions/transfer', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(this.transferForm)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al traspasar');

            this.showTransferModal = false;
            this.showToast('success', 'Traspaso Exitoso', 'Los fondos fueron transferidos con partida doble contable.');
            await this.loadAccounts();
            await this.loadTransactions();
            if (this.currentUser?.role === 'administradora' || this.currentUser?.role === 'directivo') {
              await this.loadCashFlowAll();
            }
          } catch (err) {
            this.showToast('error', 'Error en Traspaso', err.message);
          }
        },

        async verifyTransaction(id) {
          const token = this.getToken();
          try {
            const res = await fetch('/api/transactions/' + id + '/verify', {
              method: 'PATCH',
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.showToast('success', 'Verificado', 'El movimiento fue auditado y aprobado.');
              await this.loadTransactions();
            }
          } catch (err) {
            console.error(err);
          }
        },

        async cancelTransaction(id) {
          if (!confirm('¿Está seguro de anular este movimiento? Se revertirá en los saldos.')) return;
          const token = this.getToken();
          try {
            const res = await fetch('/api/transactions/' + id, {
              method: 'DELETE',
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.showToast('warning', 'Anulado', 'El movimiento fue anulado.');
              await this.loadAccounts();
              await this.loadTransactions();
              await this.loadCategories();
              if (this.currentUser?.role === 'administradora' || this.currentUser?.role === 'directivo') {
                await this.loadCashFlowAll();
              }
            }
          } catch (err) {
            console.error(err);
          }
        },

        openEditCategory(cat) {
          this.editingCat = { ...cat };
          this.showEditCatModal = true;
        },

        async saveEditedCategory() {
          const token = this.getToken();
          try {
            const res = await fetch('/api/categories/' + this.editingCat.id, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify({
                monthly_budget_usd: this.editingCat.monthly_budget_usd,
                is_active: this.editingCat.is_active
              })
            });
            if (res.ok) {
              this.showEditCatModal = false;
              this.showToast('success', 'Partida Actualizada', 'Los cambios en la partida fueron guardados exitosamente.');
              await this.loadCategories();
            } else {
              const errData = await res.json();
              throw new Error(errData.detail || 'Error al guardar');
            }
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        async toggleCategoryActive(cat) {
          const actionText = cat.is_active ? 'inactivar' : 'reactivar';
          const confirmMsg = cat.is_active 
            ? `¿Desea inactivar la partida "${cat.code} - ${cat.name}"?\n\nLos registros históricos se conservarán intactos, pero no estará disponible para nuevos gastos.`
            : `¿Desea reactivar la partida "${cat.code} - ${cat.name}" para permitir nuevos registros de gastos?`;
            
          if (!confirm(confirmMsg)) return;

          const token = this.getToken();
          try {
            const res = await fetch('/api/categories/' + cat.id, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify({
                is_active: !cat.is_active
              })
            });
            if (res.ok) {
              this.showToast('success', cat.is_active ? 'Partida Inactivada' : 'Partida Reactivada', 
                cat.is_active ? 'La partida fue retirada de nuevos registros.' : 'La partida está disponible nuevamente.');
              await this.loadCategories();
            } else {
              const errData = await res.json();
              throw new Error(errData.detail || 'Error al actualizar estado');
            }
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        openNewCategoryModal() {
          const maxCode = this.categories.length > 0 ? Math.max(...this.categories.map(c => c.code || 0)) : 0;
          this.newCatForm = {
            code: maxCode + 1,
            name: '',
            monthly_budget_usd: 100
          };
          this.showNewCatModal = true;
        },

        async saveNewCategory() {
          if (!this.newCatForm.name || !this.newCatForm.name.trim()) {
            this.showToast('warning', 'Nombre Requerido', 'Debe escribir el nombre de la partida presupuestaria');
            return;
          }
          if (!this.newCatForm.code) {
            this.showToast('warning', 'Código Requerido', 'Debe ingresar un código numérico para la partida');
            return;
          }
          const token = this.getToken();
          try {
            const res = await fetch('/api/categories', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify({
                code: parseInt(this.newCatForm.code),
                name: this.newCatForm.name.trim(),
                monthly_budget_usd: parseFloat(this.newCatForm.monthly_budget_usd) || 0
              })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al crear la partida');

            this.showNewCatModal = false;
            this.showToast('success', 'Partida Creada', `Partida "${data.name}" creada exitosamente`);
            await this.loadCategories();
            if (this.form.movement_type === 'EGRESO' && this.form.subtype === 'GASTO_OPERATIVO') {
              this.form.category_id = data.id;
            }
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        triggerExcelUpload() {
          this.$refs.excelInput.click();
        },

        async uploadExcelFile(event) {
          const file = event.target.files[0];
          if (!file) return;

          const token = this.getToken();
          const formData = new FormData();
          formData.append('file', file);

          this.showToast('warning', 'Procesando Archivo', 'Importando gastos desde el archivo Excel...');

          try {
            const res = await fetch('/api/import/excel', {
              method: 'POST',
              headers: {
                'Authorization': 'Bearer ' + token
              },
              body: formData
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al importar archivo');

            this.showToast('success', 'Importación Exitosa', data.message);
            this.filterMonth = data.month;
            await this.loadTransactions();
            await this.loadCategories();
            await this.loadAccounts();
            if (this.currentUser?.role === 'administradora' || this.currentUser?.role === 'directivo') {
              await this.loadCashFlowAll();
            }
          } catch (err) {
            this.showToast('error', 'Error al Importar', err.message);
          } finally {
            event.target.value = '';
          }
        },

        async confirmClearTransactions() {
          if (!confirm('¿Está seguro de que desea VACIAR todos los movimientos para empezar la base de datos totalmente limpia desde cero? Podrá volver a cargar cualquier Excel cuando lo desee.')) {
            return;
          }
          const token = this.getToken();
          try {
            const res = await fetch('/api/admin/clear-transactions', {
              method: 'POST',
              headers: {
                'Authorization': 'Bearer ' + token
              }
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al limpiar');

            this.showToast('success', 'Base Limpia', data.message);
            await this.loadTransactions();
            await this.loadCategories();
            await this.loadAccounts();
            if (this.currentUser?.role === 'administradora' || this.currentUser?.role === 'directivo') {
              await this.loadCashFlowAll();
            }
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        openNewAccountModal() {
          this.newAccountForm = {
            name: '',
            currency: 'USD',
            account_type: 'Caja Operativa',
            initial_balance: 0.0
          };
          this.showNewAccountModal = true;
        },

        async saveNewAccount() {
          if (!this.newAccountForm.name || !this.newAccountForm.name.trim()) {
            this.showToast('warning', 'Nombre Requerido', 'Debe escribir el nombre de la caja o banco');
            return;
          }
          const token = this.getToken();
          try {
            const res = await fetch('/api/accounts', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(this.newAccountForm)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al crear la cuenta');

            this.showNewAccountModal = false;
            this.showToast('success', 'Caja Creada', `La cuenta "${data.name}" fue creada exitosamente`);
            await this.loadAccounts();
            this.form.account_id = data.id;
            this.onAccountChange();
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        openEditAccountModal(acc) {
          this.editingAccount = { ...acc };
          this.showEditAccountModal = true;
        },

        async saveEditAccount() {
          const token = this.getToken();
          try {
            const res = await fetch('/api/accounts/' + this.editingAccount.id, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify({
                name: this.editingAccount.name,
                account_type: this.editingAccount.account_type,
                initial_balance: this.editingAccount.initial_balance,
                is_active: this.editingAccount.is_active
              })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al actualizar');

            this.showEditAccountModal = false;
            this.showToast('success', 'Caja Actualizada', 'Los datos de la cuenta fueron guardados');
            await this.loadAccounts();
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
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

        
        getAvailableAccountsForForm() {
          if (this.form.movement_type === 'EGRESO') {
            return this.accounts.filter(a => !a.only_income && !a.name.toUpperCase().includes('CASHEA'));
          }
          return this.accounts;
        },

        getAccountBalance(name) {
          const acc = this.accounts.find(a => a.name === name);
          return acc ? (acc.current_balance || 0.0) : 0.0;
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

        async loadSuppliers() {
          try {
            const token = this.getToken();
            const res = await fetch('/api/suppliers', {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              this.suppliers = await res.json();
            }
          } catch(e) { console.error(e); }
        },

        onSupplierSelect() {
          const sup = this.suppliers.find(s => s.id === parseInt(this.selectedSupplierId));
          if (sup) {
            this.selectedSupplierObj = sup;
            this.form.beneficiary = (sup.rif ? sup.rif + ' - ' : '') + sup.name;
          } else {
            this.selectedSupplierObj = null;
          }
        },

        openSupplierModal() {
          this.newSupplierForm = { name: '', rif: '', phone: '', bank_details: '' };
          this.showSupplierModal = true;
        },

        async saveNewSupplier() {
          if (!this.newSupplierForm.name.trim()) {
            alert('El nombre o razón social del proveedor es obligatorio.');
            return;
          }
          const token = this.getToken();
          const res = await fetch('/api/suppliers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(this.newSupplierForm)
          });
          if (res.ok) {
            const created = await res.json();
            await this.loadSuppliers();
            this.selectedSupplierId = created.id;
            this.onSupplierSelect();
            this.showSupplierModal = false;
            this.showToast('success', 'Proveedor Registrado', `Proveedor '${created.name}' guardado exitosamente.`);
          } else {
            const err = await res.json();
            alert(err.detail || 'Error al registrar proveedor');
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
