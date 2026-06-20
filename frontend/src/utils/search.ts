export const normalizeText = (value?: string | number | null): string => {
  if (value === null || value === undefined) {
    return '';
  }

  return String(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
};

export const splitTokens = (value?: string | number | null): string[] => {
  const normalized = normalizeText(value);
  return normalized.length === 0 ? [] : normalized.split(/\s+/).filter(Boolean);
};

export const extractSearchWords = (input: string): string[] => splitTokens(input);

export const matchesAllSearchWords = (
  searchWords: string[],
  tokens: string[],
  includes: string[] = []
): boolean => {
  if (searchWords.length === 0) {
    return true;
  }

  const dedupedTokens = Array.from(new Set(tokens.filter(Boolean)));
  const dedupedIncludes = Array.from(new Set(includes.filter(Boolean)));

  return searchWords.every((word) => {
    const tokenMatch = dedupedTokens.some((token) => token.startsWith(word));
    const includeMatch = dedupedIncludes.some((value) => value.includes(word));
    return tokenMatch || includeMatch;
  });
};

export const pacienteMatchesSearch = (
  paciente: { nombre?: string | null; apellido?: string | null; dni?: string | null },
  searchWords: string[]
): boolean => {
  const tokens = [
    ...splitTokens(paciente?.nombre),
    ...splitTokens(paciente?.apellido),
  ];

  const includes = paciente?.dni ? [normalizeText(paciente.dni)] : [];

  return matchesAllSearchWords(searchWords, tokens, includes);
};

export const medicoMatchesSearch = (
  medico: {
    nombre?: string | null;
    apellido?: string | null;
    matricula?: string | null;
    especialidad?: { nombre?: string | null } | null;
  },
  searchWords: string[]
): boolean => {
  const tokens = [
    ...splitTokens(medico?.nombre),
    ...splitTokens(medico?.apellido),
    ...(medico?.especialidad ? splitTokens(medico.especialidad.nombre) : []),
  ];

  const includes = medico?.matricula ? [normalizeText(medico.matricula)] : [];

  return matchesAllSearchWords(searchWords, tokens, includes);
};

export const genericMatchesSearch = (
  fields: Array<string | number | null | undefined>,
  searchWords: string[],
  includes: Array<string | number | null | undefined> = []
): boolean => {
  const tokens = fields.flatMap(splitTokens);
  const includeValues = includes.map(normalizeText);
  return matchesAllSearchWords(searchWords, tokens, includeValues);
};

/**
 * Función auxiliar para truncar texto de forma segura
 * Previene errores cuando el valor no es una cadena
 * @param value - Valor a truncar (puede ser string, number, null, undefined, etc.)
 * @param maxLength - Longitud máxima del texto
 * @param suffix - Sufijo a agregar si el texto se trunca (por defecto '...')
 * @returns Texto truncado o el valor convertido a string si no es una cadena
 */
export const safeSubstring = (
  value: string | number | null | undefined,
  maxLength: number,
  suffix: string = '...'
): string => {
  if (value === null || value === undefined) {
    return '';
  }
  
  // Convertir a string si no lo es
  const strValue = typeof value === 'string' ? value : String(value);
  
  // Si el valor es más corto que maxLength, retornarlo completo
  if (strValue.length <= maxLength) {
    return strValue;
  }
  
  // Truncar y agregar sufijo
  return strValue.substring(0, maxLength) + suffix;
};


