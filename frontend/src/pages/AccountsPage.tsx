import React, { useState } from 'react';
import { Landmark, Plus, ArrowRightLeft, Calculator, Edit3, CheckCircle, XCircle } from 'lucide-react';
import { useTreasury } from '../context/TreasuryContext';
import { useToast } from '../components/common/Toast';
import { TreasuryAccount } from '../types';
import { formatUSD, formatVES } from '../utils/formatters';
import { AccountModal } from '../components/modals/AccountModal';
import { TransferModal } from '../components/modals/TransferModal';
import { ArqueoModal } from '../components/modals/ArqueoModal';

export const AccountsPage: React.FC = () => {
  const { accounts, bcvRate, loadAccounts } = useTreasury();
  const { showToast } = useToast();

  const [selectedAccountToEdit, setSelectedAccountToEdit] = useState<TreasuryAccount | null>(null);
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showArqueoModal, setShowArqueoModal] = useState(false);
  const [arqueoCurrency, setArqueoCurrency] = useState<'USD' | 'VES'>('USD');

  // Totales
  const totalUsdAccounts = accounts
    .filter((a) => a.is_active && a.currency === 'USD')
    .reduce((acc, a) => acc + (a.current_balance || 0), 0);

  const totalVesAccounts = accounts
    .filter((a) => a.is_active && a.currency === 'VES')
    .reduce((acc, a) => acc + (a.current_balance || 0), 0);

  const totalConsolidatedUsd = totalUsdAccounts + (totalVesAccounts / bcvRate);

  const handleOpenEdit = (acc: TreasuryAccount) => {
    setSelectedAccountToEdit(acc);
    setShowAccountModal(true);
  };

  const handleOpenNew = () => {
    setSelectedAccountToEdit(null);
    setShowAccountModal(true);
  };

  const handleOpenArqueo = (curr: 'USD' | 'VES') => {
    setArqueoCurrency(curr);
    setShowArqueoModal(true);
  };

  return (
    <div className="space-y-6">
      {/* Tarjeta de Posición Financiera Consolidada */}
      <div className="bg-gradient-to-r from-tev-darkgreen to-tev-green text-white p-6 sm:p-8 rounded-3xl shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <span className="text-xs font-bold text-emerald-200 uppercase tracking-wider block">
              Posición Consolidada en Tesorería
            </span>
            <h2 className="text-3xl sm:text-4xl font-black mt-1">
              {formatUSD(totalConsolidatedUsd)}
            </h2>
            <p className="text-xs text-emerald-100 mt-1">
              Disponible en Efectivo USD: <strong>{formatUSD(totalUsdAccounts)}</strong> • Cuentas VES: <strong>{formatVES(totalVesAccounts)}</strong>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => handleOpenArqueo('USD')}
              className="px-3.5 py-2 bg-white/20 hover:bg-white/30 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer"
            >
              <Calculator className="w-4 h-4" />
              <span>Arqueo Físico</span>
            </button>

            <button
              type="button"
              onClick={() => setShowTransferModal(true)}
              className="px-3.5 py-2 bg-white/20 hover:bg-white/30 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer"
            >
              <ArrowRightLeft className="w-4 h-4" />
              <span>Traspaso Fondos</span>
            </button>

            <button
              type="button"
              onClick={handleOpenNew}
              className="px-4 py-2 bg-white text-tev-darkgreen hover:bg-emerald-50 rounded-xl text-xs font-black shadow transition flex items-center gap-1.5 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Nueva Cuenta</span>
            </button>
          </div>
        </div>
      </div>

      {/* Cuadrícula de Cuentas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.map((acc) => (
          <div
            key={acc.id}
            className={`p-5 rounded-3xl border transition shadow-sm bg-white ${
              acc.is_active ? 'border-gray-200' : 'border-gray-200 opacity-60 bg-gray-50'
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] uppercase font-bold text-gray-400 block tracking-wide">
                  {acc.account_type}
                </span>
                <h3 className="text-base font-black text-gray-900 mt-0.5">{acc.name}</h3>
              </div>

              <div className="flex items-center gap-1">
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-black ${
                    acc.currency === 'USD'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}
                >
                  {acc.currency}
                </span>
                <button
                  type="button"
                  onClick={() => handleOpenEdit(acc)}
                  className="p-1.5 text-gray-400 hover:text-gray-700 rounded-lg transition"
                  title="Editar cuenta"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-gray-100">
              <span className="text-[10px] text-gray-500 font-semibold block">Saldo Disponible:</span>
              <p className="text-2xl font-black text-gray-900 mt-0.5">
                {acc.currency === 'USD' ? formatUSD(acc.current_balance) : formatVES(acc.current_balance)}
              </p>
              {acc.currency === 'VES' && (
                <p className="text-[10px] text-gray-400 mt-0.5">
                  Aprox. {formatUSD(acc.current_balance / bcvRate)} al BCV
                </p>
              )}
            </div>

            <div className="mt-3 pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-400">
              <span>Inicio: {acc.currency === 'USD' ? formatUSD(acc.initial_balance) : formatVES(acc.initial_balance)}</span>
              <span className="flex items-center gap-1 font-semibold">
                {acc.is_active ? (
                  <span className="text-emerald-600 flex items-center gap-0.5">
                    <CheckCircle className="w-3 h-3" /> Activa
                  </span>
                ) : (
                  <span className="text-gray-400 flex items-center gap-0.5">
                    <XCircle className="w-3 h-3" /> Inactiva
                  </span>
                )}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Modales */}
      <AccountModal
        isOpen={showAccountModal}
        onClose={() => setShowAccountModal(false)}
        accountToEdit={selectedAccountToEdit}
      />

      <TransferModal
        isOpen={showTransferModal}
        onClose={() => setShowTransferModal(false)}
        onSuccess={loadAccounts}
      />

      <ArqueoModal
        isOpen={showArqueoModal}
        onClose={() => setShowArqueoModal(false)}
        currency={arqueoCurrency}
      />
    </div>
  );
};
