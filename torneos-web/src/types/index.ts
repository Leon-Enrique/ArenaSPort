export type ModeloCompetencia = 'enfrentamiento_directo' | 'multi_equipo';
export type FormatoFase = 'eliminacion_simple' | 'eliminacion_doble' | 'round_robin' | 'suizo';
// String en vez de union estricta: el admin (Fase B, todavía en mock data)
// usa algunos estados de mentira ('roster_lock', 'en_juego') que no son los
// reales del backend ('inscripciones_cerradas', 'check_in', 'bye', etc).
export type EstadoEdicion = string;
export type EstadoPartida = string;
export type EstadoInscripcion = 'pendiente' | 'aprobada' | 'rechazada';
export type EstadoPago = 'no_requerido' | 'pendiente' | 'confirmado';
export type RolUsuario = 'organizador' | 'staff' | 'capitan' | 'jugador' | 'publico';

export interface Juego {
  id: string;
  codigo: string; // 'mlbb' | 'free_fire' | 'codm' | 'wild_rift'
  nombre: string;
  titularesRequeridos: number;
  suplentesMaximos: number;
  modeloCompetenciaDefault: ModeloCompetencia;
  camposIdentidad: {
    key: string;
    label: string;
    placeholder: string;
    required: boolean;
  }[];
  bannerUrl: string;
  logoUrl: string;
}

export interface Torneo {
  id: string;
  nombre: string;
  slug: string;
  organizadorId?: string;
  organizadorNombre?: string;
  organizadorAvatar?: string;
}

export interface Edicion {
  id: string;
  slug?: string;
  torneoId: string;
  torneoNombre: string;
  juegoId: string;
  juego: Juego;
  numero: number;
  nombre: string;
  estado: EstadoEdicion;
  bolsaPremios: string;
  moneda: string;
  equiposInscritosCount: number;
  maxEquipos: number;
  fechaInicio: string;
  reglamentoUrl?: string;
  descripcion: string;
  sistemasPuntaje?: Record<string, any>;
}

export interface Equipo {
  id: string;
  nombre: string;
  tag: string;
  logoUrl?: string;
  estaActivo: boolean;
  capitanDiscordId?: string;
  capitanNombre?: string;
}

export interface Jugador {
  id: string;
  equipoId: string;
  nombre: string;
  identidad: Record<string, string>; // e.g. { nick: 'Shadow', id_juego: '12345678', server_id: '1002' }
  esSuplente: boolean;
  esCapitan: boolean;
  discordId?: string;
}

export interface Inscripcion {
  id: string;
  edicionId: string;
  equipo: Equipo;
  estado: EstadoInscripcion;
  estadoPago: EstadoPago;
  createdAt: string;
  roster: Jugador[];
}

export interface ParticipacionPartida {
  id: string;
  partidaId: string;
  equipoId: string;
  equipo: Equipo;
  mapasGanados?: number; // Para enfrentamiento directo (MLBB, BO3/BO5)
  esGanador?: boolean;
  posicion?: number;     // Para multi-equipo (Free Fire)
  bajas?: number;        // Kills en caída
  puntos?: number;       // Calculado por sistema de puntos
}

export interface Partida {
  id: string;
  faseId: string;
  grupoId?: string;
  nombreGrupo?: string;
  numeroRonda: number;
  numeroCaida?: number; // Para Battle Royale
  estado: EstadoPartida;
  programadaPara?: string;
  confirmadaAt?: string;
  formatoBo?: number; // 1, 3, 5
  participaciones: ParticipacionPartida[];
  evidenciaUrl?: string;
  reportadoPor?: string;
  bracket?: 'upper' | 'lower' | 'grand_final'; // Para doble eliminación
  isBye?: boolean; // Pase directo (BYE) cuando no hay suficientes equipos para potencia de 2
}

export interface Fase {
  id: string;
  edicionId: string;
  orden: number;
  nombre: string;
  modeloCompetencia: ModeloCompetencia;
  formato: FormatoFase;
  estado: string;
  partidas: Partida[];
  cuposAvance: number;
  // Campos opcionales para grupos
  numGrupos?: number;
  equiposPorGrupo?: number;
  clasificadosPorGrupo?: number;
  // Campos opcionales para BYEs
  numByes?: number;      // cantidad de BYEs generados
  maxSlots?: number;     // tamaño del bracket (potencia de 2)
  equiposInscritos?: number; // equipos reales registrados
}

export interface Disputa {
  id: string;
  partidaId: string;
  partida: Partida;
  abiertaPorEquipo: Equipo;
  motivo: string;
  evidenciaUrl: string;
  estado: 'abierta' | 'en_revision' | 'resuelta';
  resolucion?: string;
  resueltaPor?: string;
  createdAt: string;
}

export interface Usuario {
  id: string;
  nombre: string;
  email: string;
  avatarUrl: string;
  discordId: string;
  rol: RolUsuario;
}
