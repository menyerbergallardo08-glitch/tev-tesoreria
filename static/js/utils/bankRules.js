/**
 * Matriz de Cuentas y Bancos según Regla de Negocio TEV:
 * - Punto de Venta: Solo Bancaribe y Banco de Venezuela
 * - Notas de Entrega (Pago Móvil / Transferencia): Solo Mercantil
 * - Facturas Fiscales (Pago Móvil / Transferencia): Solo Banesco, Venezuela y BNC
 * - Pagos a Proveedores: Mercantil y demás cuentas habilitadas
 */
export function filterAccountsByOperation(accounts, operationType, docType, paymentMethod) {
    if (!accounts || !Array.isArray(accounts)) return [];
    
    // Solo cuentas activas
    const activeAccounts = accounts.filter(a => a.is_active);

    if (operationType === 'EXPENSE') {
        // En egresos se muestran todas las cuentas bancarias y efectivo activas (incluyendo Mercantil)
        return activeAccounts;
    }

    if (operationType === 'SALE') {
        if (paymentMethod === 'EFECTIVO_USD') {
            return activeAccounts.filter(a => a.account_type === 'EFECTIVO' && a.currency === 'USD');
        }
        if (paymentMethod === 'EFECTIVO_VES') {
            return activeAccounts.filter(a => a.account_type === 'EFECTIVO' && a.currency === 'VES');
        }
        if (paymentMethod === 'PUNTO_VENTA') {
            // Solo Bancaribe y Venezuela
            return activeAccounts.filter(a => 
                a.name.toLowerCase().includes('bancaribe') || 
                a.name.toLowerCase().includes('venezuela')
            );
        }
        if (paymentMethod === 'PAGO_MOVIL' || paymentMethod === 'TRANSFERENCIA') {
            if (docType === 'NOTA_ENTREGA') {
                // Para Notas de Entrega: Mercantil
                return activeAccounts.filter(a => a.name.toLowerCase().includes('mercantil'));
            }
            if (docType === 'FACTURA_FISCAL') {
                // Para Facturas: Banesco, Venezuela y BNC
                return activeAccounts.filter(a => 
                    a.name.toLowerCase().includes('banesco') ||
                    a.name.toLowerCase().includes('venezuela') ||
                    a.name.toLowerCase().includes('bnc') ||
                    a.name.toLowerCase().includes('nacional de crédito')
                );
            }
        }
        if (paymentMethod === 'CASHEA') {
            return activeAccounts.filter(a => a.name.toLowerCase().includes('cashea'));
        }
        if (paymentMethod === 'ZELLE') {
            return activeAccounts.filter(a => a.name.toLowerCase().includes('zelle') || a.name.toLowerCase().includes('panamá'));
        }
    }

    return activeAccounts;
}
