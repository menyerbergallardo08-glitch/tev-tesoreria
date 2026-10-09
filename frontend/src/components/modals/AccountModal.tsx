import React, { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import { TreasuryAccount } from '../../types';
import { useTreasury } from '../../context/TreasuryContext';
import { useToast } from '../common/Toast';
import { api } from '../../api/client';

interface AccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  accountToEdit: TreasuryAccount | null;
}

export const AccountModal: React.FC<AccountModalProps> = ({ isOpen, onClose, accountToEdit }) => {
  const { loadAccounts } = useTreasury();
  const { showToast } = useToast();

  const [name, setName] = useState('');
  const [currency, setCurrency] = useState<'USD' | 'VES' | 'USDT'>('USD');
  const [accountType, setAccountType] = useState('Caja Operativa');
  const [initialBalance, setInitialBalance] = useState<string>('0.00');
  const [onlyIncome, setOnlyIncome] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (accountToEdit) {
      setName(accountToEdit.name);
      setCurrency(accountToEdit.currency);
      setAccountType(accountToEdit.account_type);
      setInitialBalance(accountToEdit.initial_balance.toString());
      setOnlyIncome(!!accountToEdit.only_income);
      setIsActive(accountToEdit.is_active);
    } else {
      setName('');
      setCurrency('USD');
      setAccountType('Caja Operativa');
      setInitialBalance('0.00');
      setOnlyIncome(false);
      setIsActive(true);
    }
  }, [accountToEdit, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      showToast('warning', 'Nombre Requerido', 'Escriba el nombre de la cuenta o caja');
      return;
    }

    setSaving(true);
    try {
      if (accountToEdit) {
        await api.put(`/api/accounts/${accountToEdit.id}`, {
          name: name.trim(),
          account_type: accountType,
          initial_balance: parseFloat(initialBalance) || 0.0,
          only_income: onlyIncome,
          is_active: isActive,
        });
        showToast('success', 'Cuenta Actualizada', `Se guardaron los cambios en "${name}"`);
      } else {
        await api.post('/api/accounts', {
          name: name.trim(),
          currency,
          account_type: accountType,
          initial_balance: parseFloat(initialBalance) || 0.0,
          only_income: onlyIncome,
        });
        showToast('success', 'Cuenta Creada', `La cuenta "${name}" ha sido creada con éxito`);
      }
      await loadAccounts();
      onClose();
    } catch (err: any) {
      showToast('error', 'Error al Guardar', err.message || 'No se pudo procesar la solicitud');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto no-print">
      <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 sm:p-8 space-y-5 border border-gray-100">
        
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div>
            <h3 className="text-lg font-black text-gray-900">
              {accountToEdit ? '✏️ Editar Caja / Banco' : '➕ Nueva Caja o Banco'}
            </h3>
            <p className="text-xs text-gray-500">Gestión de instrumentos de tesorería</p>
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
            <label className="block text-xs font-bold text-gray-800 mb-1">Nombre de la Cuenta: *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Ej: Banesco Panamá, Caja Chica Tienda"
              className="w-full p-2.5 border border-gray-300 rounded-xl text-sm font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">Moneda: *</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value as any)}
                disabled={!!accountToEdit}
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:outline-none disabled:bg-gray-100"
              >
                <option value="USD">USD ($)</option>
                <option value="VES">VES (Bs.)</option>
                <option value="USDT">USDT</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">Tipo de Cuenta: *</label>
              <select
                value={accountType}
                onChange={(e) => setAccountType(e.target.value)}
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:outline-none"
              >
                <option value="Caja Operativa">Caja Operativa</option>
                <option value="Cuenta Bancaria">Cuenta Bancaria</option>
                <option value="Billetera Digital">Billetera Digital</option>
                <option value="Punto de Venta POS">Punto de Venta POS</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-800 mb-1">Saldo Inicial: *</label>
            <input
              type="number"
              step="0.01"
              value={initialBalance}
              onChange={(e) => setInitialBalance(e.target.value)}
              required
              className="w-full p-2.5 border border-gray-300 rounded-xl text-sm font-bold bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
            />
          </div>

          <div className="space-y-2 pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={onlyIncome}
                onChange={(e) => setOnlyIncome(e.target.checked)}
                className="w-4 h-4 text-tev-green rounded border-gray-300 focus:ring-tev-green"
              />
              <span className="text-xs font-semibold text-gray-700">
                Solo Ingreso (No permite débitos directos sin traspaso)
              </span>
            </label>

            {accountToEdit && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="w-4 h-4 text-tev-green rounded border-gray-300 focus:ring-tev-green"
                />
                <span className="text-xs font-semibold text-gray-700">
                  Cuenta Activa en el Sistema
                </span>
              </label>
            )}
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
              <span>{saving ? 'Guardando...' : 'Guardar Cuenta'}</span>
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
