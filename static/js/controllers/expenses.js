// Modulo TEV: TEVExpenses
window.TEVExpenses = {
        toggleRetentionAssistant() {
          if (!this.retentionAssistant) {
            this.retentionAssistant = {
              active: false,
              total_invoice: '',
              tax_base: '',
              calc_iva: 0,
              iva_rate: 0.75,
              islr_rate: 0.0,
              ret_iva_amt: 0,
              ret_islr_amt: 0,
              total_retention: 0,
              net_to_pay: 0,
              proof_number: ''
            };
          }
          this.retentionAssistant.active = !this.retentionAssistant.active;
          if (this.retentionAssistant.active) {
            this.recalculateRetentions();
          } else {
            this.form.tax_retention_amount = 0;
            this.form.tax_retention_proof = '';
          }
        },

        recalculateRetentions(source = 'total') {
          if (!this.retentionAssistant || !this.retentionAssistant.active) return;
          
          let totalInv = parseFloat(String(this.retentionAssistant.total_invoice || '0').replace(',', '.')) || 0;
          let base = parseFloat(String(this.retentionAssistant.tax_base || '0').replace(',', '.')) || 0;
          
          if (source === 'total' && totalInv > 0) {
            // Deducción automática: Base = Total / 1.16
            base = Math.round((totalInv / 1.16) * 100) / 100;
            this.retentionAssistant.tax_base = base;
          } else if (source === 'base' && base > 0) {
            // Deducción automática: Total = Base * 1.16
            const calcIva = Math.round((base * 0.16) * 100) / 100;
            totalInv = Math.round((base + calcIva) * 100) / 100;
            this.retentionAssistant.total_invoice = totalInv;
          }
          
          // El IVA no puede ser mayor al 16% de la base ni exceder la diferencia
          const iva = Math.max(0, Math.round((totalInv - base) * 100) / 100);
          this.retentionAssistant.calc_iva = iva;
          
          // Retención IVA: Solo sobre el IVA facturado
          const retIva = Math.round((iva * (this.retentionAssistant.iva_rate || 0)) * 100) / 100;
          // Retención ISLR: Solo sobre la base imponible
          const retIslr = Math.round((base * (this.retentionAssistant.islr_rate || 0)) * 100) / 100;
          const totalRet = Math.round((retIva + retIslr) * 100) / 100;
          const netToPay = Math.max(0, Math.round((totalInv - totalRet) * 100) / 100);
          
          this.retentionAssistant.ret_iva_amt = retIva;
          this.retentionAssistant.ret_islr_amt = retIslr;
          this.retentionAssistant.total_retention = totalRet;
          this.retentionAssistant.net_to_pay = netToPay;
          
          if (netToPay > 0) {
            this.form.amount_original = netToPay;
            this.recalculateExpenseUsd('original');
          }
        },

        toggleDiscountAssistant() {
          if (!this.discountAssistant) {
            this.discountAssistant = {
              active: false,
              total_invoice: '',
              discount_type: 'percent',
              discount_value: '',
              discount_amount: 0,
              net_to_pay: 0
            };
          }
          this.discountAssistant.active = !this.discountAssistant.active;
          if (this.discountAssistant.active) {
            this.recalculateDiscount();
          }
        },

        recalculateDiscount() {
          if (!this.discountAssistant || !this.discountAssistant.active) return;
          const tot = parseFloat(String(this.discountAssistant.total_invoice || '0').replace(',', '.')) || 0;
          const val = parseFloat(String(this.discountAssistant.discount_value || '0').replace(',', '.')) || 0;
          let discAmt = 0;
          if (this.discountAssistant.discount_type === 'percent') {
            discAmt = Math.round(tot * (val / 100) * 100) / 100;
          } else {
            discAmt = Math.min(tot, val);
          }
          const net = Math.max(0, Math.round((tot - discAmt) * 100) / 100);
          this.discountAssistant.discount_amount = discAmt;
          this.discountAssistant.net_to_pay = net;
          if (net > 0) {
            this.form.amount_original = net;
            this.recalculateExpenseUsd('original');
          }
        },

        recalculateExpenseUsd(fromField = 'original') {
          const rate = parseFloat(this.form.exchange_rate) || parseFloat(this.bcvRate) || 1.0;
          if (this.selectedAccountCurrency === 'VES') {
            if (fromField === 'original') {
              const orig = parseFloat(String(this.form.amount_original || '0').replace(',', '.')) || 0;
              this.form.amount_usd = Math.round((orig / rate) * 100) / 100;
            } else if (fromField === 'usd') {
              const usd = parseFloat(String(this.form.amount_usd || '0').replace(',', '.')) || 0;
              this.form.amount_original = Math.round((usd * rate) * 100) / 100;
            }
          } else {
            const orig = parseFloat(String(this.form.amount_original || '0').replace(',', '.')) || 0;
            this.form.amount_usd = orig;
          }
        },

        async submitMovement() {
          if (this.isSubmittingMovement) return;

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
              this.isSubmittingMovement = false;
              return;
            }
            this.transferForm.source_account_id = this.form.account_id;
            this.transferForm.destination_account_id = this.form.destination_account_id;
            this.transferForm.source_amount = this.form.amount_original;
            this.transferForm.date = this.form.date;
            this.transferForm.reference_number = this.form.reference_number;
            this.transferForm.description = this.form.description || 'Traspaso entre cuentas';
            try {
              await this.executeTransfer();
            } finally {
              this.isSubmittingMovement = false;
            }
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
          if (this.isSubmittingMovement) return;
          this.isSubmittingMovement = true;
          this.showConfirmModal = false;
          try {
            const token = this.getToken();
            if (!token) {
              this.showToast('error', 'Sesión Expirada', 'Su sesión ha expirado. Por favor inicie sesión nuevamente.');
              return;
            }

            const currentAcc = (this.accounts || []).find(a => a.id == this.form.account_id);
            const curr = (currentAcc && currentAcc.currency) || this.selectedAccountCurrency || 'USD';

            // Confirmación previa de seguridad (evita guardado accidental por presionar Enter)
            const subLabel = (this.form.subtype || '').replace(/_/g, ' ');
            const confMsg = `¿Confirma registrar este movimiento (${subLabel})?\n\n• Beneficiario / Proveedor: ${this.form.beneficiary || 'N/A'}\n• Monto: ${curr} ${this.form.amount_original}\n• Concepto: ${this.form.description || 'Sin descripción'}`;
            if (!confirm(confMsg)) {
              this.isSubmittingMovement = false;
              return;
            }

            const isRetActive = this.retentionAssistant && this.retentionAssistant.active;
            const retAmt = isRetActive ? (this.retentionAssistant.total_retention || 0) : 0;
            const retProof = isRetActive ? (this.retentionAssistant.proof_number || '') : '';
            
            let extraDesc = '';
            if (isRetActive && retAmt > 0) {
              extraDesc += ` [Retención SENIAT: Factura: ${this.retentionAssistant.total_invoice} | Ret. IVA: ${this.retentionAssistant.ret_iva_amt} | Ret. ISLR: ${this.retentionAssistant.ret_islr_amt} | Neto Pagado: ${this.form.amount_original}]`;
            }
            const isDiscActive = this.discountAssistant && this.discountAssistant.active;
            if (isDiscActive && this.discountAssistant.discount_amount > 0) {
              const dLabel = this.discountAssistant.discount_type === 'percent' ? `${this.discountAssistant.discount_value}%` : `${this.discountAssistant.discount_value}`;
              extraDesc += ` [Descuento Pronto Pago: -${dLabel} (Monto: ${this.discountAssistant.discount_amount}) | Factura: ${this.discountAssistant.total_invoice} | Neto Pagado: ${this.form.amount_original}]`;
            }

            const finalRate = (curr === 'VES') ? (parseFloat(this.form.exchange_rate) || parseFloat(this.bcvRate) || 1.0) : 1.0;
            const finalUsd = (curr === 'VES') ? (parseFloat(this.form.amount_usd) || (Math.round((parseFloat(this.form.amount_original) / finalRate) * 100) / 100)) : parseFloat(this.form.amount_original);
            const savedDate = this.form.date;

            const payload = {
              date: this.form.date,
              movement_type: this.form.movement_type,
              subtype: this.form.subtype,
              account_id: this.form.account_id,
              category_id: this.form.category_id ? parseInt(this.form.category_id) : null,
              amount_original: parseFloat(this.form.amount_original),
              currency: curr,
              exchange_rate: finalRate,
              amount_usd: finalUsd,
              reference_number: this.form.reference_number || '',
              invoice_date: this.form.invoice_date || null,
              beneficiary: this.form.beneficiary || '',
              description: (this.form.description || '') + extraDesc,
              tax_retention_amount: retAmt,
              tax_retention_proof: retProof
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

            this.showToast('success', '¡Guardado Exitoso!', `El movimiento fue registrado correctamente para la fecha ${savedDate}.`);
            this.form.amount_original = '';
            this.form.amount_usd = 0;
            this.form.reference_number = '';
            this.form.beneficiary = '';
            this.form.description = '';
            
            if (this.retentionAssistant) {
              this.retentionAssistant.active = false;
              this.retentionAssistant.total_invoice = '';
              this.retentionAssistant.tax_base = '';
              this.retentionAssistant.calc_iva = 0;
              this.retentionAssistant.ret_iva_amt = 0;
              this.retentionAssistant.ret_islr_amt = 0;
              this.retentionAssistant.total_retention = 0;
              this.retentionAssistant.net_to_pay = 0;
              this.retentionAssistant.proof_number = '';
            }

            if (this.discountAssistant) {
              this.discountAssistant.active = false;
              this.discountAssistant.total_invoice = '';
              this.discountAssistant.discount_value = '';
              this.discountAssistant.discount_amount = 0;
              this.discountAssistant.net_to_pay = 0;
            }

            if (savedDate) {
              this.filterDate = savedDate;
            }

            await this.loadAccounts();
            await this.loadCategories();
            await this.loadTransactions();
            if (this.currentUser?.role === 'administradora' || this.currentUser?.role === 'directivo') {
              await this.loadCashFlowAll();
            }
          } catch (err) {
            this.showToast('error', 'Error en Registro', err.message);
          } finally {
            this.isSubmittingMovement = false;
          }
        },

        async executeTransfer() {
          if (this.isSubmittingMovement) return;
          this.isSubmittingMovement = true;
          try {
            const token = this.getToken();
            if (!token) {
              this.showToast('error', 'Sesión Expirada', 'Su sesión ha expirado. Por favor inicie sesión nuevamente.');
              return;
            }
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
          } finally {
            this.isSubmittingMovement = false;
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

        openEditTransactionModal(item) {
          this.editingTx = item;
          let baseDesc = item.description || '';

          // Detectar si ya tiene un descuento de pronto pago en la descripción
          const discRegex = /\[Descuento Pronto Pago:\s*-?([\d.]+)(%?)\s*\(Monto:\s*([\d.]+)\)\s*\|\s*Factura:\s*([\d.]+)\s*\|\s*Neto Pagado:\s*([\d.]+)\]/i;
          const match = baseDesc.match(discRegex);

          if (match) {
            this.editingTxDiscount = {
              active: true,
              discount_type: match[2] === '%' ? 'percent' : 'amount',
              discount_value: match[1],
              discount_amount: parseFloat(match[3]) || 0,
              total_invoice: match[4],
              net_to_pay: parseFloat(match[5]) || (item.amount_original || 0)
            };
            baseDesc = baseDesc.replace(discRegex, '').trim();
          } else {
            this.editingTxDiscount = {
              active: false,
              total_invoice: item.amount_original ? String(item.amount_original) : '',
              discount_type: 'percent',
              discount_value: '',
              discount_amount: 0,
              net_to_pay: item.amount_original || 0
            };
          }

          this.editingTxForm = {
            beneficiary: item.beneficiary || item.client_name || '',
            doc_number: item.doc_number || '',
            reference_number: item.reference_number || '',
            description: baseDesc,
            amount_original: item.amount_original || '',
            currency: item.currency || 'USD',
            account_id: item.account_id || '',
            category_id: item.category_id || '',
            edit_reason: ''
          };
          this.showEditTransactionModal = true;
        },

        toggleEditDiscountAssistant() {
          if (!this.editingTxDiscount) {
            this.editingTxDiscount = {
              active: false,
              total_invoice: this.editingTxForm.amount_original ? String(this.editingTxForm.amount_original) : '',
              discount_type: 'percent',
              discount_value: '',
              discount_amount: 0,
              net_to_pay: this.editingTxForm.amount_original || 0
            };
          }
          this.editingTxDiscount.active = !this.editingTxDiscount.active;
          if (this.editingTxDiscount.active) {
            if (!this.editingTxDiscount.total_invoice && this.editingTxForm.amount_original) {
              this.editingTxDiscount.total_invoice = String(this.editingTxForm.amount_original);
            }
            this.recalculateEditDiscount();
          }
        },

        recalculateEditDiscount() {
          if (!this.editingTxDiscount || !this.editingTxDiscount.active) return;
          const tot = parseFloat(String(this.editingTxDiscount.total_invoice || '0').replace(',', '.')) || 0;
          const val = parseFloat(String(this.editingTxDiscount.discount_value || '0').replace(',', '.')) || 0;
          let discAmt = 0;
          if (this.editingTxDiscount.discount_type === 'percent') {
            discAmt = Math.round(tot * (val / 100) * 100) / 100;
          } else {
            discAmt = Math.min(tot, val);
          }
          const net = Math.max(0, Math.round((tot - discAmt) * 100) / 100);
          this.editingTxDiscount.discount_amount = discAmt;
          this.editingTxDiscount.net_to_pay = net;
          if (net > 0) {
            this.editingTxForm.amount_original = net;
          }
        },

        async saveEditedTransaction() {
          if (!this.editingTx) return;
          if (!this.editingTxForm.edit_reason || !this.editingTxForm.edit_reason.trim()) {
            this.showToast('error', 'Motivo Obligatorio', 'Debe indicar obligatoriamente el motivo de la corrección para la bitácora de auditoría.');
            return;
          }
          this.isSavingEditTx = true;
          try {
            const token = this.getToken();

            let finalDesc = this.editingTxForm.description ? this.editingTxForm.description.trim() : '';
            finalDesc = finalDesc.replace(/\[Descuento Pronto Pago:[^\]]+\]/gi, '').trim();

            if (this.editingTxDiscount && this.editingTxDiscount.active && this.editingTxDiscount.discount_amount > 0) {
              const dLabel = this.editingTxDiscount.discount_type === 'percent' ? `${this.editingTxDiscount.discount_value}%` : `${this.editingTxDiscount.discount_value}`;
              finalDesc += ` [Descuento Pronto Pago: -${dLabel} (Monto: ${this.editingTxDiscount.discount_amount}) | Factura: ${this.editingTxDiscount.total_invoice} | Neto Pagado: ${this.editingTxForm.amount_original}]`;
            }

            const payload = {
              beneficiary: this.editingTxForm.beneficiary,
              doc_number: this.editingTxForm.doc_number,
              reference_number: this.editingTxForm.reference_number,
              description: finalDesc,
              amount_original: parseFloat(this.editingTxForm.amount_original) || this.editingTx.amount_original,
              currency: this.editingTxForm.currency || this.editingTx.currency,
              account_id: parseInt(this.editingTxForm.account_id) || this.editingTx.account_id,
              category_id: this.editingTxForm.category_id ? parseInt(this.editingTxForm.category_id) : this.editingTx.category_id,
              edit_reason: this.editingTxForm.edit_reason.trim()
            };
            const res = await fetch('/api/transactions/' + this.editingTx.id, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al actualizar');
            this.showToast('success', 'Movimiento Corregido', `Se corrigió el movimiento #${this.editingTx.id} con registro en auditoría.`);
            this.showEditTransactionModal = false;
            await this.loadTransactions();
            await this.loadAccounts();
            if (typeof this.loadLiveMonitor === 'function') {
              await this.loadLiveMonitor();
            }
            if (typeof this.loadSalesAccumulated === 'function') {
              await this.loadSalesAccumulated();
            }
            if (typeof this.loadDirectorKpis === 'function') {
              await this.loadDirectorKpis();
            }
          } catch (err) {
            this.showToast('error', 'Error al Guardar', err.message);
          } finally {
            this.isSavingEditTx = false;
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
            account_type: 'EFECTIVO',
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
            const payload = {
              name: this.newAccountForm.name.trim(),
              currency: this.newAccountForm.currency || 'USD',
              account_type: this.newAccountForm.account_type || 'EFECTIVO',
              initial_balance: parseFloat(this.newAccountForm.initial_balance) || 0.0,
              only_income: false
            };
            const res = await fetch('/api/accounts', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al crear la cuenta');

            this.showNewAccountModal = false;
            this.showToast('success', 'Caja Creada', `La cuenta "${data.name}" fue creada exitosamente`);
            await this.loadAccounts();
            await this.loadAllAccounts();
            if (this.form) {
              this.form.account_id = data.id;
              if (typeof this.onAccountChange === 'function') {
                try { this.onAccountChange(); } catch(e) {}
              }
            }
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        openEditAccountModal(acc) {
          if (!acc) return;
          this.editingAccount = {
            id: acc.id,
            name: acc.name || '',
            currency: acc.currency || 'USD',
            account_type: acc.account_type || 'EFECTIVO',
            initial_balance: acc.initial_balance !== undefined ? acc.initial_balance : 0.0,
            is_active: Boolean(acc.is_active)
          };
          this.showEditAccountModal = true;
        },

        async saveEditAccount() {
          if (!this.editingAccount || !this.editingAccount.id) return;
          const token = this.getToken();
          try {
            const payload = {
              name: this.editingAccount.name ? this.editingAccount.name.trim() : undefined,
              account_type: this.editingAccount.account_type || 'EFECTIVO',
              initial_balance: parseFloat(this.editingAccount.initial_balance) || 0.0,
              is_active: (this.editingAccount.is_active === true || this.editingAccount.is_active === 'true')
            };
            const res = await fetch('/api/accounts/' + this.editingAccount.id, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al actualizar');

            this.showEditAccountModal = false;
            this.showToast('success', 'Caja Actualizada', 'Los datos de la cuenta fueron guardados');
            await this.loadAccounts();
            await this.loadAllAccounts();
          } catch (err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        async toggleAccountStatus(acc) {
          if (!acc || !acc.id) return;
          const token = this.getToken();
          try {
            const res = await fetch(`/api/accounts/${acc.id}/toggle-status`, {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + token }
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al cambiar estado');
            this.showToast('success', 'Estado Actualizado', data.message);
            await this.loadAccounts();
            await this.loadAllAccounts();
          } catch(err) {
            this.showToast('error', 'Error', err.message);
          }
        },

        async loadAllAccounts() {
          const token = this.getToken();
          try {
            const res = await fetch('/api/accounts?all=true', {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            if (res.ok) {
              const list = await res.json();
              this.allAccountsList = list;
              if (!this.accounts || this.accounts.length === 0) {
                this.accounts = list.filter(a => a.is_active);
              }
            }
          } catch(err) {
            console.error('Error cargando cuentas completas:', err);
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
            let errMsg = 'Error al registrar proveedor';
            try {
              const err = await res.json();
              errMsg = err.detail || errMsg;
            } catch (e) {
              errMsg = `Error (${res.status}): ${res.statusText}`;
            }
            this.showToast('error', 'Error Proveedor', errMsg);
          }
        },

        openEditSupplierModal(sup) {
          const target = sup || this.selectedSupplierObj;
          if (!target) {
            this.showToast('error', 'Proveedor Requerido', 'Seleccione un proveedor para editar.');
            return;
          }
          this.editingSupplier = {
            id: target.id,
            name: target.name || '',
            rif: target.rif || '',
            phone: target.phone || '',
            bank_details: target.bank_details || '',
            is_active: target.is_active !== false
          };
          this.showEditSupplierModal = true;
        },

        async saveEditSupplier() {
          if (!this.editingSupplier || !this.editingSupplier.id) return;
          if (!this.editingSupplier.name.trim()) {
            this.showToast('error', 'Nombre Requerido', 'La razón social del proveedor es obligatoria.');
            return;
          }
          this.isSavingSupplier = true;
          try {
            const token = this.getToken();
            const res = await fetch('/api/suppliers/' + this.editingSupplier.id, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify({
                name: this.editingSupplier.name.trim(),
                rif: this.editingSupplier.rif ? this.editingSupplier.rif.trim() : null,
                phone: this.editingSupplier.phone ? this.editingSupplier.phone.trim() : null,
                bank_details: this.editingSupplier.bank_details ? this.editingSupplier.bank_details.trim() : '',
                is_active: this.editingSupplier.is_active
              })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Error al actualizar proveedor');
            await this.loadSuppliers();
            if (this.selectedSupplierId === this.editingSupplier.id) {
              this.onSupplierSelect();
            }
            this.showEditSupplierModal = false;
            this.showToast('success', 'Proveedor Actualizado', `Datos del proveedor '${data.name}' actualizados correctamente.`);
          } catch (err) {
            this.showToast('error', 'Error Proveedor', err.message);
          } finally {
            this.isSavingSupplier = false;
          }
        },

        openSupplierDirectory() {
          this.supplierSearchQuery = '';
          this.showSupplierDirectoryModal = true;
        },

        getFilteredSuppliers() {
          if (!this.suppliers || !Array.isArray(this.suppliers)) return [];
          const q = (this.supplierSearchQuery || '').toLowerCase().trim();
          if (!q) return this.suppliers;
          return this.suppliers.filter(s =>
            (s.name && s.name.toLowerCase().includes(q)) ||
            (s.rif && s.rif.toLowerCase().includes(q)) ||
            (s.phone && s.phone.toLowerCase().includes(q)) ||
            (s.bank_details && s.bank_details.toLowerCase().includes(q))
          );
        },

        getAvailableAccountsForForm() {
          if (!this.accounts || !Array.isArray(this.accounts)) return [];
          const seen = new Set();
          const uniqueAccounts = [];
          for (const a of this.accounts) {
            if (!a.is_active) continue;
            if (this.form && this.form.movement_type === 'EGRESO') {
              if (a.only_income || (a.name && a.name.toUpperCase().includes('CASHEA'))) {
                continue;
              }
            }
            const norm = (a.name || '').trim().toLowerCase();
            if (!seen.has(norm)) {
              seen.add(norm);
              uniqueAccounts.push(a);
            }
          }
          return uniqueAccounts;
        },

        getUniqueActiveAccounts() {
          if (!this.accounts || !Array.isArray(this.accounts)) return [];
          const seen = new Set();
          const unique = [];
          for (const a of this.accounts) {
            if (!a.is_active) continue;
            const norm = (a.name || '').trim().toLowerCase();
            if (!seen.has(norm)) {
              seen.add(norm);
              unique.push(a);
            }
          }
          return unique;
        },

        getAccountBalance(name) {
          if (!this.accounts || !Array.isArray(this.accounts)) return 0.0;
          const search = (name || '').trim().toLowerCase();
          const acc = this.accounts.find(a => 
            (a.name && a.name.toLowerCase() === search) ||
            (a.name && a.name.toLowerCase().includes(search))
          );
          return acc ? (acc.current_balance || 0.0) : 0.0;
        },

};
