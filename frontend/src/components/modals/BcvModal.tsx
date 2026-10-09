import React, { useState } from 'react';
import { RefreshCw, Save, X } from 'lucide-react';
import { useTreasury } from '../../context/TreasuryContext';
import { useToast } from '../common/Toast';
import { formatNumber } from '../../utils/formatters';

export const BcvModal: React.FC = () => {
  const { bcvRate, loadingBcv, isBcvModalOpen, setIsBcvModalOpen, loadBcvRate, updateBcvRate } = useTreasury();
  const { showToast } = useToast();
  const [manualRate, setManualRate] = useState<string>(bcvRate.toString());
  const [saving, setSaving] = useState(false);

  if (!isBcvModalOpen) return null;

  const handleSyncLive = async () => {
    try {
      const rate = await loadBcvRate(true);
      setManualRate(rate.toString());
      showToast('success', 'Tasa Sincronizada', `Tasa BCV del día: Bs. ${formatNumber(rate)}`);
    } catch {
      showToast('error', 'Error BCV', 'No se pudo sincronizar automáticamente con el portal del BCV');
    }
  };

  const handleSaveManual = async (e: React.FormEvent) => {
    e.preventDefault();
    const rateNum = parseFloat(manualRate);
    if (isNaN(rateNum) || rateNum <= 0) {
      showToast('warning', 'Tasa Inválida', 'Ingrese un valor numérico mayor a 0');
      return;
    }
    setSaving(true);
    try {
      await updateBcvRate(rateNum);
      showToast('success', 'Tasa Actualizada', `La tasa oficial se fijó en Bs. ${formatNumber(rateNum)}`);
      setIsBcvModalOpen(false);
    } catch (err: any) {
      showToast('error', 'Error al Guardar', err.message || 'No se pudo fijar la tasa');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto no-print">
      <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 sm:p-8 space-y-5 border border-gray-100">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">🇻🇪</span>
            <div>
              <h3 className="text-lg font-black text-gray-900">Tasa Oficial BCV</h3>
              <p className="text-xs text-gray-500">Sincronización en vivo y ajuste de tasa</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsBcvModalOpen(false)}
            className="text-gray-400 hover:text-gray-700 font-bold p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 bg-emerald-50 rounded-2xl border border-emerald-200 text-center space-y-1">
          <p className="text-xs font-bold text-emerald-800 uppercase tracking-wide">Tasa Vigente en el Sistema:</p>
          <p className="text-3xl font-black text-emerald-950">Bs. {formatNumber(bcvRate)}</p>
          <p className="text-[11px] text-emerald-700">Utilizada para conversión automática en ventas y arqueos</p>
        </div>

        <div>
          <button
            type="button"
            onClick={handleSyncLive}
            disabled={loadingBcv}
            className="w-full py-2.5 px-4 bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loadingBcv ? 'animate-spin' : ''}`} />
            <span>{loadingBcv ? 'Consultando portal del BCV...' : 'Consultar / Sincronizar en Vivo'}</span>
          </button>
        </div>

        <form onSubmit={handleSaveManual} className="space-y-4 pt-3 border-t border-gray-100">
          <div>
            <label className="block text-xs font-bold text-gray-800 mb-1">
              ✏️ O ingresar tasa manualmente (Bs. / USD):
            </label>
            <input
              type="number"
              step="0.01"
              min="1"
              value={manualRate}
              onChange={(e) => setManualRate(e.target.value)}
              required
              placeholder="Ej: 827.74"
              className="w-full p-2.5 border border-emerald-300 rounded-xl text-base font-black text-emerald-950 bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
            <p className="text-[10px] text-gray-500 mt-1">
              Permite fijar de inmediato la tasa de la tarde publicada por el BCV.
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setIsBcvModalOpen(false)}
              className="px-4 py-2 text-xs font-bold text-gray-600 hover:bg-gray-100 rounded-xl transition cursor-pointer"
            >
              Cerrar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl text-xs font-black shadow-md transition cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Guardando...' : 'Guardar y Aplicar Tasa'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
