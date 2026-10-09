import React, { useState } from 'react';
import { X, Printer, RotateCcw } from 'lucide-react';
import { ArqueoUsdData, ArqueoVesData } from '../../types';
import { formatNumber, formatUSD, formatVES } from '../../utils/formatters';

interface ArqueoModalProps {
  isOpen: boolean;
  onClose: () => void;
  currency: 'USD' | 'VES';
  initialUsd?: ArqueoUsdData;
  initialVes?: ArqueoVesData;
  onSave?: (data: { usd: ArqueoUsdData; ves: ArqueoVesData; totalUsd: number; totalVes: number }) => void;
}

export const ArqueoModal: React.FC<ArqueoModalProps> = ({
  isOpen,
  onClose,
  currency: defaultCurrency,
  initialUsd,
  initialVes,
  onSave,
}) => {
  const [currency, setCurrency] = useState<'USD' | 'VES'>(defaultCurrency);

  const [usd, setUsd] = useState<ArqueoUsdData>(
    initialUsd || { b100: 0, b50: 0, b20: 0, b10: 0, b5: 0, b1: 0 }
  );

  const [ves, setVes] = useState<ArqueoVesData>(
    initialVes || { b500: 0, b200: 0, b100: 0, b50: 0, b20: 0, b10: 0 }
  );

  if (!isOpen) return null;

  const totalUsd =
    (usd.b100 || 0) * 100 +
    (usd.b50 || 0) * 50 +
    (usd.b20 || 0) * 20 +
    (usd.b10 || 0) * 10 +
    (usd.b5 || 0) * 5 +
    (usd.b1 || 0) * 1;

  const totalVes =
    (ves.b500 || 0) * 500 +
    (ves.b200 || 0) * 200 +
    (ves.b100 || 0) * 100 +
    (ves.b50 || 0) * 50 +
    (ves.b20 || 0) * 20 +
    (ves.b10 || 0) * 10;

  const handleReset = () => {
    if (currency === 'USD') {
      setUsd({ b100: 0, b50: 0, b20: 0, b10: 0, b5: 0, b1: 0 });
    } else {
      setVes({ b500: 0, b200: 0, b100: 0, b50: 0, b20: 0, b10: 0 });
    }
  };

  const handleConfirm = () => {
    if (onSave) {
      onSave({ usd, ves, totalUsd, totalVes });
    }
    onClose();
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto no-print">
      <div className="bg-white rounded-3xl shadow-2xl max-w-xl w-full p-6 sm:p-8 space-y-5 border border-gray-100">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div>
            <h3 className="text-lg font-black text-gray-900">Arqueo Físico de Billetes</h3>
            <p className="text-xs text-gray-500">Conteo y verificación física en gaveta de caja</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 font-bold p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Currency Tabs */}
        <div className="flex gap-2 p-1 bg-slate-100 rounded-xl">
          <button
            type="button"
            onClick={() => setCurrency('USD')}
            className={`flex-1 py-2 text-xs font-black rounded-lg transition ${
              currency === 'USD' ? 'bg-white text-emerald-900 shadow-sm' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            💵 Billetes Dólares (USD)
          </button>
          <button
            type="button"
            onClick={() => setCurrency('VES')}
            className={`flex-1 py-2 text-xs font-black rounded-lg transition ${
              currency === 'VES' ? 'bg-white text-blue-900 shadow-sm' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            🇻🇪 Billetes Bolívares (VES)
          </button>
        </div>

        {/* Resumen Total */}
        <div
          className={`p-4 rounded-2xl border text-center ${
            currency === 'USD' ? 'bg-emerald-50 border-emerald-200' : 'bg-blue-50 border-blue-200'
          }`}
        >
          <p className="text-xs font-bold uppercase tracking-wide opacity-80">
            Total Físico en {currency}:
          </p>
          <p className="text-3xl font-black mt-1">
            {currency === 'USD' ? formatUSD(totalUsd) : formatVES(totalVes)}
          </p>
        </div>

        {/* Formulario de Conteo USD */}
        {currency === 'USD' && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {[100, 50, 20, 10, 5, 1].map((val) => {
              const key = `b${val}` as keyof ArqueoUsdData;
              const count = usd[key] || 0;
              const subtotal = count * val;
              return (
                <div key={val} className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-black text-gray-800">${val} USD</span>
                    <span className="text-[11px] font-bold text-emerald-700">${subtotal}</span>
                  </div>
                  <input
                    type="number"
                    min="0"
                    value={count || ''}
                    onChange={(e) =>
                      setUsd((prev) => ({ ...prev, [key]: parseInt(e.target.value) || 0 }))
                    }
                    placeholder="0"
                    className="w-full p-2 border border-gray-300 rounded-lg text-sm font-bold text-center bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              );
            })}
          </div>
        )}

        {/* Formulario de Conteo VES */}
        {currency === 'VES' && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {[500, 200, 100, 50, 20, 10].map((val) => {
              const key = `b${val}` as keyof ArqueoVesData;
              const count = ves[key] || 0;
              const subtotal = count * val;
              return (
                <div key={val} className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-black text-gray-800">Bs. {val}</span>
                    <span className="text-[11px] font-bold text-blue-700">Bs. {formatNumber(subtotal)}</span>
                  </div>
                  <input
                    type="number"
                    min="0"
                    value={count || ''}
                    onChange={(e) =>
                      setVes((prev) => ({ ...prev, [key]: parseInt(e.target.value) || 0 }))
                    }
                    placeholder="0"
                    className="w-full p-2 border border-gray-300 rounded-lg text-sm font-bold text-center bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              );
            })}
          </div>
        )}

        {/* Botones de Acción */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-100">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleReset}
              className="p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition flex items-center gap-1 text-xs font-bold"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Limpiar</span>
            </button>
            <button
              type="button"
              onClick={handlePrint}
              className="p-2 text-blue-700 hover:bg-blue-50 rounded-xl transition flex items-center gap-1 text-xs font-bold"
            >
              <Printer className="w-4 h-4" />
              <span>Imprimir</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-bold text-gray-600 hover:bg-gray-100 rounded-xl transition"
            >
              Cerrar
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              className="px-5 py-2.5 bg-tev-green hover:bg-tev-darkgreen text-white rounded-xl text-xs font-black shadow-md transition"
            >
              Aplicar al Cuadre
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
