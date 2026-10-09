import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/common/Toast';
import { Lock, User } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { showToast } = useToast();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    try {
      await login(username.trim(), password);
      showToast('success', 'Sesión Iniciada', 'Bienvenido al Sistema de Tesorería de TEV');
    } catch (err: any) {
      const msg = err.message || 'Credenciales incorrectas o usuario inactivo';
      setErrorMsg(msg);
      showToast('error', 'Error de Acceso', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-slate-100 to-teal-50">
      <div className="bg-white rounded-3xl shadow-2xl p-8 max-w-md w-full border border-gray-100 my-auto">
        <div className="text-center mb-6">
          <img
            src="/logo.jpg"
            alt="Todo Eléctrico Valencia"
            className="h-20 mx-auto mb-3 object-contain rounded-xl shadow-sm"
          />
          <h1 className="text-2xl font-bold text-gray-800">Control de Tesorería y Gastos</h1>
          <p className="text-gray-500 text-sm mt-1">Por favor ingrese sus datos de acceso</p>
        </div>

        {errorMsg && (
          <div className="mb-4 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 rounded-lg text-sm">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-700 font-semibold mb-1 text-sm">Usuario</label>
            <div className="relative">
              <User className="w-5 h-5 text-gray-400 absolute left-3 top-3" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="Ej: cajera1, administradora, directivo"
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-tev-green focus:outline-none text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-700 font-semibold mb-1 text-sm">Contraseña</label>
            <div className="relative">
              <Lock className="w-5 h-5 text-gray-400 absolute left-3 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-tev-green focus:outline-none text-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-tev-green hover:bg-tev-darkgreen text-white font-bold rounded-xl shadow-lg transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <span>{loading ? 'Verificando credenciales...' : 'Ingresar al Sistema'}</span>
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-gray-100 text-center">
          <p className="text-xs text-gray-400 font-medium">
            Todo Eléctrico Valencia, C.A. • Acceso Seguro RBAC
          </p>
        </div>
      </div>
    </div>
  );
};
