import React, { useState } from 'react';
import { X, Save } from 'lucide-react';
import { CreditRecord } from '../../types';
import { useTreasury } from '../../context/TreasuryContext';
import { useToast } from '../common/Toast';
import { api } from '../../api/client';
import { formatNumber, formatUSD, formatVES, getTodayDateString } from '../../utils/formatters';

interface AbonoCxcModalProps {
  credit: CreditRecord | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const AbonoCxcModal: React.FC<AbonoCxcModalProps> = ({ credit, onClose, onSuccess }) => {
  const { accounts, bcvRate, loadAccounts } = useTreasury();
  const { showToast } = useToast();

  const [amountUsd, setAmountUsd] = useState<string>('');
  const [accountId, setAccountId] = useState<number>(accounts[0]?.id || 0);
  const [date, setDate] = useState<string>(getTodayDateString());
  const [referenceNumber, setReferenceNumber] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  if (!credit) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(amountUsd);
    if (isNaN(amount) || amount <= 0) {
      showToast('warning', 'Monto Requerido', 'Ingrese un monto mayor a 0');
      return;
    }
    if (amount > credit.pending_balance_usd + 0.001) {
      showToast('warning', 'Monto Excedido', `El abono no puede superar el saldo pendiente (${formatUSD(credit.pending_balance_usd)})`);
      return;
    }
    if (!accountId) {
      showToast('warning', 'Cuenta Requerida', 'Seleccione la caja o banco receptora');
      return;
    }

    setLoading(true);
    try {
      await api.post('/api/cxc/payments', {
        transaction_id: credit.sale_id || credit.id,
        amount_usd: amount,
        account_id: accountId,
        payment_method: 'ABONO_CXC',
        exchange_rate: bcvRate,
        reference_number: referenceNumber || null,
        description: description || `Abono a ${credit.doc_type} #${credit.doc_number}`,
      });

      showToast('success', 'Abono Procesado', `Se registraron ${formatUSD(amount)} a favor de ${credit.client_name}`);
      await loadAccounts();
      onSuccess();
      onClose();
    } catch (err: any) {
      showToast('error', 'Error en Abono', err.message || 'No se pudo registrar el abono');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto no-print">
      <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full p-6 sm:p-8 space-y-5 border border-gray-100">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div>
            <h3 className="text-lg font-black text-gray-900">
              {credit.is_cashea ? '📥 Liquidar Saldo Cashea' : '➕ Registrar Abono a CxC'}
            </h3>
            <p className="text-xs text-gray-500">Ingrese el pago para rebajar la deuda y sumar a caja/banco</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 font-bold p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Resumen Deuda */}
        <div
          className={`p-4 rounded-2xl border space-y-2 ${
            credit.is_cashea ? 'bg-amber-50/80 border-amber-200' : 'bg-purple-50/80 border-purple-200'
          }`}
        >
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-600 font-semibold">Documento / Venta:</span>
            <strong className="text-gray-900">{credit.doc_type} #{credit.doc_number}</strong>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-600 font-semibold">Deudor:</span>
            <strong className="text-gray-900">{credit.client_name}</strong>
          </div>
          <div className="flex justify-between items-center text-xs pt-1 border-t border-gray-200/60">
            <span className="text-gray-600 font-semibold">Monto Original:</span>
            <span className="font-bold text-gray-800">{formatUSD(credit.original_amount_usd)}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-emerald-700 font-semibold">Total Ya Abonado:</span>
            <span className="font-bold text-emerald-700">{formatUSD(credit.total_abonado_usd)}</span>
          </div>
          <div className="flex justify-between items-center text-sm pt-1 border-t border-gray-200 font-black">
            <span className="text-rose-700">Saldo Pendiente:</span>
            <span className="text-rose-700">
              {formatUSD(credit.pending_balance_usd)} ({formatVES(credit.pending_balance_usd * bcvRate)})
            </span>
          </div>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">Monto a Abonar ($ USD): *</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max={credit.pending_balance_usd}
                value={amountUsd}
                onChange={(e) => setAmountUsd(e.target.value)}
                required
                placeholder="Ej: 50.00"
                className="w-full p-2.5 border border-purple-300 rounded-xl text-sm font-black text-purple-950 bg-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">Fecha del Abono: *</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-800 mb-1">¿A qué Caja o Banco ingresa el dinero?: *</label>
            <select
              value={accountId}
              onChange={(e) => setAccountId(parseInt(e.target.value))}
              required
              className="w-full p-2.5 border border-purple-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
            >
              {accounts.filter(a => a.is_active).map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.currency}) - Saldo: {formatUSD(acc.current_balance)}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">N° Referencia / Depósito:</label>
              <input
                type="text"
                value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                placeholder="Ej: Depósito #90421"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">Concepto / Detalle:</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Ej: Abono parcial en efectivo"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-bold text-gray-600 hover:bg-gray-100 rounded-xl transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`px-5 py-2.5 text-xs font-black rounded-xl shadow-md transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50 ${
                credit.is_cashea
                  ? 'bg-amber-500 hover:bg-amber-600 text-black'
                  : 'bg-purple-700 hover:bg-purple-800 text-white'
              }`}
            >
              <Save className="w-4 h-4" />
              <span>{loading ? 'Procesando...' : 'Confirmar y Registrar Abono'}</span>
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
