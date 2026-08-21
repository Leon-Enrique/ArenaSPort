/**
 * Cliente de los streams SSE del backend: bracket en vivo y chat en vivo.
 *
 * Por qué SSE y no WebSocket: todo lo que hace falta acá es servidor ->
 * cliente. Las acciones (reportar, confirmar, mandar un mensaje) siguen
 * yendo por POST como siempre. A cambio, el navegador reconecta solo cuando
 * se corta la conexión, que es la mitad del trabajo de un WebSocket hecha
 * gratis.
 *
 * El stream de edición es público. El de chat no: el navegador no deja
 * ponerle headers a un EventSource, así que se pide un ticket de un solo uso
 * con el token normal y se entra con eso (ver app/core/tickets.py en el
 * backend). El JWT nunca viaja en la URL.
 */

import { API_BASE_URL, api } from '@/lib/api';

export interface EventoPartida {
  partida_id: number;
  fase_id: number;
  estado: string;
}

export interface EventoMensaje {
  id: number;
  partida_id: number;
  equipo_id: number | null;
  autor_nombre: string;
  texto: string;
  created_at: string;
}

/** Tipos de evento que manda el stream de una edición. */
const EVENTOS_DE_PARTIDA = [
  'partida_actualizada',
  'partida_programada',
  'checkin_abierto',
  'checkin_confirmado',
  'checkin_resuelto',
  'resultado_reportado',
  'resultado_confirmado',
  'resultado_impugnado',
  'resultado_corregido',
  'problema_reportado',
  'disputa_resuelta',
] as const;

/**
 * Escucha los cambios de partidas de una edición.
 * Devuelve la función para cortar la suscripción.
 */
export function escucharEdicion(
  edicionId: number | string,
  alCambiar: (evento: EventoPartida, tipo: string) => void,
  alCambiarConexion?: (conectado: boolean) => void,
): () => void {
  const fuente = new EventSource(`${API_BASE_URL}/stream/ediciones/${edicionId}`);

  const manejar = (tipo: string) => (e: MessageEvent) => {
    try {
      alCambiar(JSON.parse(e.data) as EventoPartida, tipo);
    } catch {
      // Un evento con formato raro no puede tumbar el stream entero.
    }
  };

  for (const tipo of EVENTOS_DE_PARTIDA) {
    fuente.addEventListener(tipo, manejar(tipo));
  }

  // Este stream es público y no usa ticket, así que la reconexión automática
  // del navegador sirve tal cual: solo hay que reflejar el estado.
  fuente.addEventListener('open', () => alCambiarConexion?.(true));
  fuente.onerror = () => alCambiarConexion?.(false);

  return () => {
    alCambiarConexion?.(false);
    fuente.close();
  };
}

const RECONEXION_MS = 2000;
const MAX_INTENTOS = 5;

/**
 * Escucha el chat de una partida. Necesita sesión iniciada.
 *
 * La reconexión se maneja a mano, y no es un capricho: el ticket es de un
 * solo uso, así que la reconexión automática del navegador reintentaría
 * eternamente con un ticket ya quemado y se comería un 401 cada vez. Ante
 * cualquier corte hay que cerrar, pedir un ticket nuevo y volver a abrir.
 *
 * Devuelve la función para cortar. Es segura de llamar en cualquier momento,
 * incluso antes de que haya llegado el primer ticket — el caso real de un
 * modal que se abre y se cierra enseguida.
 */
export function escucharChat(
  partidaId: number | string,
  alLlegarMensaje: (mensaje: EventoMensaje) => void,
): () => void {
  let cancelado = false;
  let fuente: EventSource | null = null;
  let intentos = 0;
  let temporizador: ReturnType<typeof setTimeout> | null = null;

  const conectar = async () => {
    if (cancelado) return;
    try {
      const { ticket } = await api.pedirTicketDeStream();
      if (cancelado) return;

      fuente = new EventSource(
        `${API_BASE_URL}/stream/partidas/${partidaId}/chat?ticket=${encodeURIComponent(ticket)}`,
      );

      fuente.addEventListener('open', () => {
        intentos = 0; // conectó: el presupuesto de reintentos se renueva
      });

      fuente.addEventListener('mensaje_nuevo', (e: MessageEvent) => {
        try {
          alLlegarMensaje(JSON.parse(e.data) as EventoMensaje);
        } catch {
          // Un mensaje malformado no puede cortar el chat entero.
        }
      });

      fuente.onerror = () => {
        fuente?.close();
        fuente = null;
        if (cancelado || intentos >= MAX_INTENTOS) return;
        intentos += 1;
        temporizador = setTimeout(conectar, RECONEXION_MS * intentos);
      };
    } catch {
      // Sin ticket no hay chat en vivo. No es fatal: el modal carga el
      // historial por HTTP al abrirse, así que se ve todo lo anterior — lo
      // que se pierde es que aparezcan solos los mensajes nuevos.
      if (cancelado || intentos >= MAX_INTENTOS) return;
      intentos += 1;
      temporizador = setTimeout(conectar, RECONEXION_MS * intentos);
    }
  };

  void conectar();

  return () => {
    cancelado = true;
    if (temporizador) clearTimeout(temporizador);
    fuente?.close();
  };
}
