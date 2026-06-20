/**
 * Función auxiliar segura para substring
 * No modifica String.prototype para evitar conflictos
 */
export const safeSubstring = (value: any, start?: number, end?: number): string => {
  if (value == null) {
    return '';
  }
  
  // Convertir a string si no lo es
  const str = typeof value === 'string' ? value : String(value);
  
  // Usar substring de forma segura
  try {
    // Manejar casos donde start o end pueden ser undefined
    if (start !== undefined && end !== undefined) {
      return str.substring(start, end);
    } else if (start !== undefined) {
      return str.substring(start);
    } else {
      return str;
    }
  } catch (error) {
    console.warn('Error al usar substring:', error, { value, start, end });
    return '';
  }
};

/**
 * Interceptor global de errores para capturar errores de substring
 * y otros errores relacionados con tipos
 */
export const setupGlobalErrorHandler = () => {
  // Función helper para detectar errores de ResizeObserver
  const isResizeObserverError = (message: string | Error | Event | unknown): boolean => {
    const msg = typeof message === 'string' 
      ? message 
      : message instanceof Error 
        ? message.message 
        : message instanceof Event && 'message' in message
          ? String(message.message)
          : String(message);
    
    return msg.includes('ResizeObserver loop completed with undelivered notifications') ||
           msg.includes('ResizeObserver loop limit exceeded') ||
           msg.includes('ResizeObserver loop');
  };

  // Interceptar usando window.onerror (se ejecuta ANTES que addEventListener)
  // Esto es crítico para capturar errores antes de que React Development Tools los muestre
  const originalOnError = window.onerror;
  window.onerror = (message, source, lineno, colno, error) => {
    const errorMessage = typeof message === 'string' ? message : message?.toString() || '';
    
    // Silenciar error de ResizeObserver (error conocido y benigno, común con Material-UI)
    if (isResizeObserverError(errorMessage)) {
      return true; // Retornar true previene que el error se propague
    }
    
    // Capturar errores de substring
    if (errorMessage.includes('substring is not a function')) {
      console.warn('⚠️ Error de substring capturado y manejado:', errorMessage);
      return true;
    }
    
    // Llamar al handler original si existe
    if (originalOnError) {
      return originalOnError(message, source, lineno, colno, error);
    }
    
    return false;
  };

  // Interceptor para errores no capturados (fallback)
  window.addEventListener('error', (event) => {
    // Capturar errores de substring
    if (event.message && event.message.includes('substring is not a function')) {
      console.warn('⚠️ Error de substring capturado y manejado:', event.message);
      event.preventDefault(); // Prevenir que el error se propague
      return true;
    }
    
    // Silenciar error de ResizeObserver (error conocido y benigno, común con Material-UI)
    if (event.message && (event.message.includes('ResizeObserver loop completed with undelivered notifications') ||
        event.message.includes('ResizeObserver loop limit exceeded'))) {
      event.preventDefault(); // Prevenir que el error se propague
      event.stopImmediatePropagation(); // Detener la propagación inmediatamente
      return true;
    }
    
    return false;
  }, true); // Usar capture phase para interceptar antes

  // Interceptor para promesas rechazadas
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason;
    const errorMessage = error?.message || error?.toString() || '';
    
    if (errorMessage.includes('substring is not a function')) {
      console.warn('⚠️ Error de substring en promesa capturado y manejado:', errorMessage);
      event.preventDefault(); // Prevenir que el error se propague
      return true;
    }
    
    // Silenciar error de ResizeObserver en promesas rechazadas
    if (isResizeObserverError(errorMessage)) {
      event.preventDefault(); // Prevenir que el error se propague
      event.stopPropagation(); // Detener propagación
      return true;
    }
    
    return false;
  }, true); // También usar capture phase

  // Interceptar errores en console.error (React Development Tools usa esto)
  const originalConsoleError = console.error;
  console.error = (...args: any[]) => {
    const errorMessage = args.join(' ');
    
    // Silenciar error de ResizeObserver en console
    if (isResizeObserverError(errorMessage)) {
      return; // No mostrar este error en la consola
    }
    
    // Llamar al console.error original para otros errores
    originalConsoleError.apply(console, args);
  };

  // También interceptar console.warn por si acaso
  const originalConsoleWarn = console.warn;
  console.warn = (...args: any[]) => {
    const errorMessage = args.join(' ');
    
    // Silenciar error de ResizeObserver en console.warn
    if (isResizeObserverError(errorMessage)) {
      return;
    }
    
    originalConsoleWarn.apply(console, args);
  };
};

/**
 * Función auxiliar para obtener texto seleccionado de forma segura
 * Maneja casos donde getSelection() puede fallar o retornar valores inesperados
 */
export const safeGetSelectedText = (element?: HTMLElement): string => {
  try {
    const selection = window.getSelection();
    if (selection && selection.toString()) {
      return selection.toString();
    }

    // Si hay un elemento y tiene selección
    if (element) {
      const inputElement = element as HTMLInputElement | HTMLTextAreaElement;
      if (inputElement && typeof inputElement.selectionStart === 'number' && typeof inputElement.selectionEnd === 'number') {
        const start = inputElement.selectionStart;
        const end = inputElement.selectionEnd;
        
        // Obtener el valor de forma segura
        let value: string | null | undefined = null;
        
        if ('value' in inputElement && typeof (inputElement as HTMLInputElement | HTMLTextAreaElement).value === 'string') {
          value = (inputElement as HTMLInputElement | HTMLTextAreaElement).value;
        } else if (element.textContent) {
          value = element.textContent;
        } else if ('innerText' in element && typeof (element as HTMLElement).innerText === 'string') {
          value = (element as HTMLElement).innerText;
        }
        
        // Verificar que value sea una cadena antes de usar substring
        if (value != null && typeof value === 'string' && start !== null && end !== null) {
          return value.substring(start, end);
        }
      }
    }
  } catch (error) {
    console.warn('Error al obtener texto seleccionado:', error);
  }
  
  return '';
};

