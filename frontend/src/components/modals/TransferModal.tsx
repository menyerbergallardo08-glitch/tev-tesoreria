import React, { useState } from 'react';
import { X, ArrowRightLeft, Save } from 'lucide-react';
import { useTreasury } from '../../context/TreasuryContext';
import { useToast } from '../common/Toast';
import { api } from '../../api/client';
import { formatUSD, getTodayDateString } from '../../utils/formatters';

interface TransferModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const TransferModal: React.FC<TransferModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { accounts, loadAccounts } = useTreasury();
  const { showToast } = useToast();

  const [originId, setOriginId] = useState<number>(accounts[0]?.id || 0);
  const [destId, setDestId] = useState<number>(accounts[1]?.id || accounts[0]?.id || 0);
  const [amountUsd, setAmountUsd] = useState('');
  const [date, setDate] = useState(getTodayDateString());
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  if (!isOpen) return null;

  const originAccount = accounts.find((a) => a.id === originId);
  const destAccount = accounts.find((a) => a.id === destId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (originId === destId) {
      showToast('warning', 'Cuentas Duplicadas', 'La cuenta origen y destino deben ser distintas');
      return;
    }
    const amount = parseFloat(amountUsd);
    if (isNaN(amount) || amount <= 0) {
      showToast('warning', 'Monto Requerido', 'Ingrese un monto a transferir mayor a 0');
      return;
    }

    setSaving(true);
    try {
      await api.post('/api/transfers', {
        date,
        origin_account_id: originId,
        destination_account_id: destId,
        amount_usd: amount,
        description: description || `Traspaso de ${originAccount?.name} a ${destAccount?.name}`,
      });

      showToast(
        'success',
        'Traspaso Exitoso',
        `Se transfirieron ${formatUSD(amount)} de ${originAccount?.name} a ${destAccount?.name}`
      );
      await loadAccounts();
      onSuccess();
      onClose();
    } catch (err: any) {
      showToast('error', 'Error en Transferencia', err.message || 'No se pudo realizar el traspaso');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto no-print">
      <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 sm:p-8 space-y-5 border border-gray-100">
        
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <ArrowRightLeft className="w-5 h-5 text-tev-green" />
            <div>
              <h3 className="text-lg font-black text-gray-900">Traspaso entre Cuentas</h3>
              <p className="text-xs text-gray-500">Mueve fondos internamente sin alterar el saldo neto</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 font-bold p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-gray-800 mb-1">Cuenta de Origen (Débito): *</label>
            <select
              value={originId}
              onChange={(e) => setOriginId(parseInt(e.target.value))}
              required
              className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
            >
              {accounts.filter(a => a.is_active).map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.currency}) - Saldo: {formatUSD(acc.current_balance)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-800 mb-1">Cuenta de Destino (Crédito): *</label>
            <select
              value={destId}
              onChange={(e) => setDestId(parseInt(e.target.value))}
              required
              className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
            >
              {accounts.filter(a => a.is_active).map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.currency}) - Saldo: {formatUSD(acc.current_balance)}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">Monto ($ USD): *</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amountUsd}
                onChange={(e) => setAmountUsd(e.target.value)}
                required
                placeholder="Ej: 100.00"
                className="w-full p-2.5 border border-gray-300 rounded-xl text-sm font-black bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">Fecha: *</label>
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
            <label className="block text-xs font-bold text-gray-800 mb-1">Concepto / Motivo:</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ej: Depósito bancario de efectivo"
              className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
            />
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
              disabled={saving}
              className="px-5 py-2.5 bg-tev-green hover:bg-tev-darkgreen text-white rounded-xl text-xs font-black shadow-md transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Transfiriendo...' : 'Confirmar Traspaso'}</span>
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
