export function formatNumber(val: number | string | undefined | null): string {
  if (val === undefined || val === null || isNaN(Number(val))) return '0,00';
  return Number(val).toLocaleString('es-VE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatUSD(val: number | string | undefined | null): string {
  return `$${formatNumber(val)}`;
}

export function formatVES(val: number | string | undefined | null): string {
  return `Bs. ${formatNumber(val)}`;
}

export function getTodayDateString(): string {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
