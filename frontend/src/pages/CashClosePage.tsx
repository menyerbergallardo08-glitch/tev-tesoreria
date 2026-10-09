import React, { useState, useEffect } from 'react';
import { Calendar, Printer, CheckCircle, Calculator, AlertCircle, FileText } from 'lucide-react';
import { useTreasury } from '../context/TreasuryContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/common/Toast';
import { api } from '../api/client';
import { CashCloseSummary, ArqueoUsdData, ArqueoVesData } from '../types';
import { formatNumber, formatUSD, formatVES, getTodayDateString } from '../utils/formatters';
import { ArqueoModal } from '../components/modals/ArqueoModal';
import { CashCloseReceiptModal } from '../components/modals/CashCloseReceiptModal';

export const CashClosePage: React.FC = () => {
  const { bcvRate, loadAccounts } = useTreasury();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [date, setDate] = useState(getTodayDateString());
  const [summary, setSummary] = useState<CashCloseSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [submittingClose, setSubmittingClose] = useState(false);

  // Arqueo físico modal
  const [showArqueoModal, setShowArqueoModal] = useState(false);
  const [physicalUsd, setPhysicalUsd] = useState<number>(0);
  const [physicalVes, setPhysicalVes] = useState<number>(0);
  const [arqueoUsdObj, setArqueoUsdObj] = useState<ArqueoUsdData>({ b100: 0, b50: 0, b20: 0, b10: 0, b5: 0, b1: 0 });
  const [arqueoVesObj, setArqueoVesObj] = useState<ArqueoVesData>({ b500: 0, b200: 0, b100: 0, b50: 0, b20: 0, b10: 0 });

  // Receipt Modal
  const [showReceiptModal, setShowReceiptModal] = useState(false);
  const [notes, setNotes] = useState('');

  const loadDailySummary = async () => {
    setLoading(true);
    try {
      const data = await api.get<CashCloseSummary>(`/api/cash-close/summary?date=${date}`);
      setSummary(data);
      // Pre-fill physical from collections if not edited
      if (data?.collections_summary) {
        setPhysicalUsd(data.collections_summary.cash_usd || 0);
        setPhysicalVes(data.collections_summary.cash_ves || 0);
      }
    } catch (e) {
      console.error('Error al cargar cuadre:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDailySummary();
  }, [date]);

  const handleArqueoSave = (data: { usd: ArqueoUsdData; ves: ArqueoVesData; totalUsd: number; totalVes: number }) => {
    setArqueoUsdObj(data.usd);
    setArqueoVesObj(data.ves);
    setPhysicalUsd(data.totalUsd);
    setPhysicalVes(data.totalVes);
    showToast('success', 'Arqueo Aplicado', `Efectivo en mano: ${formatUSD(data.totalUsd)} y ${formatVES(data.totalVes)}`);
  };

  // Expected vs Real
  const expectedTotalUsd = summary?.collections_summary?.total_collected_real_usd || 0;
  const differenceUsd = (physicalUsd + (physicalVes / (summary?.bcv_rate || bcvRate))) - (summary?.collections_summary?.cash_usd || 0);

  const handleConfirmClose = async () => {
    if (!summary) return;
    if (!confirm('¿Confirma el cierre de caja del día? Esta acción fijará el arqueo definitivo de la jornada.')) {
      return;
    }

    setSubmittingClose(true);
    try {
      await api.post('/api/cash-close', {
        date,
        profit_sales_total_usd: summary.sales_summary?.net_sales_usd || 0,
        sales_fiscal_iva_usd: summary.sales_summary?.fiscal_iva_usd || 0,
        sales_notes_credit_usd: summary.sales_summary?.notes_credit_usd || 0,
        sales_notes_collected_usd: summary.sales_summary?.notes_collected_usd || 0,
        returns_total_usd: summary.sales_summary?.returns_total_usd || 0,
        cash_usd_physical: physicalUsd,
        cash_ves_physical: physicalVes,
        pos_total_usd: summary.collections_summary?.pos_total || 0,
        bank_transfers_usd: summary.collections_summary?.pago_movil_usd || 0,
        cashea_usd: summary.collections_summary?.cashea_usd || 0,
        retentions_iva_usd: summary.collections_summary?.retentions_iva_usd || 0,
        retentions_islr_usd: summary.collections_summary?.retentions_islr_usd || 0,
        expenses_caja_usd: summary.collections_summary?.expenses_caja_usd || 0,
        total_expected_usd: expectedTotalUsd,
        difference_usd: differenceUsd,
        status: Math.abs(differenceUsd) < 0.05 ? 'CUADRADO' : differenceUsd > 0 ? 'SOBRANTE' : 'FALTANTE',
        arqueo_usd_json: JSON.stringify(arqueoUsdObj),
        arqueo_ves_json: JSON.stringify(arqueoVesObj),
        notes: notes.trim() || null,
      });

      showToast('success', 'Caja Cerrada', 'El cierre de operaciones del día fue registrado exitosamente');
      await loadDailySummary();
      await loadAccounts();
    } catch (err: any) {
      showToast('error', 'Error en Cierre', err.message || 'No se pudo cerrar la caja');
    } finally {
      setSubmittingClose(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Barra Superior */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-200">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg sm:text-xl font-black text-gray-900">
                Cuadre Diario & Cierre de Caja
              </h2>
              <p className="text-xs text-gray-500">
                Conciliación entre ventas registradas, arqueo físico y recaudación por canal
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="p-2 border border-gray-300 rounded-xl text-xs font-bold bg-white focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowReceiptModal(true)}
              className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white rounded-xl text-xs font-black shadow transition flex items-center gap-1.5 cursor-pointer"
            >
              <Printer className="w-4 h-4" />
              <span>Imprimir Cierre (1 Hoja)</span>
            </button>
          </div>
        </div>

        {/* 1. Resumen Comercial */}
        <div className="mt-6 space-y-3">
          <h3 className="text-xs font-black uppercase text-gray-700 tracking-wider">
            1. Resumen Comercial de Ventas
          </h3>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] text-gray-500 font-semibold block">Facturación Fiscal (IVA):</span>
              <strong className="text-sm font-black text-gray-900">
                {formatUSD(summary?.sales_summary?.fiscal_iva_usd || 0)}
              </strong>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] text-gray-500 font-semibold block">Notas a Crédito (CxC):</span>
              <strong className="text-sm font-black text-gray-900">
                {formatUSD(summary?.sales_summary?.notes_credit_usd || 0)}
              </strong>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] text-gray-500 font-semibold block">Notas Cobradas:</span>
              <strong className="text-sm font-black text-gray-900">
                {formatUSD(summary?.sales_summary?.notes_collected_usd || 0)}
              </strong>
            </div>

            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl">
              <span className="text-[10px] text-emerald-800 font-bold block uppercase">Venta Neta del Día:</span>
              <strong className="text-base font-black text-emerald-950">
                {formatUSD(summary?.sales_summary?.net_sales_usd || 0)}
              </strong>
            </div>
          </div>
        </div>

        {/* 2. Recaudación por Medio de Pago */}
        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-black uppercase text-gray-700 tracking-wider">
              2. Fondos Recaudados por Canal
            </h3>
            <button
              type="button"
              onClick={() => setShowArqueoModal(true)}
              className="px-3 py-1 bg-tev-green/10 hover:bg-tev-green/20 text-tev-darkgreen text-xs font-black rounded-lg transition flex items-center gap-1 cursor-pointer"
            >
              <Calculator className="w-3.5 h-3.5" />
              <span>Conteo de Billetes Físicos</span>
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] text-gray-500 font-semibold block">Efectivo USD (Gaveta):</span>
              <strong className="text-sm font-black text-gray-900">
                {formatUSD(physicalUsd)}
              </strong>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] text-gray-500 font-semibold block">Efectivo VES (Gaveta):</span>
              <strong className="text-sm font-black text-gray-900">
                {formatVES(physicalVes)}
              </strong>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] text-gray-500 font-semibold block">Lotes Puntos de Venta (POS):</span>
              <strong className="text-sm font-black text-blue-900">
                {formatUSD(summary?.collections_summary?.pos_total || 0)}
              </strong>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] text-gray-500 font-semibold block">Pago Móvil / Bancos VES:</span>
              <strong className="text-sm font-black text-gray-900">
                {formatUSD(summary?.collections_summary?.pago_movil_usd || 0)}
              </strong>
            </div>

            <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-xl">
              <span className="text-[10px] text-amber-900 font-semibold block">Cashea (Por Cobrar):</span>
              <strong className="text-sm font-black text-amber-950">
                {formatUSD(summary?.collections_summary?.cashea_usd || 0)}
              </strong>
            </div>

            <div className="p-3 bg-purple-50/60 border border-purple-200 rounded-xl">
              <span className="text-[10px] text-purple-900 font-semibold block">Retenciones Fiscales:</span>
              <strong className="text-sm font-black text-purple-950">
                {formatUSD((summary?.collections_summary?.retentions_iva_usd || 0) + (summary?.collections_summary?.retentions_islr_usd || 0))}
              </strong>
            </div>

            <div className="p-3 bg-rose-50/60 border border-rose-200 rounded-xl">
              <span className="text-[10px] text-rose-800 font-semibold block">Vales / Gastos Menores:</span>
              <strong className="text-sm font-black text-rose-700">
                -{formatUSD(summary?.collections_summary?.expenses_caja_usd || 0)}
              </strong>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
              <span className="text-[10px] text-blue-900 font-bold block uppercase">Total Recaudado:</span>
              <strong className="text-base font-black text-blue-950">
                {formatUSD(expectedTotalUsd)}
              </strong>
            </div>
          </div>
        </div>

        {/* 3. Conciliación y Diferencia */}
        <div className="mt-6 pt-4 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <span className="text-xs font-bold text-gray-600 block">
              Diferencia del Cuadre (Físico vs Sistema):
            </span>
            <div className="flex items-center gap-2">
              <span
                className={`text-2xl font-black ${
                  Math.abs(differenceUsd) < 0.05
                    ? 'text-emerald-700'
                    : differenceUsd > 0
                    ? 'text-blue-700'
                    : 'text-rose-700'
                }`}
              >
                {Math.abs(differenceUsd) < 0.05
                  ? 'CUADRADO ($0.00)'
                  : `${differenceUsd > 0 ? 'SOBRANTE: +' : 'FALTANTE: '}${formatUSD(differenceUsd)}`}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleConfirmClose}
              disabled={submittingClose || summary?.is_closed}
              className={`px-6 py-3 rounded-xl text-xs font-black shadow-md transition flex items-center gap-2 ${
                summary?.is_closed
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-tev-green hover:bg-tev-darkgreen text-white cursor-pointer'
              }`}
            >
              <CheckCircle className="w-4 h-4" />
              <span>{summary?.is_closed ? 'Caja Ya Cerrada' : submittingClose ? 'Cerrando...' : 'Confirmar Cierre de Caja'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Modales */}
      <ArqueoModal
        isOpen={showArqueoModal}
        onClose={() => setShowArqueoModal(false)}
        currency="USD"
        initialUsd={arqueoUsdObj}
        initialVes={arqueoVesObj}
        onSave={handleArqueoSave}
      />

      <CashCloseReceiptModal
        isOpen={showReceiptModal}
        onClose={() => setShowReceiptModal(false)}
        summary={summary}
        date={date}
      />
    </div>
  );
};
