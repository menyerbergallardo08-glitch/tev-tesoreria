import React, { useState, useEffect } from 'react';
import { CreditCard, Plus, DollarSign, Filter, Search } from 'lucide-react';
import { useTreasury } from '../context/TreasuryContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/common/Toast';
import { api } from '../api/client';
import { CreditRecord } from '../types';
import { formatNumber, formatUSD, formatVES, getTodayDateString } from '../utils/formatters';
import { AbonoCxcModal } from '../components/modals/AbonoCxcModal';

export const CxcPage: React.FC = () => {
  const { bcvRate } = useTreasury();
  const { hasRole } = useAuth();
  const { showToast } = useToast();

  const [credits, setCredits] = useState<CreditRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterPendingOnly, setFilterPendingOnly] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Modal de Abono
  const [selectedCredit, setSelectedCredit] = useState<CreditRecord | null>(null);

  // Modal Deuda Histórica Onboarding
  const [showHistoricalModal, setShowHistoricalModal] = useState(false);
  const [histClient, setHistClient] = useState('');
  const [histRif, setHistRif] = useState('');
  const [histDocType, setHistDocType] = useState('NOTA_ENTREGA');
  const [histDocNumber, setHistDocNumber] = useState('');
  const [histAmount, setHistAmount] = useState('');
  const [histDate, setHistDate] = useState(getTodayDateString());
  const [savingHist, setSavingHist] = useState(false);

  const loadCredits = async () => {
    setLoading(true);
    try {
      const data = await api.get<CreditRecord[]>('/api/cxc');
      setCredits(data);
    } catch (e) {
      console.error('Error al cargar CxC:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCredits();
  }, []);

  const handleCreateHistorical = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(histAmount);
    if (isNaN(amount) || amount <= 0) {
      showToast('warning', 'Monto Requerido', 'El saldo histórico debe ser mayor a 0');
      return;
    }
    if (!histClient.trim() || !histDocNumber.trim()) {
      showToast('warning', 'Datos Incompletos', 'Cliente y número de documento son obligatorios');
      return;
    }

    setSavingHist(true);
    try {
      await api.post('/api/cxc/historical', {
        client_name: histClient.trim(),
        client_rif: histRif.trim() || null,
        doc_type: histDocType,
        doc_number: histDocNumber.trim(),
        emission_date: histDate,
        amount_usd: amount,
      });

      showToast('success', 'Deuda Cargada', `Deuda histórica de ${histClient} agregada a CxC sin distorsionar ventas`);
      setShowHistoricalModal(false);
      setHistClient('');
      setHistRif('');
      setHistDocNumber('');
      setHistAmount('');
      await loadCredits();
    } catch (err: any) {
      showToast('error', 'Error al Guardar', err.message || 'No se pudo cargar la deuda');
    } finally {
      setSavingHist(false);
    }
  };

  // Filtrado
  const filtered = credits.filter((c) => {
    if (filterPendingOnly && c.pending_balance_usd <= 0) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        c.client_name.toLowerCase().includes(q) ||
        c.doc_number.toLowerCase().includes(q) ||
        (c.client_rif && c.client_rif.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const totalPendingUsd = credits.reduce((acc, c) => acc + (c.pending_balance_usd || 0), 0);
  const totalOriginalUsd = credits.reduce((acc, c) => acc + (c.original_amount_usd || 0), 0);
  const totalAbonadoUsd = credits.reduce((acc, c) => acc + (c.total_abonado_usd || 0), 0);

  return (
    <div className="space-y-6">
      {/* Tarjetas Resumen */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-3xl border border-gray-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
              Total Cartera Pendiente (CxC)
            </span>
            <p className="text-2xl font-black text-rose-700 mt-0.5">
              {formatUSD(totalPendingUsd)}
            </p>
            <p className="text-[10px] text-gray-400">
              Equivalente: {formatVES(totalPendingUsd * bcvRate)}
            </p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-gray-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <CreditCard className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
              Total Cobrado / Abonado
            </span>
            <p className="text-2xl font-black text-emerald-700 mt-0.5">
              {formatUSD(totalAbonadoUsd)}
            </p>
            <p className="text-[10px] text-gray-400">
              Deuda Original: {formatUSD(totalOriginalUsd)}
            </p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-gray-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center font-bold">
            <Filter className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
              Documentos en Cartera
            </span>
            <p className="text-2xl font-black text-purple-900 mt-0.5">
              {credits.filter((c) => c.pending_balance_usd > 0).length} pendientes
            </p>
            <p className="text-[10px] text-gray-400">
              {credits.length} registros totales
            </p>
          </div>
        </div>
      </div>

      {/* Lista y Acciones */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-200 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-black text-gray-900">
              Cuentas por Cobrar & Créditos Activos
            </h2>
            <p className="text-xs text-gray-500">
              Control de clientes, cobros parciales y liquidación de cuotas
            </p>
          </div>

          <div className="flex items-center gap-2">
            {hasRole(['administradora', 'directivo']) && (
              <button
                type="button"
                onClick={() => setShowHistoricalModal(true)}
                className="px-3.5 py-2 bg-purple-50 hover:bg-purple-100 text-purple-900 border border-purple-200 rounded-xl text-xs font-black transition flex items-center gap-1.5 cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>+ Cargar Deuda Histórica</span>
              </button>
            )}
          </div>
        </div>

        {/* Barra de Filtros */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar por cliente, RIF o N° documento..."
              className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-xl text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-tev-green focus:outline-none"
            />
          </div>

          <label className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl cursor-pointer">
            <input
              type="checkbox"
              checked={filterPendingOnly}
              onChange={(e) => setFilterPendingOnly(e.target.checked)}
              className="w-4 h-4 text-tev-green rounded border-gray-300 focus:ring-tev-green"
            />
            <span className="text-xs font-bold text-gray-700 whitespace-nowrap">
              Solo Saldos Pendientes
            </span>
          </label>
        </div>

        {/* Tabla */}
        {loading ? (
          <p className="text-xs text-gray-400 py-8 text-center">Cargando cuentas por cobrar...</p>
        ) : filtered.length === 0 ? (
          <p className="text-xs text-gray-400 py-12 text-center">
            No se encontraron documentos en cuentas por cobrar con los filtros seleccionados.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-gray-600 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Documento</th>
                  <th className="p-3">Cliente / Deudor</th>
                  <th className="p-3 text-right">Monto Original</th>
                  <th className="p-3 text-right">Total Abonado</th>
                  <th className="p-3 text-right">Saldo Pendiente</th>
                  <th className="p-3 text-center">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/50 transition">
                    <td className="p-3">
                      <span className="font-bold text-gray-900 block">
                        {c.doc_type} #{c.doc_number}
                      </span>
                      <span className="text-[10px] text-gray-400">{c.date}</span>
                    </td>
                    <td className="p-3">
                      <span className="font-bold text-gray-800 block">{c.client_name}</span>
                      {c.client_rif && (
                        <span className="text-[10px] text-gray-400">{c.client_rif}</span>
                      )}
                      {c.is_cashea && (
                        <span className="inline-block mt-0.5 px-1.5 py-0.2 bg-amber-100 text-amber-800 text-[9px] font-black rounded">
                          Cashea
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right text-gray-600">
                      {formatUSD(c.original_amount_usd)}
                    </td>
                    <td className="p-3 text-right text-emerald-700 font-bold">
                      {formatUSD(c.total_abonado_usd)}
                    </td>
                    <td className="p-3 text-right">
                      {c.pending_balance_usd > 0 ? (
                        <div>
                          <span className="font-black text-rose-700 block">
                            {formatUSD(c.pending_balance_usd)}
                          </span>
                          <span className="text-[10px] text-gray-400">
                            Bs. {formatNumber(c.pending_balance_usd * bcvRate)}
                          </span>
                        </div>
                      ) : (
                        <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-black">
                          SOLVENTE
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-center">
                      {c.pending_balance_usd > 0 ? (
                        <button
                          type="button"
                          onClick={() => setSelectedCredit(c)}
                          className="px-3 py-1.5 bg-purple-700 hover:bg-purple-800 text-white rounded-xl text-xs font-black shadow-xs transition cursor-pointer"
                        >
                          Abonar / Cobrar
                        </button>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Abono */}
      {selectedCredit && (
        <AbonoCxcModal
          credit={selectedCredit}
          onClose={() => setSelectedCredit(null)}
          onSuccess={loadCredits}
        />
      )}

      {/* Modal Deuda Histórica Onboarding */}
      {showHistoricalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full space-y-4">
            <h3 className="text-lg font-black text-gray-900">
              Cargar Deuda Histórica en CxC
            </h3>
            <p className="text-xs text-gray-500">
              Registra una cuenta por cobrar previa sin sumar a las ventas ni a la caja del período actual.
            </p>

            <form onSubmit={handleCreateHistorical} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Nombre del Cliente: *</label>
                <input
                  type="text"
                  value={histClient}
                  onChange={(e) => setHistClient(e.target.value)}
                  required
                  placeholder="Ej: Constructora San Diego"
                  className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">RIF / Cédula:</label>
                <input
                  type="text"
                  value={histRif}
                  onChange={(e) => setHistRif(e.target.value)}
                  placeholder="Ej: J-29381029-4"
                  className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Tipo Documento:</label>
                  <select
                    value={histDocType}
                    onChange={(e) => setHistDocType(e.target.value)}
                    className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white"
                  >
                    <option value="NOTA_ENTREGA">Nota de Entrega</option>
                    <option value="FACTURA_FISCAL">Factura Fiscal</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">N° Documento: *</label>
                  <input
                    type="text"
                    value={histDocNumber}
                    onChange={(e) => setHistDocNumber(e.target.value)}
                    required
                    placeholder="Ej: NE-3100"
                    className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Monto Deuda ($ USD): *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={histAmount}
                    onChange={(e) => setHistAmount(e.target.value)}
                    required
                    placeholder="0.00"
                    className="w-full p-2.5 border border-purple-300 rounded-xl text-sm font-black text-purple-950 bg-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Fecha de Origen: *</label>
                  <input
                    type="date"
                    value={histDate}
                    onChange={(e) => setHistDate(e.target.value)}
                    required
                    className="w-full p-2.5 border border-gray-300 rounded-xl text-xs bg-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowHistoricalModal(false)}
                  className="px-4 py-2 text-xs font-bold text-gray-600 rounded-xl hover:bg-gray-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={savingHist}
                  className="px-5 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-xl text-xs font-bold shadow-md cursor-pointer"
                >
                  {savingHist ? 'Guardando...' : 'Cargar en CxC'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
