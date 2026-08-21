/**
 * Cliente API oficial para la integración Frontend (Next.js) <-> Backend (FastAPI).
 * Base URL: http://localhost:8000/api
 *
 * Sin fallback a datos de mentira: si el backend no responde, el error se
 * propaga y cada pantalla decide cómo mostrarlo (loading/error state real).
 */

import {
  ApiBandejaNotificaciones, ApiCampoIdentidad, ApiDisputa, ApiEdicion, ApiEquipoResumen, ApiFase, ApiInscripcion,
  ApiInscripcionCreada, ApiJuego, ApiMensajePartida, ApiMiInscripcion, ApiMiPartida, ApiNotificacion, ApiPartida, ApiReporteResultado,
  ApiResumenEdicion, ApiTablaGrupo, ApiTokenOut, ApiTorneo, ApiUsuario, ApiUsuarioAdmin,
} from '@/lib/api-types';
import {
  Disputa, Edicion, Equipo, Fase, Inscripcion, Jugador, Juego, Partida,
  ParticipacionPartida, Torneo, Usuario,
} from '@/types';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function extraerMensajeError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: any) => d.msg || JSON.stringify(d)).join(' · ');
    }
  } catch {
    // el cuerpo no era JSON
  }
  return `Error ${res.status}: ${res.statusText}`;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      ...options.headers,
    };

    const res = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });

    if (!res.ok) {
      throw new ApiError(res.status, await extraerMensajeError(res));
    }
    if (res.status === 204) return undefined as T;
    return await res.json();
  }

  // ──────────────────────────────────────────
  // JUEGOS
  // ──────────────────────────────────────────
  async getJuegos(): Promise<Juego[]> {
    const juegos = await this.request<ApiJuego[]>('/juegos');
    return juegos.map(mapJuego);
  }

  // ──────────────────────────────────────────
  // TORNEOS & EDICIONES
  // ──────────────────────────────────────────
  async getTorneos(): Promise<Torneo[]> {
    const torneos = await this.request<ApiTorneo[]>('/torneos');
    return torneos.map(mapTorneo);
  }

  async getTorneoById(id: string): Promise<ApiTorneo> {
    const torneos = await this.request<ApiTorneo[]>('/torneos');
    const torneo = torneos.find(t => String(t.id) === id);
    if (!torneo) throw new ApiError(404, 'El torneo no existe.');
    return torneo;
  }

  async deleteTorneo(torneoId: string): Promise<void> {
    return this.request<void>(`/torneos/${torneoId}`, { method: 'DELETE' });
  }

  /** Lista de ediciones con su torneo ya resuelto, lista para la UI (home, explorador). */
  async getEdicionesCompletas(): Promise<Edicion[]> {
    const [ediciones, torneos] = await Promise.all([
      this.request<ApiEdicion[]>('/ediciones'),
      this.request<ApiTorneo[]>('/torneos'),
    ]);
    const torneoPorId = new Map(torneos.map(t => [t.id, t]));
    return ediciones
      .map(edicion => {
        const torneo = torneoPorId.get(edicion.torneo_id);
        if (!torneo) return null;
        return mapEdicionBasica(edicion, torneo);
      })
      .filter((e): e is Edicion => e !== null);
  }

  async getEdicionBySlug(slug: string): Promise<ApiResumenEdicion | null> {
    const ediciones = await this.request<ApiEdicion[]>(`/ediciones?slug=${encodeURIComponent(slug)}`);
    if (ediciones.length === 0) return null;
    return this.getResumenEdicion(String(ediciones[0].id));
  }

  async getResumenEdicion(edicionId: string): Promise<ApiResumenEdicion> {
    return this.request<ApiResumenEdicion>(`/ediciones/${edicionId}/resumen`);
  }

  async getEdiciones(): Promise<ApiEdicion[]> {
    return this.request<ApiEdicion[]>('/ediciones');
  }

  async getEdicionById(edicionId: string): Promise<ApiEdicion> {
    return this.request<ApiEdicion>(`/ediciones/${edicionId}`);
  }

  async getEdicionesByTorneo(torneoId: string): Promise<ApiEdicion[]> {
    return this.request<ApiEdicion[]>(`/ediciones?torneo_id=${torneoId}`);
  }

  // ──────────────────────────────────────────
  // ADMIN: TORNEOS & EDICIONES
  // ──────────────────────────────────────────
  async createTorneo(data: { nombre: string; descripcion?: string; logo_url?: string }): Promise<ApiTorneo> {
    return this.request<ApiTorneo>('/torneos', { method: 'POST', body: JSON.stringify(data) });
  }

  async createEdicion(data: {
    torneo_id: number; juego_id: number; numero: number; nombre: string;
    max_equipos?: number; zona_horaria?: string; fecha_inicio?: string; bolsa_premios?: string;
  }): Promise<ApiEdicion> {
    return this.request<ApiEdicion>('/ediciones', { method: 'POST', body: JSON.stringify(data) });
  }

  async cambiarEstadoEdicion(edicionId: string, estado: string): Promise<ApiEdicion> {
    return this.request<ApiEdicion>(`/ediciones/${edicionId}/estado?estado=${estado}`, { method: 'POST' });
  }

  /** Ajustes de una edición ya creada. Solo se mandan los campos a cambiar:
   *  el backend usa exclude_unset, así que omitir uno lo deja como estaba. */
  async updateEdicion(edicionId: string, data: {
    max_equipos?: number | null; fecha_inicio?: string | null; bolsa_premios?: string | null;
    reglamento_url?: string | null; discord_webhook_url?: string | null; requiere_aprobacion?: boolean;
  }): Promise<ApiEdicion> {
    return this.request<ApiEdicion>(`/ediciones/${edicionId}`, { method: 'PATCH', body: JSON.stringify(data) });
  }

  async probarWebhook(edicionId: string): Promise<{ mensaje: string }> {
    return this.request<{ mensaje: string }>(`/ediciones/${edicionId}/probar-webhook`, { method: 'POST' });
  }

  // ──────────────────────────────────────────
  // NOTIFICACIONES
  // ──────────────────────────────────────────
  async getNotificaciones(): Promise<ApiBandejaNotificaciones> {
    return this.request<ApiBandejaNotificaciones>('/notificaciones');
  }

  async marcarNotificacionLeida(id: number): Promise<ApiNotificacion> {
    return this.request<ApiNotificacion>(`/notificaciones/${id}/leer`, { method: 'POST' });
  }

  async marcarTodasLeidas(): Promise<ApiBandejaNotificaciones> {
    return this.request<ApiBandejaNotificaciones>('/notificaciones/leer-todas', { method: 'POST' });
  }

  // ──────────────────────────────────────────
  // FASES & PARTIDAS
  // ──────────────────────────────────────────
  async getFasesByEdicion(edicionId: string): Promise<ApiFase[]> {
    return this.request<ApiFase[]>(`/ediciones/${edicionId}/fases`);
  }

  async createFase(edicionId: string, data: {
    orden: number; nombre: string; modelo_competencia: string; formato: string; config?: Record<string, any>;
  }): Promise<ApiFase> {
    return this.request<ApiFase>(`/ediciones/${edicionId}/fases`, { method: 'POST', body: JSON.stringify(data) });
  }

  async sortearFase(edicionId: string, faseId: string): Promise<ApiPartida[]> {
    return this.request<ApiPartida[]>(`/ediciones/${edicionId}/fases/${faseId}/sortear`, { method: 'POST' });
  }

  async sortearFaseDesdeAnterior(edicionId: string, faseId: string, data: {
    fase_origen_id: number; cupos_por_grupo?: number; ronda_origen?: number;
  }): Promise<ApiPartida[]> {
    return this.request<ApiPartida[]>(`/ediciones/${edicionId}/fases/${faseId}/sortear-desde-fase-anterior`, {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async siguienteRondaSuiza(edicionId: string, faseId: string): Promise<ApiPartida[]> {
    return this.request<ApiPartida[]>(`/ediciones/${edicionId}/fases/${faseId}/siguiente-ronda-suiza`, { method: 'POST' });
  }

  async cerrarFase(edicionId: string, faseId: string): Promise<ApiFase> {
    return this.request<ApiFase>(`/ediciones/${edicionId}/fases/${faseId}/cerrar`, { method: 'POST' });
  }

  async resetearSorteo(edicionId: string, faseId: string): Promise<ApiFase> {
    return this.request<ApiFase>(`/ediciones/${edicionId}/fases/${faseId}/resetear-sorteo`, { method: 'POST' });
  }

  async eliminarFase(edicionId: string, faseId: string): Promise<void> {
    return this.request<void>(`/ediciones/${edicionId}/fases/${faseId}`, { method: 'DELETE' });
  }

  async getPartidasByFase(faseId: string): Promise<ApiPartida[]> {
    return this.request<ApiPartida[]>(`/fases/${faseId}/partidas`);
  }

  async getPartida(faseId: string, partidaId: string): Promise<ApiPartida> {
    return this.request<ApiPartida>(`/fases/${faseId}/partidas/${partidaId}`);
  }

  async abrirCheckinPartida(faseId: string, partidaId: string, minutos = 15): Promise<ApiPartida> {
    return this.request<ApiPartida>(`/fases/${faseId}/partidas/${partidaId}/abrir-checkin`, {
      method: 'POST', body: JSON.stringify({ minutos }),
    });
  }

  async resolverCheckinPartida(faseId: string, partidaId: string): Promise<ApiPartida> {
    return this.request<ApiPartida>(`/fases/${faseId}/partidas/${partidaId}/resolver-checkin`, { method: 'POST' });
  }

  async resolverReporteVencido(faseId: string, partidaId: string): Promise<ApiPartida> {
    return this.request<ApiPartida>(`/fases/${faseId}/partidas/${partidaId}/resolver-reporte-vencido`, { method: 'POST' });
  }

  async programarPartida(faseId: string, partidaId: string, programadaPara: string): Promise<ApiPartida> {
    return this.request<ApiPartida>(`/fases/${faseId}/partidas/${partidaId}/programar`, {
      method: 'PATCH', body: JSON.stringify({ programada_para: programadaPara }),
    });
  }

  async getMensajesPartida(faseId: string, partidaId: string): Promise<ApiMensajePartida[]> {
    return this.request<ApiMensajePartida[]>(`/fases/${faseId}/partidas/${partidaId}/mensajes`);
  }

  /**
   * Canjea la sesión por un ticket corto para abrir un stream privado.
   *
   * El navegador no deja mandar el header Authorization en un EventSource, y
   * poner el JWT en la query string lo dejaría escrito en los logs de acceso
   * del servidor y del proxy. El ticket sirve una sola vez y vive un minuto.
   */
  async pedirTicketDeStream(): Promise<{ ticket: string; vence_en_segundos: number }> {
    return this.request<{ ticket: string; vence_en_segundos: number }>('/stream/ticket', {
      method: 'POST',
    });
  }

  async enviarMensajePartida(faseId: string, partidaId: string, data: {
    equipo_id?: number; texto: string;
  }): Promise<ApiMensajePartida> {
    return this.request<ApiMensajePartida>(`/fases/${faseId}/partidas/${partidaId}/mensajes`, {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async confirmarResultadoAdmin(faseId: string, partidaId: string, equipoId: string): Promise<ApiPartida> {
    return this.request<ApiPartida>(`/fases/${faseId}/partidas/${partidaId}/confirmar`, {
      method: 'POST', body: JSON.stringify({ equipo_id: Number(equipoId) }),
    });
  }

  async corregirResultado(faseId: string, partidaId: string, data: {
    resultados: { equipo_id: number; mapas_ganados: number }[]; motivo: string;
  }): Promise<{ partida: ApiPartida }> {
    return this.request(`/fases/${faseId}/partidas/${partidaId}/corregir-resultado`, {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async getTablaFase(edicionId: string, faseId: string): Promise<ApiTablaGrupo[]> {
    return this.request<ApiTablaGrupo[]>(`/ediciones/${edicionId}/fases/${faseId}/tabla`);
  }

  // ──────────────────────────────────────────
  // INSCRIPCIONES
  // ──────────────────────────────────────────
  async getInscripcionesAprobadas(edicionId: string): Promise<ApiInscripcion[]> {
    return this.request<ApiInscripcion[]>(`/ediciones/${edicionId}/inscripciones?estado=aprobada`);
  }

  async getInscripciones(edicionId: string, estado?: string): Promise<ApiInscripcion[]> {
    const qs = estado ? `?estado=${estado}` : '';
    return this.request<ApiInscripcion[]>(`/ediciones/${edicionId}/inscripciones${qs}`);
  }

  async revisarInscripcion(edicionId: string, inscripcionId: string, estado: 'aprobada' | 'rechazada', motivoRechazo?: string): Promise<ApiInscripcion> {
    return this.request<ApiInscripcion>(`/ediciones/${edicionId}/inscripciones/${inscripcionId}/revisar`, {
      method: 'POST', body: JSON.stringify({ estado, motivo_rechazo: motivoRechazo }),
    });
  }

  async sembrarAutomatico(edicionId: string, semilla?: number): Promise<{ nombre: string; seed: number }[]> {
    const qs = semilla !== undefined ? `?semilla=${semilla}` : '';
    return this.request(`/ediciones/${edicionId}/inscripciones/sembrar-automatico${qs}`, { method: 'POST' });
  }

  async editarSeedInscripcion(edicionId: string, inscripcionId: string, seed: number): Promise<ApiInscripcion> {
    return this.request<ApiInscripcion>(`/ediciones/${edicionId}/inscripciones/${inscripcionId}/seed`, {
      method: 'PATCH', body: JSON.stringify({ seed }),
    });
  }

  async createInscripcion(edicionId: string, data: {
    nombre_equipo: string;
    tag?: string;
    contacto_nombre?: string;
    contacto_whatsapp?: string;
    contacto_discord?: string;
    capitan_declarado?: string;
    jugadores: { identidad: Record<string, string>; es_suplente?: boolean; es_capitan?: boolean; discord_id?: string }[];
  }): Promise<ApiInscripcionCreada> {
    return this.request<ApiInscripcionCreada>(`/ediciones/${edicionId}/inscripciones`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ──────────────────────────────────────────
  // CHECK-IN / REPORTE DE RESULTADO
  // ──────────────────────────────────────────
  async checkInPartida(faseId: string, partidaId: string, equipoId: string): Promise<ApiPartida> {
    return this.request<ApiPartida>(`/fases/${faseId}/partidas/${partidaId}/checkin`, {
      method: 'POST',
      body: JSON.stringify({ equipo_id: Number(equipoId) }),
    });
  }

  async reportarResultado(faseId: string, partidaId: string, data: {
    equipo_id: number; marcador_propio: number; marcador_rival: number; evidencia_url?: string;
  }): Promise<ApiReporteResultado> {
    return this.request<ApiReporteResultado>(`/fases/${faseId}/partidas/${partidaId}/reportar`, {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async impugnarResultado(faseId: string, partidaId: string, data: {
    equipo_id: number; motivo: string;
  }): Promise<ApiDisputa> {
    return this.request<ApiDisputa>(`/fases/${faseId}/partidas/${partidaId}/impugnar`, {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async getMisInscripciones(): Promise<ApiMiInscripcion[]> {
    return this.request<ApiMiInscripcion[]>('/usuarios/me/inscripciones');
  }

  async getMisPartidas(): Promise<ApiMiPartida[]> {
    return this.request<ApiMiPartida[]>('/usuarios/me/partidas');
  }

  // ──────────────────────────────────────────
  // DISPUTAS (admin)
  // ──────────────────────────────────────────
  async getDisputasGlobal(estado?: string): Promise<ApiDisputa[]> {
    const qs = estado ? `?estado=${estado}` : '';
    return this.request<ApiDisputa[]>(`/disputas${qs}`);
  }

  async resolverDisputa(disputaId: string, data: {
    resolucion: string; accion: 'reprogramar' | 'walkover' | 'confirmar_resultado';
    equipo_ganador_id?: number; resultados?: { equipo_id: number; mapas_ganados: number }[];
  }): Promise<ApiDisputa> {
    return this.request<ApiDisputa>(`/disputas/${disputaId}/resolver`, {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  // ──────────────────────────────────────────
  // USUARIOS (admin)
  // ──────────────────────────────────────────
  async getUsuariosAdmin(): Promise<ApiUsuarioAdmin[]> {
    return this.request<ApiUsuarioAdmin[]>('/usuarios');
  }

  async cambiarRolUsuario(usuarioId: string, esOrganizador: boolean, puedeGestionar?: boolean): Promise<ApiUsuarioAdmin> {
    return this.request<ApiUsuarioAdmin>(`/usuarios/${usuarioId}/rol`, {
      method: 'PATCH',
      body: JSON.stringify({ es_organizador: esOrganizador, puede_gestionar_organizadores: puedeGestionar }),
    });
  }

  // ──────────────────────────────────────────
  // AUTH
  // ──────────────────────────────────────────
  getDiscordLoginUrl(): string {
    return `${API_BASE_URL}/auth/discord/login`;
  }

  async registrarConEmail(email: string, password: string, nombre: string): Promise<ApiTokenOut> {
    return this.request<ApiTokenOut>('/auth/local/registro', {
      method: 'POST',
      body: JSON.stringify({ email, password, nombre }),
    });
  }

  async loginConEmail(email: string, password: string): Promise<ApiTokenOut> {
    return this.request<ApiTokenOut>('/auth/local/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async getMe(): Promise<Usuario> {
    const u = await this.request<ApiUsuario>('/auth/discord/yo');
    return mapUsuario(u);
  }
}

export const api = new ApiClient();

// ──────────────────────────────────────────
// MAPEOS: respuesta del backend (snake_case) → forma que usa la UI
// ──────────────────────────────────────────

export function mapJuego(j: ApiJuego): Juego {
  return {
    id: String(j.id),
    codigo: j.codigo,
    nombre: j.nombre,
    titularesRequeridos: j.titulares_requeridos,
    suplentesMaximos: j.suplentes_maximos,
    modeloCompetenciaDefault: j.modelo_competencia_default,
    camposIdentidad: j.campos_identidad.campos.map((c: ApiCampoIdentidad) => ({
      key: c.nombre,
      label: c.etiqueta,
      placeholder: c.etiqueta,
      required: c.requerido,
    })),
    bannerUrl: '',
    logoUrl: '',
  };
}

export function mapTorneo(t: ApiTorneo): Torneo {
  return {
    id: String(t.id),
    nombre: t.nombre,
    slug: t.slug,
  };
}

function mapEdicionBasica(e: ApiEdicion, torneo: ApiTorneo): Edicion {
  const juego = mapJuego(e.juego);
  return {
    id: String(e.id),
    slug: e.slug,
    torneoId: String(e.torneo_id),
    torneoNombre: torneo.nombre,
    juegoId: juego.id,
    juego,
    numero: e.numero,
    nombre: e.nombre,
    estado: e.estado,
    bolsaPremios: e.bolsa_premios || '',
    moneda: 'USD',
    equiposInscritosCount: e.equipos_aprobados,
    maxEquipos: e.max_equipos ?? 0,
    fechaInicio: e.fecha_inicio || '',
    fechaRosterLock: e.roster_lock || '',
    reglamentoUrl: e.reglamento_url || undefined,
    descripcion: '',
  };
}

export function mapResumenAEdicion(r: ApiResumenEdicion, torneo?: ApiTorneo): Edicion {
  const e = r.edicion;
  const juego = mapJuego(e.juego);
  return {
    id: String(e.id),
    slug: e.slug,
    torneoId: String(e.torneo_id),
    torneoNombre: torneo?.nombre || e.nombre,
    juegoId: juego.id,
    juego,
    numero: e.numero,
    nombre: e.nombre,
    estado: e.estado,
    bolsaPremios: e.bolsa_premios || '',
    moneda: 'USD',
    equiposInscritosCount: r.equipos_aprobados,
    maxEquipos: e.max_equipos ?? 0,
    fechaInicio: e.fecha_inicio || '',
    fechaRosterLock: e.roster_lock || '',
    reglamentoUrl: e.reglamento_url || undefined,
    descripcion: '',
  };
}

export function mapEquipo(e: ApiEquipoResumen | { id: number; nombre: string; tag: string | null; logo_url?: string | null }): Equipo {
  return {
    id: String(e.id),
    nombre: e.nombre,
    tag: e.tag || '',
    logoUrl: (e as any).logo_url || undefined,
    estaActivo: true,
  };
}

export function mapPartida(p: ApiPartida, nombreFase = ''): Partida {
  const bracketMap: Record<string, 'upper' | 'lower' | 'grand_final'> = {
    alta: 'upper',
    baja: 'lower',
    gran_final: 'grand_final',
    unica: 'upper',
  };
  return {
    id: String(p.id),
    faseId: String(p.fase_id),
    nombreGrupo: nombreFase,
    numeroRonda: p.ronda || 1,
    numeroCaida: p.numero_caida || undefined,
    estado: p.estado,
    programadaPara: p.programada_para || undefined,
    participaciones: p.participaciones.map((part): ParticipacionPartida => ({
      id: String(part.id),
      partidaId: String(p.id),
      equipoId: String(part.equipo.id),
      equipo: mapEquipo(part.equipo),
      mapasGanados: part.mapas_ganados ?? undefined,
      esGanador: part.es_ganador ?? undefined,
      posicion: part.posicion ?? undefined,
      bajas: part.bajas ?? undefined,
      puntos: part.puntos ?? undefined,
    })),
    bracket: bracketMap[p.lado],
    isBye: p.estado === 'bye',
  } as Partida;
}

export function mapFase(f: ApiFase, partidas: Partida[] = []): Fase {
  return {
    id: String(f.id),
    edicionId: String(f.edicion_id),
    orden: f.orden,
    nombre: f.nombre,
    modeloCompetencia: f.modelo_competencia,
    formato: f.formato,
    estado: f.estado as Fase['estado'],
    partidas,
    cuposAvance: f.config?.cupos_avance || 1,
    numGrupos: f.config?.grupos,
  };
}

export function mapInscripcion(i: ApiInscripcion): Inscripcion {
  return {
    id: String(i.id),
    edicionId: String(i.edicion_id),
    equipo: mapEquipo(i.equipo),
    estado: i.estado,
    estadoPago: 'no_requerido',
    createdAt: i.created_at,
    roster: i.jugadores.map((j): Jugador => ({
      id: String(j.id),
      equipoId: String(i.equipo.id),
      nombre: j.identidad.nick || j.identidad.nombre || `Jugador #${j.orden}`,
      identidad: j.identidad,
      esSuplente: j.es_suplente,
      esCapitan: j.es_capitan,
      discordId: j.discord_id || undefined,
    })),
  };
}

export function mapUsuario(u: ApiUsuario): Usuario {
  return {
    id: String(u.id),
    nombre: u.discord_username,
    email: '',
    avatarUrl: u.discord_avatar_url || '',
    discordId: u.discord_id,
    rol: u.es_organizador ? 'organizador' : 'jugador',
  };
}
