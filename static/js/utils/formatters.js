export function formatUSD(amount) {
    const num = parseFloat(amount) || 0;
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(num);
}

export function formatVES(amount) {
    const num = parseFloat(amount) || 0;
    return new Intl.NumberFormat('es-VE', {
        style: 'currency',
        currency: 'VES',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(num);
}

export function parseDecimal(input) {
    if (!input) return 0.0;
    if (typeof input === 'number') return input;
    const cleaned = input.toString().replace(/\s/g, '').replace(/,/g, '.');
    const val = parseFloat(cleaned);
    return isNaN(val) ? 0.0 : val;
}
