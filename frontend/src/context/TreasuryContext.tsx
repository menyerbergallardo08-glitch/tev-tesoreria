import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { TreasuryAccount, Category, Supplier } from '../types';
import { api } from '../api/client';
import { useAuth } from './AuthContext';

interface TreasuryContextType {
  accounts: TreasuryAccount[];
  categories: Category[];
  suppliers: Supplier[];
  bcvRate: number;
  loadingBcv: boolean;
  isBcvModalOpen: boolean;
  loadAccounts: () => Promise<void>;
  loadCategories: () => Promise<void>;
  loadSuppliers: () => Promise<void>;
  loadBcvRate: (sync?: boolean) => Promise<number>;
  updateBcvRate: (newRate: number) => Promise<void>;
  setIsBcvModalOpen: (open: boolean) => void;
}

const TreasuryContext = createContext<TreasuryContextType | undefined>(undefined);

export const TreasuryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState<TreasuryAccount[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [bcvRate, setBcvRate] = useState<number>(827.74);
  const [loadingBcv, setLoadingBcv] = useState(false);
  const [isBcvModalOpen, setIsBcvModalOpen] = useState(false);

  const loadAccounts = useCallback(async () => {
    try {
      const data = await api.get<TreasuryAccount[]>('/api/accounts');
      setAccounts(data);
    } catch (e) {
      console.error('Error al cargar cuentas:', e);
    }
  }, []);

  const loadCategories = useCallback(async () => {
    try {
      const data = await api.get<Category[]>('/api/categories');
      setCategories(data);
    } catch (e) {
      console.error('Error al cargar categorías:', e);
    }
  }, []);

  const loadSuppliers = useCallback(async () => {
    try {
      const data = await api.get<Supplier[]>('/api/suppliers');
      setSuppliers(data);
    } catch (e) {
      console.error('Error al cargar proveedores:', e);
    }
  }, []);

  const loadBcvRate = useCallback(async (_sync = false): Promise<number> => {
    setLoadingBcv(true);
    try {
      const res = await api.get<{ rate: number }>('/api/system/bcv-rate');
      if (res.rate && res.rate > 0) {
        setBcvRate(res.rate);
        return res.rate;
      }
    } catch (e) {
      console.error('Error al sincronizar BCV:', e);
    } finally {
      setLoadingBcv(false);
    }
    return bcvRate;
  }, [bcvRate]);

  const updateBcvRate = async (newRate: number) => {
    await api.post('/api/system/bcv-rate', { rate: newRate });
    setBcvRate(newRate);
  };

  useEffect(() => {
    if (user) {
      loadAccounts();
      loadCategories();
      loadSuppliers();
      loadBcvRate();
    }
  }, [user, loadAccounts, loadCategories, loadSuppliers, loadBcvRate]);

  return (
    <TreasuryContext.Provider
      value={{
        accounts,
        categories,
        suppliers,
        bcvRate,
        loadingBcv,
        isBcvModalOpen,
        loadAccounts,
        loadCategories,
        loadSuppliers,
        loadBcvRate,
        updateBcvRate,
        setIsBcvModalOpen,
      }}
    >
      {children}
    </TreasuryContext.Provider>
  );
};

export const useTreasury = () => {
  const context = useContext(TreasuryContext);
  if (!context) {
    throw new Error('useTreasury debe ser utilizado dentro de un TreasuryProvider');
  }
  return context;
};
