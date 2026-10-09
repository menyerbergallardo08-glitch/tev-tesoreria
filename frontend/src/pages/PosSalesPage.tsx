import React, { useState, useEffect } from 'react';
import { ShoppingCart, CheckCircle2, RotateCcw, AlertTriangle } from 'lucide-react';
import { useTreasury } from '../context/TreasuryContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/common/Toast';
import { api } from '../api/client';
import { Transaction } from '../types';
import { formatNumber, formatUSD, formatVES, getTodayDateString } from '../utils/formatters';

export const PosSalesPage: React.FC = () => {
  const { accounts, bcvRate, loadAccounts } = useTreasury();
  const { hasRole } = useAuth();
  const { showToast } = useToast();

  const [date, setDate] = useState(getTodayDateString());
  const [docType, setDocType] = useState<'NOTA_ENTREGA' | 'FACTURA_FISCAL'>('NOTA_ENTREGA');
  const [docNumber, setDocNumber] = useState('');
  const [clientName, setClientName] = useState('');
  const [clientRif, setClientRif] = useState('');
  const [amountUsd, setAmountUsd] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('EFECTIVO_USD');
  const [accountId, setAccountId] = useState<number>(accounts[0]?.id || 0);
  const [isCredit, setIsCredit] = useState(false);
  const [hasAbono, setHasAbono] = useState(false);
  const [abonoUsd, setAbonoUsd] = useState('');
  const [abonoAccountId, setAbonoAccountId] = useState<number>(accounts[0]?.id || 0);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [recentSales, setRecentSales] = useState<Transaction[]>([]);
  const [loadingSales, setLoadingSales] = useState(false);

  // Set default account when accounts load
  useEffect(() => {
    if (accounts.length > 0 && !accountId) {
      const defaultAcc = accounts.find((a) => a.is_active && a.currency === 'USD') || accounts[0];
      setAccountId(defaultAcc.id);
      setAbonoAccountId(defaultAcc.id);
    }
  }, [accounts, accountId]);

  const loadRecentSales = async () => {
    setLoadingSales(true);
    try {
      const data = await api.get<Transaction[]>(`/api/sales?date=${date}`);
      setRecentSales(data);
    } catch (e) {
      console.error('Error al cargar ventas:', e);
    } finally {
      setLoadingSales(false);
    }
  };

  useEffect(() => {
    loadRecentSales();
  }, [date]);

  const totalUsdNum = parseFloat(amountUsd) || 0;
  const totalVesEquiv = totalUsdNum * bcvRate;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docNumber.trim()) {
      showToast('warning', 'Documento Requerido', 'Ingrese el número de factura o nota de entrega');
      return;
    }
    if (totalUsdNum <= 0) {
      showToast('warning', 'Monto Requerido', 'El monto de venta debe ser mayor a $0.00');
      return;
    }

    const abonoNum = hasAbono && isCredit ? parseFloat(abonoUsd) || 0 : 0;
    if (isCredit && hasAbono && abonoNum >= totalUsdNum) {
      showToast('warning', 'Monto Inconsistente', 'El abono inicial debe ser menor al total en ventas a crédito');
      return;
    }

    setSubmitting(true);
    try {
      await api.post('/api/sales', {
        date,
        doc_type: docType,
        doc_number: docNumber.trim(),
        client_name: clientName.trim() || 'Cliente Mostrador',
        client_rif: clientRif.trim() || null,
        amount_usd: totalUsdNum,
        payment_method: paymentMethod,
        account_id: isCredit ? null : accountId,
        exchange_rate: bcvRate,
        amount_ves: totalVesEquiv,
        is_credit: isCredit,
        abono_usd: abonoNum,
        abono_account_id: abonoNum > 0 ? abonoAccountId : null,
        reference_number: referenceNumber.trim() || null,
        description: notes.trim() || null,
      });

      showToast(
        'success',
        'Venta Registrada',
        `${docType} #${docNumber} registrada exitosamente por ${formatUSD(totalUsdNum)}`
      );

      // Reset form
      setDocNumber('');
      setAmountUsd('');
      setAbonoUsd('');
      setHasAbono(false);
      setIsCredit(false);
      setReferenceNumber('');
      setNotes('');

      await loadAccounts();
      await loadRecentSales();
    } catch (err: any) {
      showToast('error', 'Error al Guardar Venta', err.message || 'No se pudo registrar la venta');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVoidSale = async (txId: number) => {
    const reason = prompt('Indique el motivo de la anulación:');
    if (!reason) return;

    try {
      await api.post('/api/sales/void', {
        transaction_id: txId,
        reason,
      });
      showToast('success', 'Venta Anulada', 'La transacción fue revertida en tesorería');
      await loadAccounts();
      await loadRecentSales();
    } catch (err: any) {
      showToast('error', 'Error al Anular', err.message || 'No se pudo anular');
    }
  };

  return (
    <div className="space-y-6">
      {/* Tarjeta de Registro de Ventas */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-tev-green/10 text-tev-green flex items-center justify-center font-bold">
              <ShoppingCart className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg sm:text-xl font-black text-gray-900">
                Punto de Venta & Facturación
              </h2>
              <p className="text-xs text-gray-500">
                Registro de cobro de contado, crédito o venta con abono inicial
              </p>
            </div>
          </div>
          <span className="text-xs font-bold text-gray-400 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200">
            Tasa: {formatVES(bcvRate)}
          </span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Fila 1: Documento y Fecha */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Tipo de Documento: *</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value as any)}
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              >
                <option value="NOTA_ENTREGA">📦 Nota de Entrega</option>
                <option value="FACTURA_FISCAL">🧾 Factura Fiscal (IVA)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">N° de Documento: *</label>
              <input
                type="text"
                value={docNumber}
                onChange={(e) => setDocNumber(e.target.value)}
                required
                placeholder="Ej: NE-4921 o FAC-1002"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Fecha de Emisión: *</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:outline-none"
              />
            </div>
          </div>

          {/* Fila 2: Cliente y RIF */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Nombre del Cliente:</label>
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="Ej: Distribuidora Eléctrica Central"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">RIF / Cédula:</label>
              <input
                type="text"
                value={clientRif}
                onChange={(e) => setClientRif(e.target.value)}
                placeholder="Ej: J-12345678-9 o V-18492019"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              />
            </div>
          </div>

          {/* Fila 3: Monto USD y Conversión VES */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-2xl space-y-1">
              <label className="block text-xs font-black text-emerald-950 uppercase">
                Monto Total de la Venta ($ USD): *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amountUsd}
                onChange={(e) => setAmountUsd(e.target.value)}
                required
                placeholder="0.00"
                className="w-full p-2.5 border border-emerald-300 rounded-xl text-xl font-black text-emerald-950 bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>

            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex flex-col justify-center">
              <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wide">
                Equivalente al BCV Oficial:
              </span>
              <span className="text-xl font-black text-gray-900 mt-1">
                {formatVES(totalVesEquiv)}
              </span>
              <span className="text-[10px] text-gray-400">Calculado a Bs. {formatNumber(bcvRate)}</span>
            </div>
          </div>

          {/* Fila 4: Opción Crédito vs Contado */}
          <div className="p-4 bg-purple-50/50 border border-purple-200 rounded-2xl space-y-3">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={isCredit}
                onChange={(e) => setIsCredit(e.target.checked)}
                className="w-4 h-4 text-purple-700 rounded border-gray-300 focus:ring-purple-600"
              />
              <span className="text-xs font-black text-purple-950">
                ¿Es una Venta a Crédito? (Se registrará en Cuentas por Cobrar sin inflar la caja)
              </span>
            </label>

            {isCredit && (
              <div className="pl-6 space-y-3 pt-2 border-t border-purple-200">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasAbono}
                    onChange={(e) => setHasAbono(e.target.checked)}
                    className="w-4 h-4 text-purple-700 rounded border-gray-300 focus:ring-purple-600"
                  />
                  <span className="text-xs font-semibold text-purple-900">
                    El cliente realiza un abono o anticipo inicial hoy
                  </span>
                </label>

                {hasAbono && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-xs font-bold text-purple-950 mb-1">
                        Monto del Abono Inicial ($ USD):
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0.01"
                        max={totalUsdNum - 0.01}
                        value={abonoUsd}
                        onChange={(e) => setAbonoUsd(e.target.value)}
                        placeholder="0.00"
                        className="w-full p-2 border border-purple-300 rounded-xl text-sm font-bold bg-white focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-purple-950 mb-1">
                        Caja o Banco Receptora del Abono:
                      </label>
                      <select
                        value={abonoAccountId}
                        onChange={(e) => setAbonoAccountId(parseInt(e.target.value))}
                        className="w-full p-2 border border-purple-300 rounded-xl text-xs font-bold bg-white focus:outline-none"
                      >
                        {accounts.filter(a => a.is_active).map((acc) => (
                          <option key={acc.id} value={acc.id}>
                            {acc.name} ({acc.currency})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Fila 5: Forma de Pago y Cuenta Receptora (si es contado) */}
          {!isCredit && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Forma de Pago: *</label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
                >
                  <option value="EFECTIVO_USD">💵 Efectivo Divisas ($ USD)</option>
                  <option value="EFECTIVO_VES">🇻🇪 Efectivo Bolívares (VES)</option>
                  <option value="PUNTO_VENTA_POS">💳 Punto de Venta (Tarjeta)</option>
                  <option value="PAGO_MOVIL">📲 Pago Móvil / Transferencia</option>
                  <option value="CASHEA">🟡 Cashea</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Caja o Cuenta Receptora: *</label>
                <select
                  value={accountId}
                  onChange={(e) => setAccountId(parseInt(e.target.value))}
                  className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
                >
                  {accounts.filter(a => a.is_active).map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.currency}) - Saldo: {formatUSD(acc.current_balance)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Fila 6: Referencia y Notas */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">N° Referencia / Lote POS:</label>
              <input
                type="text"
                value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                placeholder="Ej: Lote 0482 o Ref 98402"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Notas / Observaciones:</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Ej: Entrega de cables y lámparas LED"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
              />
            </div>
          </div>

          {/* Botón Guardar con Spinner (Anti-Doble Clic PB-02) */}
          <div className="pt-3 border-t border-gray-100 flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="w-full sm:w-auto px-8 py-3 bg-tev-green hover:bg-tev-darkgreen text-white font-black rounded-xl shadow-lg transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle2 className="w-5 h-5" />
              <span>{submitting ? 'Procesando Venta...' : '💾 Registrar Venta en Sistema'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Historial de Ventas del Día */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-4">
          <h3 className="text-base font-black text-gray-900">
            Ventas Registradas del Día ({date})
          </h3>
          <span className="text-xs font-bold text-gray-500">
            {recentSales.length} operaciones
          </span>
        </div>

        {loadingSales ? (
          <p className="text-xs text-gray-400 py-4 text-center">Cargando movimientos...</p>
        ) : recentSales.length === 0 ? (
          <p className="text-xs text-gray-400 py-8 text-center">
            No se han registrado ventas en la fecha seleccionada.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-gray-600 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Doc</th>
                  <th className="p-3">Cliente</th>
                  <th className="p-3">Tipo / Canal</th>
                  <th className="p-3 text-right">Monto USD</th>
                  <th className="p-3 text-center">Estado</th>
                  {hasRole(['administradora', 'directivo']) && (
                    <th className="p-3 text-center">Acciones</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recentSales.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50/50 transition">
                    <td className="p-3 font-bold text-gray-900">
                      {tx.doc_type || 'VENTA'} #{tx.doc_number || tx.reference_number || tx.id}
                    </td>
                    <td className="p-3 text-gray-700">{tx.beneficiary || 'Cliente Mostrador'}</td>
                    <td className="p-3 text-gray-500">
                      {tx.subtype?.replace('VENTA_', '')}
                    </td>
                    <td className="p-3 text-right font-black text-gray-900">
                      {formatUSD(tx.amount_usd)}
                    </td>
                    <td className="p-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          tx.status === 'ANULADO'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {tx.status}
                      </span>
                    </td>
                    {hasRole(['administradora', 'directivo']) && (
                      <td className="p-3 text-center">
                        {tx.status !== 'ANULADO' && (
                          <button
                            type="button"
                            onClick={() => handleVoidSale(tx.id)}
                            className="p-1 text-gray-400 hover:text-rose-600 rounded-lg transition"
                            title="Anular venta"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
