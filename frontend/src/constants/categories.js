/** Categorías de facturas — espejo de backend/constants.py */
export const CATEGORIES = {
  electricidad: { label: 'Electricidad', emoji: '⚡', color: '#fbbf24' },
  gas:          { label: 'Gas',           emoji: '🔥', color: '#f97316' },
  agua:         { label: 'Agua',          emoji: '💧', color: '#38bdf8' },
  internet:     { label: 'Internet',      emoji: '🌐', color: '#a78bfa' },
  telefono:     { label: 'Teléfono',      emoji: '📱', color: '#22d3ee' },
  alquiler:     { label: 'Alquiler',      emoji: '🏠', color: '#34d399' },
  expensas:     { label: 'Expensas',      emoji: '🏢', color: '#818cf8' },
  seguro:       { label: 'Seguro',        emoji: '🛡️', color: '#86efac' },
  streaming:    { label: 'Streaming',     emoji: '📺', color: '#f472b6' },
  otro:         { label: 'Otro',          emoji: '🏷️', color: '#9ca3af' },
}

export const CATEGORY_KEYS = Object.keys(CATEGORIES)
