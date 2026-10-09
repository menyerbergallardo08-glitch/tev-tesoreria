import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TreasuryProvider } from './context/TreasuryContext';
import { ToastProvider } from './components/common/Toast';
import { Header, ActiveTab } from './components/layout/Header';
import { BcvModal } from './components/modals/BcvModal';
import { LoginPage } from './pages/LoginPage';
import { PosSalesPage } from './pages/PosSalesPage';
import { ExpensesPage } from './pages/ExpensesPage';
import { CxcPage } from './pages/CxcPage';
import { AccountsPage } from './pages/AccountsPage';
import { CashClosePage } from './pages/CashClosePage';

const MainLayout: React.FC = () => {
  const { user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>('ventas');

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-tev-green border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-bold text-gray-500">Cargando Sistema de Tesorería TEV...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-gray-800">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'ventas' && <PosSalesPage />}
        {activeTab === 'egresos' && <ExpensesPage />}
        {activeTab === 'cxc' && <CxcPage />}
        {activeTab === 'cuentas' && <AccountsPage />}
        {activeTab === 'cierre' && <CashClosePage />}
      </main>

      <footer className="py-4 border-t border-gray-200 bg-white text-center text-xs text-gray-400 no-print">
        Todo Eléctrico Valencia, C.A. • Sistema de Tesorería, Gastos y Flujo de Caja v3.2 (Vite SPA)
      </footer>

      <BcvModal />
    </div>
  );
};

export function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <TreasuryProvider>
          <MainLayout />
        </TreasuryProvider>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
