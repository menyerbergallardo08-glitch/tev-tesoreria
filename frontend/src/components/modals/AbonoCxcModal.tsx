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

  const [paymentType, setPaymentType] = useState<'COBRO' | 'RETENCION' | 'NOTA_CREDITO'>('COBRO');
  const [amountUsd, setAmountUsd] = useState<string>('');
  const [accountId, setAccountId] = useState<number>(accounts[0]?.id || 0);
  const [date, setDate] = useState<string>(getTodayDateString());
  const [referenceNumber, setReferenceNumber] = useState('');
  const [description, setDescription] = useState('');
  
  // Retención SENIAT
  const [retentionProof, setRetentionProof] = useState('');
  const [retentionType, setRetentionType] = useState('IVA_75');

  // Nota de Crédito
  const [creditNoteRef, setCreditNoteRef] = useState('');
  const [creditNoteDate, setCreditNoteDate] = useState(getTodayDateString());

  const [loading, setLoading] = useState(false);

  if (!credit) return null;

  const handleProofChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '').slice(0, 14);
    setRetentionProof(val);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(amountUsd);
    if (isNaN(amount) || amount <= 0) {
      showToast('warning', 'Monto Requerido', 'Ingrese un monto mayor a 0');
      return;
    }
    if (amount > credit.pending_balance_usd + 0.001) {
      showToast('warning', 'Monto Excedido', `El monto no puede superar el saldo pendiente (${formatUSD(credit.pending_balance_usd)})`);
      return;
    }

    if (paymentType === 'COBRO' && !accountId) {
      showToast('warning', 'Cuenta Requerida', 'Seleccione la caja o banco receptora');
      return;
    }

    if (paymentType === 'RETENCION') {
      if (retentionProof.length !== 14) {
        showToast('warning', 'Comprobante SENIAT Inválido', 'El comprobante debe constar exactamente de 14 dígitos (AAAAMMCCCCCCCC)');
        return;
      }
    }

    if (paymentType === 'NOTA_CREDITO' && !creditNoteRef.trim()) {
      showToast('warning', 'N° Nota de Crédito Requerido', 'Indique el número de la Nota de Crédito que se está cruzando');
      return;
    }

    setLoading(true);
    try {
      await api.post('/api/cxc/payments', {
        transaction_id: credit.sale_id || credit.id,
        amount_usd: amount,
        payment_type: paymentType,
        account_id: paymentType === 'COBRO' ? accountId : null,
        payment_method: paymentType === 'RETENCION' ? 'RETENCION_SENIAT' : (paymentType === 'NOTA_CREDITO' ? 'CRUCE_NOTA_CREDITO' : 'ABONO_CXC'),
        exchange_rate: bcvRate,
        reference_number: paymentType === 'RETENCION' ? retentionProof : (paymentType === 'NOTA_CREDITO' ? creditNoteRef : referenceNumber || null),
        retention_proof: paymentType === 'RETENCION' ? retentionProof : null,
        retention_type: paymentType === 'RETENCION' ? retentionType : null,
        credit_note_ref: paymentType === 'NOTA_CREDITO' ? creditNoteRef : null,
        credit_note_date: paymentType === 'NOTA_CREDITO' ? creditNoteDate : null,
        description: description || (paymentType === 'RETENCION' ? `Retención SENIAT ${retentionType} aplicada` : (paymentType === 'NOTA_CREDITO' ? `Cruce con NC #${creditNoteRef}` : `Abono a ${credit.doc_type} #${credit.doc_number}`)),
      });

      const label = paymentType === 'RETENCION' ? 'Retención SENIAT Registrada' : (paymentType === 'NOTA_CREDITO' ? 'Nota de Crédito Cruzada' : 'Abono Procesado');
      showToast('success', label, `Se aplicaron ${formatUSD(amount)} a favor de ${credit.client_name}`);
      await loadAccounts();
      onSuccess();
      onClose();
    } catch (err: any) {
      showToast('error', 'Error en Operación', err.message || 'No se pudo registrar la operación');
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
              {credit.is_cashea ? '📥 Liquidar Saldo Cashea' : '➕ Amortizar o Cobrar CxC'}
            </h3>
            <p className="text-xs text-gray-500">Cobros en dinero, retenciones SENIAT o cruce de notas de crédito</p>
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
            <strong className="text-gray-900">{credit.client_name} {credit.client_rif ? `(${credit.client_rif})` : ''}</strong>
          </div>
          <div className="flex justify-between items-center text-xs pt-1 border-t border-gray-200/60">
            <span className="text-gray-600 font-semibold">Monto Original:</span>
            <span className="font-bold text-gray-800">{formatUSD(credit.original_amount_usd)}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-emerald-700 font-semibold">Total Ya Amortizado:</span>
            <span className="font-bold text-emerald-700">{formatUSD(credit.total_abonado_usd)}</span>
          </div>
          <div className="flex justify-between items-center text-sm pt-1 border-t border-gray-200 font-black">
            <span className="text-rose-700">Saldo Pendiente:</span>
            <span className="text-rose-700">
              {formatUSD(credit.pending_balance_usd)} ({formatVES(credit.pending_balance_usd * bcvRate)})
            </span>
          </div>
        </div>

        {/* Selector de Modalidad */}
        <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-2xl text-xs font-bold">
          <button
            type="button"
            onClick={() => setPaymentType('COBRO')}
            className={`py-2 px-2 rounded-xl transition text-center ${
              paymentType === 'COBRO'
                ? 'bg-white text-purple-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            💵 Cobro Dinero
          </button>
          <button
            type="button"
            onClick={() => setPaymentType('RETENCION')}
            className={`py-2 px-2 rounded-xl transition text-center ${
              paymentType === 'RETENCION'
                ? 'bg-white text-purple-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            🏛️ Retención SENIAT
          </button>
          <button
            type="button"
            onClick={() => setPaymentType('NOTA_CREDITO')}
            className={`py-2 px-2 rounded-xl transition text-center ${
              paymentType === 'NOTA_CREDITO'
                ? 'bg-white text-purple-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            📄 Cruce con NC
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">
                {paymentType === 'RETENCION' ? 'Monto Retenido ($ USD): *' : (paymentType === 'NOTA_CREDITO' ? 'Monto a Cruzar ($ USD): *' : 'Monto a Cobrar ($ USD): *')}
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max={credit.pending_balance_usd}
                value={amountUsd}
                onChange={(e) => setAmountUsd(e.target.value)}
                required
                placeholder="0.00"
                className="w-full p-2.5 border border-purple-300 rounded-xl text-sm font-black text-purple-950 bg-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1">Fecha de Operación: *</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                className="w-full p-2.5 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:outline-none"
              />
            </div>
          </div>

          {/* Modalidad 1: COBRO ORDINARIO */}
          {paymentType === 'COBRO' && (
            <>
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

              <div>
                <label className="block text-xs font-bold text-gray-800 mb-1">N° Referencia / Lote / Comprobante:</label>
                <input
                  type="text"
                  value={referenceNumber}
                  onChange={(e) => setReferenceNumber(e.target.value)}
                  placeholder="Ej: Transf #90421 o Pago Móvil"
                  className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white focus:outline-none"
                />
              </div>
            </>
          )}

          {/* Modalidad 2: RETENCION SENIAT */}
          {paymentType === 'RETENCION' && (
            <div className="p-3 bg-purple-50/70 border border-purple-200 rounded-2xl space-y-3">
              <p className="text-[11px] text-purple-900 font-medium">
                ⚖️ <strong>Efecto Fiscal:</strong> Rebaja la deuda del cliente sin ingresar dinero físico a la gaveta de caja ni al banco.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-800 mb-1">Tipo de Retención:</label>
                  <select
                    value={retentionType}
                    onChange={(e) => setRetentionType(e.target.value)}
                    className="w-full p-2.5 border border-purple-300 rounded-xl text-xs font-bold bg-white"
                  >
                    <option value="IVA_75">Retención 75% IVA</option>
                    <option value="IVA_100">Retención 100% IVA</option>
                    <option value="ISLR_2">Retención 2% ISLR</option>
                    <option value="ISLR_3">Retención 3% ISLR</option>
                    <option value="ISLR_OTRO">Otra Retención ISLR</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-800 mb-1">Comprobante SENIAT (14 dígitos): *</label>
                  <input
                    type="text"
                    value={retentionProof}
                    onChange={handleProofChange}
                    required
                    placeholder="AAAAMMCCCCCCCC (14 dígitos)"
                    className="w-full p-2.5 border border-purple-300 rounded-xl text-xs font-mono font-bold bg-white"
                  />
                  <span className="text-[10px] text-gray-400">{retentionProof.length}/14 dígitos</span>
                </div>
              </div>
            </div>
          )}

          {/* Modalidad 3: NOTA DE CREDITO */}
          {paymentType === 'NOTA_CREDITO' && (
            <div className="p-3 bg-purple-50/70 border border-purple-200 rounded-2xl space-y-3">
              <p className="text-[11px] text-purple-900 font-medium">
                📄 <strong>Compensación:</strong> Aplica saldo a favor previo del cliente (devolución o nota de crédito anterior). No genera flujo de efectivo en caja.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-800 mb-1">N° Nota de Crédito: *</label>
                  <input
                    type="text"
                    value={creditNoteRef}
                    onChange={(e) => setCreditNoteRef(e.target.value)}
                    required
                    placeholder="Ej: NC-0042 o NC-Profit-123"
                    className="w-full p-2.5 border border-purple-300 rounded-xl text-xs font-bold bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-800 mb-1">Fecha Emisión NC:</label>
                  <input
                    type="date"
                    value={creditNoteDate}
                    onChange={(e) => setCreditNoteDate(e.target.value)}
                    className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white"
                  />
                </div>
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-gray-800 mb-1">Observaciones / Detalle Adicional:</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ej: Amortización convenida con administración"
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
              disabled={loading}
              className={`px-5 py-2.5 text-xs font-black rounded-xl shadow-md transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50 ${
                credit.is_cashea
                  ? 'bg-amber-500 hover:bg-amber-600 text-black'
                  : 'bg-purple-700 hover:bg-purple-800 text-white'
              }`}
            >
              <Save className="w-4 h-4" />
              <span>{loading ? 'Procesando...' : (paymentType === 'RETENCION' ? 'Aplicar Retención' : (paymentType === 'NOTA_CREDITO' ? 'Cruzar Nota de Crédito' : 'Confirmar y Cobrar'))}</span>
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
