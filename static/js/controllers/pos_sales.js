// Modulo TEV: TEVPosSales
window.TEVPosSales = {
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

};
