import React from 'react';
import { X, Printer } from 'lucide-react';
import { CashCloseSummary } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { formatNumber, formatUSD, formatVES } from '../../utils/formatters';

interface CashCloseReceiptModalProps {
  isOpen: boolean;
  onClose: () => void;
  summary: CashCloseSummary | null;
  date: string;
}

export const CashCloseReceiptModal: React.FC<CashCloseReceiptModalProps> = ({
  isOpen,
  onClose,
  summary,
  date,
}) => {
  const { user } = useAuth();

  if (!isOpen || !summary) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-3xl shadow-2xl max-w-2xl w-full p-6 sm:p-8 space-y-6 border border-gray-200">
        
        {/* Header no imprimible */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100 no-print">
          <div className="flex items-center gap-2">
            <span className="text-2xl">📄</span>
            <div>
              <h3 className="text-lg font-black text-gray-900">Comprobante de Cuadre Diario</h3>
              <p className="text-xs text-gray-500">Resumen integral para archivo físico y auditoría (1 Hoja)</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white rounded-xl text-xs font-black shadow transition flex items-center gap-1.5 cursor-pointer"
            >
              <Printer className="w-4 h-4" />
              <span>Imprimir / Guardar PDF</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-700 font-bold rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ÁREA IMPRIMIBLE DEL COMPROBANTE */}
        <div
          id="cash-close-printable-area"
          className="p-4 sm:p-6 bg-white border border-gray-200 rounded-2xl space-y-5 text-gray-900"
        >
          {/* Encabezado Corporativo */}
          <div className="flex items-start justify-between border-b-2 border-gray-900 pb-4">
            <div>
              <h1 className="text-lg font-black tracking-tight text-gray-900">TODO ELÉCTRICO VALENCIA, C.A.</h1>
              <p className="text-[11px] font-bold text-gray-600">RIF: J-40842247-9 | Sistema de Control Interno y Tesorería</p>
              <p className="text-[10px] text-gray-500">Valencia, Estado Carabobo - Venezuela</p>
            </div>
            <div className="text-right">
              <span className="inline-block px-3 py-1 bg-gray-900 text-white font-black text-xs rounded-lg uppercase tracking-wider">
                COMPROBANTE DE CIERRE
              </span>
              <p className="text-xs font-bold text-gray-700 mt-1">
                Fecha: <strong className="text-gray-900">{date}</strong>
              </p>
              <p className="text-[10px] text-gray-500">
                Tasa BCV: {formatVES(summary.bcv_rate)}
              </p>
            </div>
          </div>

          {/* Metadatos de Responsabilidad */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 bg-slate-50 rounded-xl text-xs border border-slate-200">
            <div>
              <span className="text-[10px] text-gray-500 font-bold block">OPERADOR / CAJERO:</span>
              <strong className="text-gray-900">{user?.full_name || 'Cajero de Turno'}</strong>
            </div>
            <div>
              <span className="text-[10px] text-gray-500 font-bold block">ESTADO DEL CIERRE:</span>
              <strong className={summary.is_closed ? 'text-emerald-700' : 'text-amber-700'}>
                {summary.is_closed ? 'CERRADO / CUADRADO' : 'AUDITORÍA PREVIA'}
              </strong>
            </div>
            <div>
              <span className="text-[10px] text-gray-500 font-bold block">TOTAL TRANSACCIONES:</span>
              <strong className="text-gray-900">{summary.transactions_count || 0} ops</strong>
            </div>
            <div>
              <span className="text-[10px] text-gray-500 font-bold block">EMISIÓN:</span>
              <strong className="text-gray-700">
                {new Date().toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })}
              </strong>
            </div>
          </div>

          {/* 1. Resumen Comercial de Ventas */}
          <div>
            <h4 className="text-xs font-black uppercase text-gray-800 border-b border-gray-300 pb-1 mb-2">
              1. Resumen Comercial de Ventas
            </h4>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">🧾 Facturación Fiscal (Con IVA):</span>
                <span className="font-bold text-gray-900">{formatUSD(summary.sales_summary?.fiscal_iva_usd || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">📦 Notas de Entrega a Crédito (CxC):</span>
                <span className="font-bold text-gray-900">{formatUSD(summary.sales_summary?.notes_credit_usd || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">📥 Notas Cobradas / Convertidas:</span>
                <span className="font-bold text-gray-900">{formatUSD(summary.sales_summary?.notes_collected_usd || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-rose-700">↩️ (-) Devoluciones / Reembolsos:</span>
                <span className="font-bold text-rose-700">-{formatUSD(summary.sales_summary?.returns_total_usd || 0)}</span>
              </div>
            </div>
            <div className="flex justify-between items-center p-2.5 bg-emerald-50 rounded-xl border border-emerald-200 mt-2">
              <span className="text-xs font-black text-emerald-950 uppercase">VENTA NETA TOTAL DEL DÍA:</span>
              <span className="text-sm font-black text-emerald-950">
                {formatUSD(summary.sales_summary?.net_sales_usd || 0)} ({formatVES((summary.sales_summary?.net_sales_usd || 0) * summary.bcv_rate)})
              </span>
            </div>
          </div>

          {/* 2. Recaudación y Conciliación por Medio de Pago */}
          <div>
            <h4 className="text-xs font-black uppercase text-gray-800 border-b border-gray-300 pb-1 mb-2">
              2. Fondos Recaudados y Conciliación por Medio de Pago
            </h4>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">💵 Gaveta Efectivo USD (En mano):</span>
                <span className="font-bold text-gray-900">{formatUSD(summary.collections_summary?.cash_usd || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">🇻🇪 Gaveta Efectivo VES (Bs. en mano):</span>
                <span className="font-bold text-gray-900">
                  {formatVES(summary.collections_summary?.cash_ves || 0)}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">💳 Total Lotes Puntos de Venta (POS):</span>
                <span className="font-bold text-blue-900">{formatUSD(summary.collections_summary?.pos_total || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">📲 Pago Móvil / Bancos VES:</span>
                <span className="font-bold text-gray-900">{formatUSD(summary.collections_summary?.pago_movil_usd || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-amber-900 font-bold">🟡 BNC - Cashea (Por Liquidar):</span>
                <span className="font-bold text-amber-950">{formatUSD(summary.collections_summary?.cashea_usd || 0)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-purple-900">📑 Retenciones IVA/ISLR:</span>
                <span className="font-bold text-purple-950">
                  {formatUSD((summary.collections_summary?.retentions_iva_usd || 0) + (summary.collections_summary?.retentions_islr_usd || 0))}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100 col-span-2">
                <span className="text-rose-700">💸 (-) Vales / Gastos Menores Pagados de Caja:</span>
                <span className="font-bold text-rose-700">-{formatUSD(summary.collections_summary?.expenses_caja_usd || 0)}</span>
              </div>
            </div>
            <div className="flex justify-between items-center p-2.5 bg-blue-50 rounded-xl border border-blue-200 mt-2">
              <span className="text-xs font-black text-blue-950 uppercase">TOTAL FONDOS RECAUDADOS / CONCILIADOS:</span>
              <span className="text-sm font-black text-blue-950">
                {formatUSD(summary.collections_summary?.total_collected_real_usd || 0)}
              </span>
            </div>
          </div>

          {/* Observaciones */}
          {summary.notes && (
            <div className="p-3 bg-gray-50 rounded-xl text-xs border border-gray-200">
              <span className="text-[10px] font-bold text-gray-500 uppercase block">Observaciones del Cierre:</span>
              <p className="text-gray-800 italic mt-0.5">{summary.notes}</p>
            </div>
          )}

          {/* Bloque de Firmas */}
          <div className="grid grid-cols-2 gap-8 pt-6 mt-4 border-t border-gray-300 text-center text-xs">
            <div>
              <div className="border-b border-gray-400 w-3/4 mx-auto pb-6"></div>
              <p className="font-bold text-gray-900 mt-2">{user?.full_name || 'Cajero / Asistente'}</p>
              <p className="text-[10px] text-gray-500 font-semibold uppercase">Caja / Entregó Conforme</p>
            </div>
            <div>
              <div className="border-b border-gray-400 w-3/4 mx-auto pb-6"></div>
              <p className="font-bold text-gray-900 mt-2">{summary.verified_by || 'Administración / Auditoría'}</p>
              <p className="text-[10px] text-gray-500 font-semibold uppercase">Administración / Recibió y Verificó</p>
            </div>
          </div>

        </div>

        {/* Botón inferior de cierre (no imprimible) */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-gray-100 no-print">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-xl text-xs font-bold transition cursor-pointer"
          >
            Cerrar Ventana
          </button>
          <button
            type="button"
            onClick={handlePrint}
            className="px-6 py-2.5 bg-blue-700 hover:bg-blue-800 text-white rounded-xl text-xs font-black shadow transition flex items-center gap-1.5 cursor-pointer"
          >
            <Printer className="w-4 h-4" />
            <span>Imprimir Comprobante (1 Hoja)</span>
          </button>
        </div>

      </div>
    </div>
  );
};
