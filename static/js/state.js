// Estado Inicial Reactivo TEV Tesoreria
window.TEVState = {
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

};
