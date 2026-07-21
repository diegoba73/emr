import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Turno, Paciente, Medico, Especialidad, User, CentroFisico, TipoAtencion, ArchivoMedico, Consulta, Solicitud, Recurso, TipoExamen } from '../types';
import { authService, LoginCredentials } from '../services/auth';
import { getTiposExamen } from '../services/apiService';

const IS_DEV = process.env.NODE_ENV === 'development';

const devLog = (...args: unknown[]) => {
  if (IS_DEV) console.log(...args);
};

const devWarn = (...args: unknown[]) => {
  if (IS_DEV) console.warn(...args);
};

const devError = (message: string, err?: unknown) => {
  if (!IS_DEV) return;
  const detail = err instanceof Error ? err.message : '';
  console.error(detail ? `${message}: ${detail}` : message);
};

interface DataContextType {
  turnos: Turno[];
  pacientes: Paciente[];
  pacientesLoadError: string | null;
  medicos: Medico[];
  especialidades: Especialidad[];
  centrosFisicos: CentroFisico[];
  tiposAtencion: TipoAtencion[];
  recursos: Recurso[];
  archivosMedicos: ArchivoMedico[];
  consultas: Consulta[];
  solicitudes: Solicitud[];
  tiposExamen: TipoExamen[];
  currentUser: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loading: {
    turnos: boolean;
    pacientes: boolean;
    medicos: boolean;
    especialidades: boolean;
    centrosFisicos: boolean;
    tiposAtencion: boolean;
    recursos: boolean;
    archivosMedicos: boolean;
    consultas: boolean;
    solicitudes: boolean;
    tiposExamen: boolean;
    user: boolean;
  };
  lastUpdate: {
    turnos: Date;
    pacientes: Date;
    medicos: Date;
    especialidades: Date;
    centrosFisicos: Date;
    tiposAtencion: Date;
    recursos: Date;
    archivosMedicos: Date;
    consultas: Date;
    solicitudes: Date;
    tiposExamen: Date;
  };
  refreshAll: () => Promise<void>;
  refreshTurnos: () => Promise<void>;
  loadTurnos: () => void;
  loadPacientes: () => void;
  loadMedicos: () => void;
  loadEspecialidades: () => void;
  loadCentrosFisicos: () => void;
  loadTiposAtencion: () => void;
  loadRecursos: () => void;
  loadArchivosMedicos: () => void;
  loadConsultas: () => void;
  loadSolicitudes: () => void;
  loadTiposExamen: () => void;
  loadCurrentUser: () => void;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  setTurnos: React.Dispatch<React.SetStateAction<Turno[]>>;
  setPacientes: React.Dispatch<React.SetStateAction<Paciente[]>>;
  setArchivosMedicos: React.Dispatch<React.SetStateAction<ArchivoMedico[]>>;
  setConsultas: React.Dispatch<React.SetStateAction<Consulta[]>>;
  setSolicitudes: React.Dispatch<React.SetStateAction<Solicitud[]>>;
  setCurrentUser: React.Dispatch<React.SetStateAction<User | null>>;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const useData = () => {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
};

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [pacientesLoadError, setPacientesLoadError] = useState<string | null>(null);
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [centrosFisicos, setCentrosFisicos] = useState<CentroFisico[]>([]);
  const [tiposAtencion, setTiposAtencion] = useState<TipoAtencion[]>([]);
  const [recursos, setRecursos] = useState<Recurso[]>([]);
  const [archivosMedicos, setArchivosMedicos] = useState<ArchivoMedico[]>([]);
  const [consultas, setConsultas] = useState<Consulta[]>([]);
  const [solicitudes, setSolicitudes] = useState<Solicitud[]>([]);
  const [tiposExamen, setTiposExamen] = useState<TipoExamen[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState({
    turnos: false,
    pacientes: false,
    medicos: false,
    especialidades: false,
    centrosFisicos: false,
    tiposAtencion: false,
    recursos: false,
    archivosMedicos: false,
    consultas: false,
    solicitudes: false,
    tiposExamen: false,
    user: false
  });
  const [lastUpdate, setLastUpdate] = useState({
    turnos: new Date(),
    pacientes: new Date(),
    medicos: new Date(),
    especialidades: new Date(),
    centrosFisicos: new Date(),
    tiposAtencion: new Date(),
    recursos: new Date(),
    archivosMedicos: new Date(),
    consultas: new Date(),
    solicitudes: new Date(),
    tiposExamen: new Date()
  });

  const loadCurrentUser = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, user: true }));
      devLog('🔍 Intentando cargar usuario actual...');
      
      const userData = await authService.getCurrentUser();
      if (userData) {
        devLog('✅ Usuario cargado');
        // Normalizar rol a mayúsculas para consistencia en toda la app
        const normalized = { ...userData, rol: (userData?.rol || '').toUpperCase() as "ADMIN" | "SECRETARIA" | "MEDICO" | "PACIENTE" | "ENFERMERIA" };
        setCurrentUser(normalized);
      } else {
        devLog('⚠️ No hay usuario autenticado');
        setCurrentUser(null);
      }
    } catch (error: unknown) {
      const err = error as { code?: string; message?: string; response?: { status?: number } };
      // Verificar si es un error de red (servidor no disponible)
      if (err?.code === 'ERR_NETWORK' || err?.message === 'Network Error' || err?.code === 'ERR_CONNECTION_RESET') {
        devWarn('⚠️ Servidor no disponible. Verifica que el backend esté corriendo en http://localhost:8000');
        // No limpiar tokens en caso de error de red, puede ser temporal
      } else if (err?.response?.status === 401) {
        // Usuario no autenticado - esto es normal si no hay sesión
        devLog('⚠️ Usuario no autenticado (401)');
        setCurrentUser(null);
        // Limpiar tokens solo si es un error de autenticación
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
      } else {
        devError('Error cargando usuario', error);
        setCurrentUser(null);
        // Limpiar tokens si hay otro tipo de error
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
      }
    } finally {
      setLoading(prev => ({ ...prev, user: false }));
    }
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    try {
      setLoading(prev => ({ ...prev, user: true }));
      await authService.login(credentials);
      const userData = await authService.getCurrentUser();
      if (userData) {
        const normalized = { ...userData, rol: (userData?.rol || '').toUpperCase() as "ADMIN" | "SECRETARIA" | "MEDICO" | "PACIENTE" | "ENFERMERIA" };
        setCurrentUser(normalized);
      } else {
        setCurrentUser(null);
      }
      devLog('✅ Login exitoso');
    } catch (error: unknown) {
      devError('Error en login', error);
      setCurrentUser(null);
      throw error; // Re-lanzar para que el componente pueda manejarlo
    } finally {
      setLoading(prev => ({ ...prev, user: false }));
    }
  }, []);



  // OPTIMIZACIÓN: Aumentar PAGE_SIZE para reducir número de requests
  const PAGE_SIZE = 1000; // Aumentado de 200 a 1000 para cargar más datos por request
  const API_BASE = process.env.REACT_APP_API_URL?.replace(/\/api\/?$/, '') || 'http://localhost:8000';

  const normalizePaginationUrl = useCallback((url: string): string => {
    if (!url) return url;
    if (url.startsWith('http')) {
      try {
        const parsed = new URL(url);
        return `${API_BASE}${parsed.pathname}${parsed.search}`;
      } catch {
        return url;
      }
    }
    return url.startsWith('/') ? `${API_BASE}${url}` : `${API_BASE}/${url}`;
  }, [API_BASE]);

  const fetchPaginated = useCallback(async <T,>(initialPath: string): Promise<{ items: T[]; total: number }> => {
    const items: T[] = [];
    let total = 0;
    let nextUrl: string | null = `${API_BASE}${initialPath}`;
    let pageCount = 0;
    const MAX_PAGES = 50; // Límite de seguridad para evitar loops infinitos

    while (nextUrl && pageCount < MAX_PAGES) {
      pageCount++;
      const response: Response = await fetch(nextUrl, { credentials: 'include' });
      if (!response.ok) {
        await response.text();
        devError(`Error HTTP ${response.status} en ${initialPath}`);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json() as T[] | { results?: T[]; count?: number; next?: string };
      const pageResults: T[] = Array.isArray(data)
        ? data
        : Array.isArray(data?.results)
          ? data.results
          : [];

      items.push(...pageResults);
      const paginatedData = Array.isArray(data) ? null : data;
      total = paginatedData && typeof paginatedData.count === 'number' ? paginatedData.count : items.length;

      const nextValue: unknown = paginatedData?.next;
      if (typeof nextValue === 'string' && nextValue.length > 0) {
        nextUrl = normalizePaginationUrl(nextValue);
      } else {
        nextUrl = null;
      }
    }

    if (pageCount >= MAX_PAGES) {
      devWarn(`⚠️ Se alcanzó el límite de páginas (${MAX_PAGES}) para ${initialPath}`);
    }

    return { items, total };
  }, [normalizePaginationUrl]);

  const loadTurnos = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, turnos: true }));
      devLog('🔍 Intentando cargar turnos...');
      // Alcance por rol lo define el backend (médico: solo sus turnos; agenda global: admin/secretaría/enfermería)
      const { items, total } = await fetchPaginated<Turno>(
        `/api/turnos/?page_size=${PAGE_SIZE}`
      );
      devLog('✅ Total turnos cargados:', items.length, 'registros (total reportado:', total, ')');
      setTurnos(items);
      setLastUpdate(prev => ({ ...prev, turnos: new Date() }));
    } catch (error) {
      devError('Error loading turnos', error);
    } finally {
      setLoading(prev => ({ ...prev, turnos: false }));
    }
  }, [fetchPaginated, currentUser]);

  const loadPacientes = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, pacientes: true }));
      setPacientesLoadError(null);
      devLog('🔍 Intentando cargar pacientes...');

      const { items, total } = await fetchPaginated<Paciente>(
        `/api/pacientes/?page_size=${PAGE_SIZE}`
      );
      devLog(`✅ Pacientes cargados: ${items.length} registros (total reportado: ${total})`);
      setPacientes(items);
      setLastUpdate(prev => ({ ...prev, pacientes: new Date() }));
    } catch (error) {
      devError('Error cargando pacientes', error);
      setPacientes([]);
      setPacientesLoadError(
        'No se pudieron cargar los pacientes. Verificá que el backend esté activo (./emrctl up) y aplicá migraciones (./emrctl repair-migrations).'
      );
    } finally {
      setLoading(prev => ({ ...prev, pacientes: false }));
    }
  }, [fetchPaginated]);

  const loadMedicos = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, medicos: true }));
      devLog('🔍 Intentando cargar médicos...');
      
      // Secretarias, admin y enfermería ven todos los médicos sin necesidad de ?all=true
      // El parámetro ?all=true no es necesario para estos roles
      const { items, total } = await fetchPaginated<Medico>(`/api/medicos/?page_size=${PAGE_SIZE}`);
      devLog('✅ Total médicos cargados:', items.length, 'registros (total reportado:', total, ')');
      setMedicos(items);
      setLastUpdate(prev => ({ ...prev, medicos: new Date() }));
    } catch (error: unknown) {
      devError('Error loading medicos', error);
      setMedicos([]); // Asegurar que siempre sea un array
    } finally {
      setLoading(prev => ({ ...prev, medicos: false }));
    }
  }, []);

  const loadEspecialidades = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, especialidades: true }));
      devLog('🔍 Intentando cargar especialidades...');
      
      // OPTIMIZACIÓN: Usar fetchPaginated para manejar paginación automáticamente
      const { items, total } = await fetchPaginated<Especialidad>(`/api/especialidades/?page_size=${PAGE_SIZE}`);
      devLog('✅ Especialidades cargadas:', items.length, 'registros (total:', total, ')');
      setEspecialidades(items);
      setLastUpdate(prev => ({ ...prev, especialidades: new Date() }));
    } catch (error: unknown) {
      devError('Error loading especialidades', error);
      setEspecialidades([]);
    } finally {
      setLoading(prev => ({ ...prev, especialidades: false }));
    }
  }, [fetchPaginated]);

  const loadCentrosFisicos = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, centrosFisicos: true }));
      devLog('🔍 Intentando cargar centros físicos...');
      
      // OPTIMIZACIÓN: Usar fetchPaginated para manejar paginación automáticamente
      const { items, total } = await fetchPaginated<CentroFisico>(`/api/catalogos/centros-fisicos/?page_size=${PAGE_SIZE}`);
      devLog('✅ Centros físicos cargados:', items.length, 'registros (total:', total, ')');
      setCentrosFisicos(items);
      setLastUpdate(prev => ({ ...prev, centrosFisicos: new Date() }));
    } catch (error: unknown) {
      devError('Error loading centros físicos', error);
      setCentrosFisicos([]);
    } finally {
      setLoading(prev => ({ ...prev, centrosFisicos: false }));
    }
  }, [fetchPaginated]);

  const loadTiposAtencion = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, tiposAtencion: true }));
      devLog('🔍 Intentando cargar tipos de atención...');
      
      // OPTIMIZACIÓN: Usar fetchPaginated para manejar paginación automáticamente
      const { items, total } = await fetchPaginated<TipoAtencion>(`/api/catalogos/tipos-atencion/?page_size=${PAGE_SIZE}`);
      devLog('✅ Tipos de atención cargados:', items.length, 'registros (total:', total, ')');
      setTiposAtencion(items);
      setLastUpdate(prev => ({ ...prev, tiposAtencion: new Date() }));
    } catch (error: unknown) {
      devError('Error loading tipos de atención', error);
      setTiposAtencion([]);
    } finally {
      setLoading(prev => ({ ...prev, tiposAtencion: false }));
    }
  }, [fetchPaginated]);

  const loadRecursos = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, recursos: true }));
      devLog('🔍 Intentando cargar recursos...');
      const { items } = await fetchPaginated<Recurso>('/api/recursos/?page_size=500');
      devLog('✅ Recursos cargados:', items.length, 'registros');
      setRecursos(items);
      setLastUpdate(prev => ({ ...prev, recursos: new Date() }));
    } catch (error: unknown) {
      devError('Error loading recursos', error);
      setRecursos([]);
    } finally {
      setLoading(prev => ({ ...prev, recursos: false }));
    }
  }, [fetchPaginated]);

  const loadTiposExamen = useCallback(async () => {
    try {
      devLog('🚀🚀🚀 INTENTANDO CARGAR EXÁMENES - loadTiposExamen INICIADA 🚀🚀🚀');
      setLoading(prev => ({ ...prev, tiposExamen: true }));
      devLog('🔍 Intentando cargar tipos de examen...');
      devLog('📡 Llamando a getTiposExamen()...');
      
      const items = await getTiposExamen();
      devLog('✅ Tipos de examen cargados:', items.length, 'registros');
      setTiposExamen(items);
      setLastUpdate(prev => ({ ...prev, tiposExamen: new Date() }));
    } catch (error: unknown) {
      devError('Error loading tipos examen', error);
      setTiposExamen([]); // Asegurar que siempre sea un array
    } finally {
      setLoading(prev => ({ ...prev, tiposExamen: false }));
      devLog('🏁 loadTiposExamen finalizada');
    }
  }, []);

  const refreshAll = useCallback(async () => {
    devLog('🔄 Iniciando refreshAll (carga paralela optimizada)...');
    
    // Verificar que el usuario esté autenticado antes de cargar datos
    if (!currentUser) {
      devLog('⚠️ Usuario no autenticado, esperando...');
      return;
    }
    
    // OPTIMIZACIÓN: Cargar solo datos esenciales en paralelo
    // Datos bajo demanda (NO se cargan aquí):
    // - loadPacientes() - pacientes se cargan bajo demanda con búsqueda remota
    // - loadConsultas() - consultas se cargan localmente en cada página
    // - loadArchivosMedicos() - se cargan cuando se necesitan
    // - loadSolicitudes() - se cargan cuando se necesitan
    devLog('📊 Cargando datos esenciales en paralelo...');
    
    try {
      await Promise.all([
        loadTurnos(),
        loadMedicos(),
        loadEspecialidades(),
        loadCentrosFisicos(),
        loadTiposAtencion(),
        loadRecursos(),
        loadTiposExamen(),
      ]);
      
      devLog('✅ refreshAll completado (datos esenciales cargados)');
    } catch (error) {
      devError('Error en refreshAll', error);
      // Continuar aunque algunas cargas fallen
    }
  }, [currentUser, loadTurnos, loadMedicos, loadEspecialidades, loadCentrosFisicos, loadTiposAtencion, loadRecursos, loadTiposExamen]);

  const refreshTurnos = useCallback(async () => {
    devLog('🔄 Refrescando solo turnos...');
    
    if (!currentUser) {
      devLog('⚠️ Usuario no autenticado, no refrescando turnos');
      return;
    }
    
    await loadTurnos();
    devLog('✅ Turnos refrescados');
  }, [currentUser, loadTurnos]);

  const loadArchivosMedicos = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, archivosMedicos: true }));
      const { items } = await fetchPaginated<ArchivoMedico>(`/api/archivos-medicos/archivos/?page_size=${PAGE_SIZE}`);
      setArchivosMedicos(items);
      setLastUpdate(prev => ({ ...prev, archivosMedicos: new Date() }));
    } catch {
      setArchivosMedicos([]);
    } finally {
      setLoading(prev => ({ ...prev, archivosMedicos: false }));
    }
  }, [fetchPaginated]);

  const loadConsultas = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, consultas: true }));
      devLog('🔍 Intentando cargar consultas...');
      
      // Usar fetchPaginated para manejar paginación automáticamente
      const { items, total } = await fetchPaginated<Consulta>(`/api/consultas/?page_size=${PAGE_SIZE}`);
      devLog('✅ Consultas cargadas:', items.length, 'registros (total:', total, ')');
      setConsultas(items);
      setLastUpdate(prev => ({ ...prev, consultas: new Date() }));
    } catch (error: unknown) {
      devError('Error loading consultas', error);
      setConsultas([]);
    } finally {
      setLoading(prev => ({ ...prev, consultas: false }));
    }
  }, [fetchPaginated]);

  const loadSolicitudes = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, solicitudes: true }));
      devLog('🔍 Intentando cargar solicitudes...');
      
      // OPTIMIZACIÓN: Usar fetchPaginated para manejar paginación automáticamente
      const { items, total } = await fetchPaginated<Solicitud>(`/api/solicitudes/?page_size=${PAGE_SIZE}`);
      devLog('✅ Solicitudes cargadas:', items.length, 'registros (total:', total, ')');
      setSolicitudes(items);
      setLastUpdate(prev => ({ ...prev, solicitudes: new Date() }));
    } catch (error: unknown) {
      devError('Error loading solicitudes', error);
      setSolicitudes([]);
    } finally {
      setLoading(prev => ({ ...prev, solicitudes: false }));
    }
  }, [fetchPaginated]);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
      setCurrentUser(null);
      setTurnos([]);
      // setPacientes([]) - pacientes ya no se cargan globalmente
      setMedicos([]);
      setEspecialidades([]);
      setArchivosMedicos([]);
      setConsultas([]);
      setSolicitudes([]);
      setTiposExamen([]);
      devLog('✅ Logout exitoso');
    } catch (error) {
      devError('Error during logout', error);
      // Aún así limpiamos el estado local
      setCurrentUser(null);
    }
  }, []);

  // Cargar usuario al inicializar
  useEffect(() => {
    devLog('🚀 DataContext inicializado, cargando usuario...');
    // Agregar un pequeño delay para asegurar que el componente esté montado
    const timer = setTimeout(() => {
      loadCurrentUser();
    }, 100);
    
    return () => clearTimeout(timer);
  }, [loadCurrentUser]);

  // Cargar datos esenciales cuando el usuario se autentica
  useEffect(() => {
    if (currentUser) {
      // OPTIMIZACIÓN: Cargar solo datos esenciales al inicio, el resto se carga bajo demanda
      // Datos esenciales: turnos, recursos, especialidades, centros físicos, tipos de atención
      // Datos bajo demanda (NO se cargan automáticamente):
      // - pacientes (búsqueda remota en AsyncAutocomplete)
      // - consultas (carga local en Consultas.tsx y MisConsultas.tsx)
      // - médicos (se cargan cuando se necesitan)
      // - solicitudes (se cargan cuando se necesitan)
      // - archivos médicos (se cargan cuando se necesitan)
      // - tipos examen (se cargan cuando se necesitan)
      const timer = setTimeout(() => {
        // Cargar datos esenciales en paralelo
        Promise.all([
          loadTurnos(),
          loadRecursos(),
          loadEspecialidades(),
          loadCentrosFisicos(),
          loadTiposAtencion(),
        ]).catch(error => {
          devError('Error cargando datos esenciales', error);
        });
      }, 100);
      
      return () => {
        clearTimeout(timer);
      };
    }
  }, [currentUser, loadTurnos, loadRecursos, loadEspecialidades, loadCentrosFisicos, loadTiposAtencion]);

  // Precargar pacientes para roles con lectura global (admin, secretaría, enfermería)
  useEffect(() => {
    if (!currentUser) return;
    const rolesConListadoGlobal = ['ADMIN', 'SECRETARIA', 'ENFERMERIA'];
    if (
      rolesConListadoGlobal.includes(currentUser.rol) &&
      pacientes.length === 0 &&
      !loading.pacientes &&
      !pacientesLoadError
    ) {
      void loadPacientes();
    }
  }, [currentUser, pacientes.length, loading.pacientes, pacientesLoadError, loadPacientes]);

  // ELIMINADO: useEffect problemático que causaba bucle infinito
  // useEffect(() => {
  //   if (currentUser) {
  //     devLog('👤 Usuario autenticado, cargando datos...');
  //     // Agregar un pequeño delay para asegurar que las cookies estén establecidas
  //     const timer = setTimeout(() => {
  //       refreshAll();
  //     }, 1000);
  //     
  //     return () => clearTimeout(timer);
  //   } else {
  //     devLog('⚠️ Usuario no autenticado, no cargando datos');
  //   }
  // }, [currentUser]);

  // Computed values
  const isAuthenticated = currentUser !== null;
  const isLoading = loading.user;

  const value = {
    turnos,
    pacientes,
    pacientesLoadError,
    medicos,
    especialidades,
    centrosFisicos,
    tiposAtencion,
    recursos,
    archivosMedicos,
    consultas,
    solicitudes,
    tiposExamen,
    currentUser,
    isAuthenticated,
    isLoading,
    loading,
    lastUpdate,
    refreshAll,
    refreshTurnos,
    loadTurnos,
    loadPacientes,
    loadMedicos,
    loadEspecialidades,
    loadCentrosFisicos,
    loadTiposAtencion,
    loadRecursos,
    loadArchivosMedicos,
    loadConsultas,
    loadSolicitudes,
    loadTiposExamen,
    loadCurrentUser,
    login,
    logout,
    setTurnos,
    setPacientes,
    setArchivosMedicos,
    setConsultas,
    setSolicitudes,
    setCurrentUser
  };

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  );
}; 