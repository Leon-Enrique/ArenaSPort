/**
 * Tipos que reflejan tal cual las respuestas del backend (snake_case).
 * `src/lib/api.ts` los mapea a los tipos de UI en `src/types/index.ts`.
 */

export interface ApiCampoIdentidad {
  nombre: string;
  etiqueta: string;
  requerido: boolean;
}

export interface ApiJuego {
  id: number;
  codigo: string;
  nombre: string;
  modelo_competencia_default: 'enfrentamiento_directo' | 'multi_equipo';
  titulares_requeridos: number;
  suplentes_maximos: number;
  campos_identidad: {
    campos: ApiCampoIdentidad[];
    clave_unica: string[];
  };
}

export interface ApiTorneo {
  id: number;
  nombre: string;
  slug: string;
  descripcion: string | null;
  logo_url: string | null;
}

export interface ApiEdicion {
  id: number;
  torneo_id: number;
  juego: ApiJuego;
  numero: number;
  nombre: string;
  slug: string;
  estado: 'borrador' | 'inscripciones_abiertas' | 'inscripciones_cerradas' | 'en_curso' | 'finalizada' | 'cancelada';
  zona_horaria: string;
  max_equipos: number | null;
  inscripcion_abre: string | null;
  inscripcion_cierra: string | null;
  roster_lock: string | null;
  fecha_inicio: string | null;
  bolsa_premios: string | null;
  reglamento_url: string | null;
  equipos_aprobados: number;
}

export interface ApiFase {
  id: number;
  edicion_id: number;
  orden: number;
  nombre: string;
  modelo_competencia: 'enfrentamiento_directo' | 'multi_equipo';
  formato: 'eliminacion_simple' | 'eliminacion_doble' | 'round_robin' | 'suizo' | 'liga_acumulativa';
  estado: string;
  config: Record<string, any>;
}

export interface ApiEquipoResumen {
  id: number;
  nombre: string;
  tag: string | null;
}

export interface ApiParticipacion {
  id: number;
  equipo: ApiEquipoResumen;
  slot: number | null;
  mapas_ganados: number | null;
  es_ganador: boolean | null;
  posicion: number | null;
  bajas: number | null;
  puntos: number | null;
  checkin_at: string | null;
}

export interface ApiPartida {
  id: number;
  fase_id: number;
  lado: 'unica' | 'alta' | 'baja' | 'gran_final';
  ronda: number | null;
  numero_caida: number | null;
  estado: 'programada' | 'check_in' | 'en_curso' | 'reportada' | 'confirmada' | 'en_disputa' | 'walkover' | 'bye';
  siguiente_partida_ganador_id: number | null;
  siguiente_partida_perdedor_id: number | null;
  programada_para: string | null;
  checkin_abre_at: string | null;
  checkin_cierra_at: string | null;
  participaciones: ApiParticipacion[];
}

export interface ApiMensajePartida {
  id: number;
  equipo_id: number | null;
  autor_nombre: string;
  texto: string;
  created_at: string;
}

export interface ApiFilaTabla {
  equipo_id: number;
  equipo_nombre: string;
  posicion: number;
  jugados: number;
  victorias: number;
  empates: number;
  derrotas: number;
  mapas_favor: number;
  mapas_contra: number;
  diferencia_mapas: number;
  puntos: number;
}

export interface ApiTablaGrupo {
  grupo: number | null;
  filas: ApiFilaTabla[];
}

export interface ApiJugador {
  id: number;
  identidad: Record<string, string>;
  orden: number;
  es_suplente: boolean;
  es_capitan: boolean;
  discord_id: string | null;
}

export interface ApiEquipo {
  id: number;
  nombre: string;
  tag: string | null;
  logo_url: string | null;
}

export interface ApiInscripcion {
  id: number;
  edicion_id: number;
  estado: 'pendiente' | 'aprobada' | 'rechazada';
  seed: number | null;
  created_at: string;
  equipo: ApiEquipo;
  jugadores: ApiJugador[];
}

export interface ApiInscripcionCreada {
  inscripcion: ApiInscripcion;
  avisos: string[];
}

export interface ApiPartidaResumen {
  id: number;
  fase_id: number;
  fase_nombre: string;
  ronda: number | null;
  estado: string;
  equipo_a_nombre: string | null;
  equipo_b_nombre: string | null;
  mapas_a: number | null;
  mapas_b: number | null;
  confirmada_at: string | null;
  programada_para: string | null;
}

export interface ApiResumenEdicion {
  edicion: ApiEdicion;
  juego: { codigo: string; nombre: string };
  equipos_aprobados: number;
  fases: ApiFase[];
  ultimos_resultados: ApiPartidaResumen[];
  proximas_partidas: ApiPartidaResumen[];
}

export interface ApiUsuario {
  id: number;
  discord_id: string;
  discord_username: string;
  discord_avatar_url: string | null;
  es_organizador: boolean;
}

export interface ApiTokenOut {
  access_token: string;
  token_type: string;
  usuario: ApiUsuario;
}

export interface ApiErrorDetail {
  detail: string | { msg: string }[];
}

export interface ApiMiInscripcion {
  edicion_id: number;
  edicion_nombre: string;
  edicion_slug: string;
  torneo_nombre: string;
  torneo_slug: string;
  es_capitan: boolean;
  inscripcion: ApiInscripcion;
}

export interface ApiMiPartida {
  partida_id: number;
  fase_id: number;
  fase_nombre: string;
  edicion_nombre: string;
  edicion_slug: string;
  torneo_nombre: string;
  estado: 'programada' | 'check_in' | 'en_curso' | 'reportada' | 'confirmada' | 'en_disputa' | 'walkover' | 'bye';
  ronda: number | null;
  mi_equipo_id: number | null;
  mi_equipo_nombre: string | null;
  rival_equipo_nombre: string | null;
  checkin_cierra_at: string | null;
  programada_para: string | null;
}

export interface ApiUsuarioAdmin {
  id: number;
  discord_id: string;
  discord_username: string;
  discord_avatar_url: string | null;
  es_organizador: boolean;
  puede_gestionar_organizadores: boolean;
  esta_activo: boolean;
  created_at: string;
  ultimo_login_at: string;
}

export interface ApiDisputa {
  id: number;
  partida_id: number;
  abierta_por_equipo_id: number;
  motivo: string;
  evidencia_url: string | null;
  estado: string;
  resolucion: string | null;
  created_at: string;
  resuelta_at: string | null;
}

export interface ApiReporteResultado {
  id: number;
  partida_id: number;
  equipo_reportante_id: number | null;
  marcador_propio: number;
  marcador_rival: number;
  evidencia_url: string | null;
  estado: string;
  vencimiento: string | null;
  confirmado_por_equipo_id: number | null;
  confirmado_at: string | null;
  es_correccion: boolean;
  motivo: string | null;
  aplicado_por_usuario_id: number | null;
  created_at: string;
}
