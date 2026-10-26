import React, { useState, useEffect } from 'react';
import { TrendingDown, CheckCircle2, Building2, Edit3, Trash2, X } from 'lucide-react';
import { useTreasury } from '../context/TreasuryContext';
import { useToast } from '../components/common/Toast';
import { api } from '../api/client';
import { Transaction } from '../types';
import { formatUSD, formatVES, getTodayDateString } from '../utils/formatters';

export const ExpensesPage: React.FC = () => {
  const { accounts, categories, suppliers, bcvRate, loadAccounts, loadSuppliers } = useTreasury();
  const { showToast } = useToast();

  const [date, setDate] = useState(getTodayDateString());
  const [subtype, setSubtype] = useState('GASTO_OPERATIVO');
  const categoryList = Array.isArray(categories) ? categories : [];
  const accountList = Array.isArray(accounts) ? accounts : [];
  const supplierList = Array.isArray(suppliers) ? suppliers : [];

  const [selectedSupplierId, setSelectedSupplierId] = useState<string>('');
  const [beneficiary, setBeneficiary] = useState('');
  const [categoryId, setCategoryId] = useState<number>(categoryList[0]?.id || 1);
  const [accountId, setAccountId] = useState<number>(accountList[0]?.id || 1);
  const [amountUsd, setAmountUsd] = useState('');
  const [docNumber, setDocNumber] = useState('');
  const [referenceNumber, setReferenceNumber] = useState('');
  const [description, setDescription] = useState('');

  // Retención SENIAT
  const [applyRetention, setApplyRetention] = useState(false);
  const [retentionAmount, setRetentionAmount] = useState('');
  const [retentionProof, setRetentionProof] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [recentExpenses, setRecentExpenses] = useState<Transaction[]>([]);
  const expenseList = Array.isArray(recentExpenses) ? recentExpenses : [];
  const [loadingExpenses, setLoadingExpenses] = useState(false);

  // Modal para nuevo proveedor rápido
  const [showSupplierModal, setShowSupplierModal] = useState(false);
  const [newSupName, setNewSupName] = useState('');
  const [newSupRif, setNewSupRif] = useState('');
  const [savingSup, setSavingSup] = useState(false);

  // Modal para corrección de error de dedo
  const [editingTx, setEditingTx] = useState<Transaction | null>(null);
  const [editBeneficiary, setEditBeneficiary] = useState('');
  const [editDocNumber, setEditDocNumber] = useState('');
  const [editReference, setEditReference] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    if (categoryList.length > 0 && !categoryId) {
      setCategoryId(categoryList[0].id);
    }
    if (accountList.length > 0 && !accountId) {
      const active = accountList.find((a) => a.is_active && !a.only_income) || accountList[0];
      if (active) setAccountId(active.id);
    }
  }, [categories, accounts, categoryId, accountId, categoryList, accountList]);

  const loadRecentExpenses = async () => {
    setLoadingExpenses(true);
    try {
      const data = await api.get<Transaction[]>(`/api/expenses?date=${date}`);
      if (Array.isArray(data)) {
        setRecentExpenses(data);
      } else {
        setRecentExpenses([]);
      }
    } catch (e) {
      console.error('Error al cargar egresos:', e);
    } finally {
      setLoadingExpenses(false);
    }
  };

  useEffect(() => {
    loadRecentExpenses();
  }, [date]);

  const handleSupplierChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const idStr = e.target.value;
    setSelectedSupplierId(idStr);
    const sup = supplierList.find((s) => s.id === parseInt(idStr));
    if (sup) {
      setBeneficiary(`${sup.rif ? sup.rif + ' - ' : ''}${sup.name}`);
    }
  };

  // Validación y formateo estricto del comprobante SENIAT (PB-01)
  const handleRetentionProofChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '').slice(0, 14);
    setRetentionProof(val);
  };

  const handleCreateSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSupName.trim()) {
      showToast('warning', 'Nombre Requerido', 'Indique la razón social del proveedor');
      return;
    }
    setSavingSup(true);
    try {
      const created = await api.post<any>('/api/suppliers', {
        name: newSupName.trim(),
        rif: newSupRif.trim() || null,
      });
      await loadSuppliers();
      setSelectedSupplierId(created.id.toString());
      setBeneficiary(`${created.rif ? created.rif + ' - ' : ''}${created.name}`);
      setShowSupplierModal(false);
      setNewSupName('');
      setNewSupRif('');
      showToast('success', 'Proveedor Guardado', `"${created.name}" fue agregado`);
    } catch (err: any) {
      showToast('error', 'Error Proveedor', err.message || 'No se pudo guardar');
    } finally {
      setSavingSup(false);
    }
  };

  const handleOpenEdit = (tx: Transaction) => {
    setEditingTx(tx);
    setEditBeneficiary(tx.beneficiary || '');
    setEditDocNumber(tx.doc_number || '');
    setEditReference(tx.reference_number || '');
    setEditDescription(tx.description || '');
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTx) return;
    setSavingEdit(true);
    try {
      await api.patch(`/api/transactions/${editingTx.id}`, {
        beneficiary: editBeneficiary.trim(),
        doc_number: editDocNumber.trim() || null,
        reference_number: editReference.trim() || null,
        description: editDescription.trim() || null,
      });
      showToast('success', 'Movimiento Corregido', `Se actualizaron los datos del registro #${editingTx.id}`);
      setEditingTx(null);
      await loadRecentExpenses();
    } catch (err: any) {
      showToast('error', 'Error al Corregir', err.message || 'No se pudo actualizar');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleVoidExpense = async (txId: number) => {
    if (!confirm('¿Confirma que desea anular este egreso? El monto se revertirá en el saldo de la cuenta.')) {
      return;
    }
    try {
      await api.delete(`/api/transactions/${txId}`);
      showToast('success', 'Egreso Anulado', `El movimiento #${txId} fue anulado`);
      await loadAccounts();
      await loadRecentExpenses();
    } catch (err: any) {
      showToast('error', 'Error al Anular', err.message || 'No se pudo anular el egreso');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(amountUsd);
    if (isNaN(amount) || amount <= 0) {
      showToast('warning', 'Monto Requerido', 'El monto debe ser mayor a $0.00');
      return;
    }
    if (!beneficiary.trim()) {
      showToast('warning', 'Beneficiario Requerido', 'Indique el beneficiario o seleccione un proveedor');
      return;
    }

    if (applyRetention) {
      if (retentionProof.length !== 14) {
        showToast(
          'warning',
          'Comprobante SENIAT Inválido',
          'El comprobante debe tener exactamente 14 dígitos (YYYYMMXXXXXXXX)'
        );
        return;
      }
      const retAmt = parseFloat(retentionAmount);
      if (isNaN(retAmt) || retAmt <= 0) {
        showToast('warning', 'Retención Inválida', 'Indique el monto de la retención');
        return;
      }
    }

    setSubmitting(true);
    try {
      await api.post('/api/expenses', {
        date,
        category_id: categoryId,
        account_id: accountId,
        amount_usd: amount,
        currency: 'USD',
        exchange_rate: bcvRate,
        subtype,
        beneficiary: beneficiary.trim(),
        reference_number: referenceNumber.trim() || null,
        doc_number: docNumber.trim() || null,
        description: description.trim() || null,
        tax_retention_amount: applyRetention ? parseFloat(retentionAmount) || 0 : 0,
        tax_retention_proof: applyRetention ? retentionProof : null,
      });

      showToast('success', 'Egreso Registrado', `Se registraron ${formatUSD(amount)} para ${beneficiary}`);

      // Reset
      setAmountUsd('');
      setDocNumber('');
      setReferenceNumber('');
      setDescription('');
      setApplyRetention(false);
      setRetentionAmount('');
      setRetentionProof('');

      await loadAccounts();
      await loadRecentExpenses();
    } catch (err: any) {
      showToast('error', 'Error al Guardar Egreso', err.message || 'No se pudo registrar');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
              <TrendingDown className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg sm:text-xl font-black text-gray-900">
                Registro de Egresos & Control Fiscal
              </h2>
              <p className="text-xs text-gray-500">
                Pagos operativos, proveedores y retenciones oficiales SENIAT
              </p>
            </div>
          </div>
          <span className="text-xs font-bold text-gray-400 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200">
            Tasa: {formatVES(bcvRate)}
          </span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Fila 1: Subtipo, Fecha y Categoría */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Subtipo de Egreso: *</label>
              <select
                value={subtype}
                onChange={(e) => setSubtype(e.target.value)}
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              >
                <option value="GASTO_OPERATIVO">🏢 Gasto Operativo / Administrativo</option>
                <option value="PAGO_PROVEEDOR">🏭 Pago a Proveedor de Mercancía</option>
                <option value="VALE_CAJA">🧾 Vale de Caja / Gasto Menor</option>
                <option value="RETIRO_ACCIONISTA">👤 Retiro de Socios / Accionistas</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Fecha del Egreso: *</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Partida Presupuestaria: *</label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(parseInt(e.target.value))}
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              >
                {categoryList.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Fila 2: Proveedor / Beneficiario */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-bold text-gray-700">Seleccionar Proveedor Registrado:</label>
                <button
                  type="button"
                  onClick={() => setShowSupplierModal(true)}
                  className="text-[11px] font-bold text-tev-green hover:underline flex items-center gap-1"
                >
                  <Building2 className="w-3 h-3" />
                  <span>+ Nuevo Proveedor</span>
                </button>
              </div>
              <select
                value={selectedSupplierId}
                onChange={handleSupplierChange}
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              >
                <option value="">-- Escribir beneficiario libre o elegir proveedor --</option>
                {supplierList.map((sup) => (
                  <option key={sup.id} value={sup.id}>
                    {sup.name} {sup.rif ? `(${sup.rif})` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">
                Beneficiario / Razón Social: *
              </label>
              <input
                type="text"
                value={beneficiary}
                onChange={(e) => setBeneficiary(e.target.value)}
                required
                placeholder="Ej: J-30491823-1 Corp Elecon"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              />
            </div>
          </div>

          {/* Fila 3: Monto y Cuenta Pagadora */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 bg-rose-50/70 border border-rose-200 rounded-2xl space-y-1">
              <label className="block text-xs font-black text-rose-950 uppercase">
                Monto del Egreso ($ USD): *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amountUsd}
                onChange={(e) => setAmountUsd(e.target.value)}
                required
                placeholder="0.00"
                className="w-full p-2.5 border border-rose-300 rounded-xl text-xl font-black text-rose-950 bg-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">
                Cuenta / Caja Pagadora (Débito): *
              </label>
              <select
                value={accountId}
                onChange={(e) => setAccountId(parseInt(e.target.value))}
                className="w-full p-3 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              >
                {accountList.filter(a => a.is_active && !a.only_income).map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({acc.currency}) - Saldo Disponible: {formatUSD(acc.current_balance)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Fila 4: N° Factura / Referencia */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">N° de Factura / Soporte Físico:</label>
              <input
                type="text"
                value={docNumber}
                onChange={(e) => setDocNumber(e.target.value)}
                placeholder="Ej: Factura #8042"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">N° de Transferencia / Referencia:</label>
              <input
                type="text"
                value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                placeholder="Ej: Ref Banesco #9012"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
              />
            </div>
          </div>

          {/* Fila 5: Retención SENIAT (Validación de 14 dígitos PB-01) */}
          <div className="p-4 bg-amber-50/60 border border-amber-200 rounded-2xl space-y-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={applyRetention}
                onChange={(e) => setApplyRetention(e.target.checked)}
                className="w-4 h-4 text-amber-700 rounded border-gray-300 focus:ring-amber-600"
              />
              <span className="text-xs font-black text-amber-950">
                ¿Aplica Retención Oficial SENIAT (IVA o ISLR)?
              </span>
            </label>

            {applyRetention && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-amber-200">
                <div>
                  <label className="block text-xs font-bold text-amber-950 mb-1">
                    Monto Retenido ($ USD): *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={retentionAmount}
                    onChange={(e) => setRetentionAmount(e.target.value)}
                    required={applyRetention}
                    placeholder="0.00"
                    className="w-full p-2 border border-amber-300 rounded-xl text-sm font-bold bg-white focus:outline-none"
                  />
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs font-bold text-amber-950">
                      N° de Comprobante (14 Dígitos): *
                    </label>
                    <span className="text-[10px] font-bold text-gray-500">
                      {retentionProof.length}/14
                    </span>
                  </div>
                  <input
                    type="text"
                    value={retentionProof}
                    onChange={handleRetentionProofChange}
                    required={applyRetention}
                    maxLength={14}
                    placeholder="20260900000001"
                    className="w-full p-2 border border-amber-300 rounded-xl text-xs font-mono font-bold tracking-wider bg-white focus:outline-none"
                  />
                  <p className="text-[10px] text-gray-500 mt-1">
                    Estructura: Año (4) + Mes (2) + Secuencia (8). Formato: YYYYMMXXXXXXXX
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Botón Guardar con Spinner (Anti-Doble Clic PB-02) */}
          <div className="pt-3 border-t border-gray-100 flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="w-full sm:w-auto px-8 py-3 bg-rose-700 hover:bg-rose-800 text-white font-black rounded-xl shadow-lg transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle2 className="w-5 h-5" />
              <span>{submitting ? 'Procesando Egreso...' : '💾 Registrar Egreso en Tesorería'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Historial de Egresos */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-4">
          <h3 className="text-base font-black text-gray-900">
            Egresos Registrados ({date})
          </h3>
          <span className="text-xs font-bold text-gray-500">
            {recentExpenses.length} movimientos
          </span>
        </div>

        {loadingExpenses ? (
          <p className="text-xs text-gray-400 py-4 text-center">Cargando egresos...</p>
        ) : recentExpenses.length === 0 ? (
          <p className="text-xs text-gray-400 py-8 text-center">
            No se han registrado egresos en la fecha seleccionada.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-gray-600 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Beneficiario</th>
                  <th className="p-3">Categoría</th>
                  <th className="p-3">Subtipo</th>
                  <th className="p-3 text-right">Monto USD</th>
                  <th className="p-3 text-center">Estado</th>
                  <th className="p-3 text-center">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {expenseList.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50/50 transition">
                    <td className="p-3 font-bold text-gray-900">
                      <div>{tx.beneficiary}</div>
                      {tx.reference_number && (
                        <div className="text-[10px] text-gray-400 font-normal">Ref: {tx.reference_number}</div>
                      )}
                    </td>
                    <td className="p-3 text-gray-600">{tx.category_name || 'General'}</td>
                    <td className="p-3 text-gray-500">{tx.subtype?.replace('GASTO_', '')}</td>
                    <td className="p-3 text-right font-black text-rose-700">
                      -{formatUSD(tx.amount_usd)}
                    </td>
                    <td className="p-3 text-center">
                      <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        {tx.status}
                      </span>
                    </td>
                    <td className="p-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(tx)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                          title="Corregir datos de texto (error de dedo)"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleVoidExpense(tx.id)}
                          className="p-1.5 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                          title="Anular egreso y revertir saldo"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Nuevo Proveedor */}
      {showSupplierModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl p-6 max-w-sm w-full space-y-4">
            <h3 className="text-base font-black text-gray-900">Registrar Nuevo Proveedor</h3>
            <form onSubmit={handleCreateSupplier} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Razón Social: *</label>
                <input
                  type="text"
                  value={newSupName}
                  onChange={(e) => setNewSupName(e.target.value)}
                  required
                  placeholder="Ej: Materiales Eléctricos Carabobo"
                  className="w-full p-2 border border-gray-300 rounded-xl text-xs bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">RIF:</label>
                <input
                  type="text"
                  value={newSupRif}
                  onChange={(e) => setNewSupRif(e.target.value)}
                  placeholder="Ej: J-40892019-1"
                  className="w-full p-2 border border-gray-300 rounded-xl text-xs bg-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowSupplierModal(false)}
                  className="px-3 py-1.5 text-xs text-gray-600 rounded-lg hover:bg-gray-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={savingSup}
                  className="px-4 py-1.5 bg-tev-green text-white text-xs font-bold rounded-lg shadow-sm"
                >
                  {savingSup ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Corrección de Error de Dedo */}
      {editingTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-gray-100">
              <div>
                <h3 className="text-base font-black text-gray-900">✏️ Corregir Datos de Egreso #{editingTx.id}</h3>
                <p className="text-[11px] text-gray-500">Subsanar errores de tipeo en proveedor, documento o referencia</p>
              </div>
              <button type="button" onClick={() => setEditingTx(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Beneficiario / Proveedor: *</label>
                <input
                  type="text"
                  value={editBeneficiary}
                  onChange={(e) => setEditBeneficiary(e.target.value)}
                  required
                  className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">N° Documento / Factura:</label>
                  <input
                    type="text"
                    value={editDocNumber}
                    onChange={(e) => setEditDocNumber(e.target.value)}
                    className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">N° Referencia Bancaria:</label>
                  <input
                    type="text"
                    value={editReference}
                    onChange={(e) => setEditReference(e.target.value)}
                    className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Concepto / Detalle:</label>
                <input
                  type="text"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setEditingTx(null)}
                  className="px-4 py-2 text-xs font-bold text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={savingEdit}
                  className="px-5 py-2 bg-tev-green hover:bg-tev-darkgreen text-white text-xs font-bold rounded-xl shadow-sm transition"
                >
                  {savingEdit ? 'Guardando...' : 'Guardar Corrección'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
