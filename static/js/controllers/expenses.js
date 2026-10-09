// Modulo TEV: TEVExpenses
window.TEVExpenses = {
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

};
