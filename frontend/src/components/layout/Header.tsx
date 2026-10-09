import React from 'react';
import { LogOut, RefreshCw, User as UserIcon } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTreasury } from '../../context/TreasuryContext';
import { formatNumber } from '../../utils/formatters';
import { APP_CONFIG } from '../../config';

export type ActiveTab = 'ventas' | 'egresos' | 'cxc' | 'cuentas' | 'cierre';

interface HeaderProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab }) => {
  const { user, logout, hasRole } = useAuth();
  const { bcvRate, setIsBcvModalOpen } = useTreasury();

  if (!user) return null;

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30 shadow-sm no-print">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
        {/* Fila Principal */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between py-2.5 sm:py-0 sm:h-20 gap-2 sm:gap-4">
          
          {/* Logo y Marca */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 sm:gap-3">
              <img
                src={APP_CONFIG.logoUrl}
                alt={APP_CONFIG.companyName}
                className="h-9 sm:h-12 object-contain rounded-lg shadow-xs"
              />
              <div>
                <h1 className="text-sm sm:text-lg font-black text-gray-900 leading-tight tracking-tight">
                  {APP_CONFIG.companyShortName}
                </h1>
                <p className="text-[10px] sm:text-xs text-tev-green font-bold">
                  {APP_CONFIG.systemSlogan}
                </p>
              </div>
            </div>


            {/* Móvil: Logout rápido */}
            <div className="flex sm:hidden items-center gap-2">
              <button
                onClick={() => setIsBcvModalOpen(true)}
                className="px-2 py-1 bg-emerald-50 text-emerald-900 border border-emerald-200 rounded-lg text-xs font-black flex items-center gap-1"
              >
                <span>🇻🇪</span>
                <span>Bs. {formatNumber(bcvRate)}</span>
              </button>
              <button
                onClick={logout}
                className="p-1.5 text-gray-500 hover:text-rose-600 rounded-lg"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Indicadores de Escritorio */}
          <div className="hidden sm:flex items-center gap-3">
            {/* Botón Tasa BCV */}
            <button
              type="button"
              onClick={() => setIsBcvModalOpen(true)}
              className="px-3.5 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 rounded-xl text-xs font-black shadow-xs transition flex items-center gap-2 cursor-pointer"
            >
              <span className="text-base">🇻🇪</span>
              <div className="text-left">
                <span className="text-[10px] text-emerald-700 font-bold block uppercase tracking-wide leading-none">
                  Tasa Oficial BCV
                </span>
                <span className="text-sm font-black leading-tight">
                  Bs. {formatNumber(bcvRate)}
                </span>
              </div>
              <RefreshCw className="w-3.5 h-3.5 text-emerald-600 ml-1" />
            </button>

            {/* Usuario y Rol */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="w-8 h-8 rounded-lg bg-tev-green/10 text-tev-green flex items-center justify-center font-bold">
                <UserIcon className="w-4 h-4" />
              </div>
              <div className="text-left">
                <span className="text-xs font-bold text-gray-900 block leading-tight">
                  {user.full_name}
                </span>
                <span className="text-[10px] uppercase font-black tracking-wider text-tev-darkgreen">
                  {user.role}
                </span>
              </div>
            </div>

            {/* Botón Salir */}
            <button
              onClick={logout}
              className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition"
              title="Cerrar Sesión"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>

        </div>

        {/* Pestañas de Navegación */}
        <nav className="flex space-x-1 sm:space-x-2 overflow-x-auto py-2 border-t border-gray-100 scrollbar-none">
          <button
            onClick={() => setActiveTab('ventas')}
            className={`px-3 sm:px-4 py-2 rounded-xl text-xs font-black transition whitespace-nowrap ${
              activeTab === 'ventas'
                ? 'bg-tev-green text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            🛒 Facturación & Ventas
          </button>

          {hasRole(['administradora', 'directivo']) && (
            <button
              onClick={() => setActiveTab('egresos')}
              className={`px-3 sm:px-4 py-2 rounded-xl text-xs font-black transition whitespace-nowrap ${
                activeTab === 'egresos'
                  ? 'bg-tev-green text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              💸 Egresos & SENIAT
            </button>
          )}

          <button
            onClick={() => setActiveTab('cxc')}
            className={`px-3 sm:px-4 py-2 rounded-xl text-xs font-black transition whitespace-nowrap ${
              activeTab === 'cxc'
                ? 'bg-tev-green text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            📋 Cuentas por Cobrar (CxC)
          </button>

          {hasRole(['administradora', 'directivo']) && (
            <button
              onClick={() => setActiveTab('cuentas')}
              className={`px-3 sm:px-4 py-2 rounded-xl text-xs font-black transition whitespace-nowrap ${
                activeTab === 'cuentas'
                  ? 'bg-tev-green text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              🏦 Cajas y Bancos
            </button>
          )}

          <button
            onClick={() => setActiveTab('cierre')}
            className={`px-3 sm:px-4 py-2 rounded-xl text-xs font-black transition whitespace-nowrap ${
              activeTab === 'cierre'
                ? 'bg-tev-green text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            📊 Cuadre Diario de Caja
          </button>
        </nav>

      </div>
    </header>
  );
};
