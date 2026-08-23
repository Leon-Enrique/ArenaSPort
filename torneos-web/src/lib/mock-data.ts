import { Juego, Torneo, Edicion, Fase, Equipo, Partida, Inscripcion, Disputa, Usuario } from '@/types';

// ────────────────────────────────────────────
// JUEGOS
// ────────────────────────────────────────────
export const MOCK_JUEGOS: Juego[] = [
  {
    id: 'juego-1',
    codigo: 'mlbb',
    nombre: 'Mobile Legends: Bang Bang',
    titularesRequeridos: 5,
    suplentesMaximos: 2,
    modeloCompetenciaDefault: 'enfrentamiento_directo',
    camposIdentidad: [
      { key: 'nick', label: 'Nick en Juego', placeholder: 'Ej. BeastMode', required: true },
      { key: 'id_juego', label: 'ID de Juego (Game ID)', placeholder: 'Ej. 123456789', required: true },
      { key: 'server_id', label: 'Server ID (Zona)', placeholder: 'Ej. 1002', required: true }
    ],
    bannerUrl: 'https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=1200&auto=format&fit=crop',
    logoUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=200&auto=format&fit=crop'
  },
  {
    id: 'juego-2',
    codigo: 'free_fire',
    nombre: 'Free Fire Battle Royale',
    titularesRequeridos: 4,
    suplentesMaximos: 1,
    modeloCompetenciaDefault: 'multi_equipo',
    camposIdentidad: [
      { key: 'nick', label: 'Nick de Jugador', placeholder: 'Ej. FF_ProGuy', required: true },
      { key: 'uid', label: 'UID de Free Fire', placeholder: 'Ej. 987654321', required: true }
    ],
    bannerUrl: 'https://images.unsplash.com/photo-1511512578047-dfb367046420?q=80&w=1200&auto=format&fit=crop',
    logoUrl: 'https://images.unsplash.com/photo-1579373903781-fd5c0c30c4cd?q=80&w=200&auto=format&fit=crop'
  },
  {
    id: 'juego-3',
    codigo: 'codm',
    nombre: 'Call of Duty: Mobile MP',
    titularesRequeridos: 5,
    suplentesMaximos: 2,
    modeloCompetenciaDefault: 'enfrentamiento_directo',
    camposIdentidad: [
      { key: 'nick', label: 'Activision Nick', placeholder: 'Ej. Viper#1234', required: true },
      { key: 'uid', label: 'CODM UID', placeholder: 'Ej. 6789012345', required: true }
    ],
    bannerUrl: 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=1200&auto=format&fit=crop',
    logoUrl: 'https://images.unsplash.com/photo-1563089145-599997674d42?q=80&w=200&auto=format&fit=crop'
  }
];

// ────────────────────────────────────────────
// EQUIPOS
// ────────────────────────────────────────────
export const MOCK_EQUIPOS: Equipo[] = [
  { id: 'eq-1', nombre: 'Alpha Esports', tag: 'ALP', estaActivo: true, capitanNombre: 'Shadow' },
  { id: 'eq-2', nombre: 'Cyber Titans', tag: 'CTN', estaActivo: true, capitanNombre: 'Nexus' },
  { id: 'eq-3', nombre: 'Viper Warriors', tag: 'VPW', estaActivo: true, capitanNombre: 'Viper' },
  { id: 'eq-4', nombre: 'Nova Squad', tag: 'NVS', estaActivo: true, capitanNombre: 'Kira' },
  { id: 'eq-5', nombre: 'Phoenix Gaming', tag: 'PHX', estaActivo: true, capitanNombre: 'Blaze' },
  { id: 'eq-6', nombre: 'Immortal Beasts', tag: 'IBE', estaActivo: true, capitanNombre: 'Thor' },
  { id: 'eq-7', nombre: 'Shadow Renegades', tag: 'SRN', estaActivo: true, capitanNombre: 'Ghost' },
  { id: 'eq-8', nombre: 'Apex Hunters', tag: 'APH', estaActivo: true, capitanNombre: 'Hunter' },
  { id: 'eq-9', nombre: 'Fury Kings', tag: 'FRK', estaActivo: true, capitanNombre: 'Rex' },
  { id: 'eq-10', nombre: 'Vortex Legion', tag: 'VTX', estaActivo: true, capitanNombre: 'Storm' },
  { id: 'eq-11', nombre: 'Solar Knights', tag: 'SLK', estaActivo: true, capitanNombre: 'Sol' },
  { id: 'eq-12', nombre: 'Kraken Esports', tag: 'KRK', estaActivo: true, capitanNombre: 'Poseidon' }
];

// ────────────────────────────────────────────
// ROSTERS COMPLETOS por equipo
// ────────────────────────────────────────────
export const MOCK_ROSTERS: Record<string, {
  jugadorId: string; nick: string; idJuego: string; serverId?: string; uid?: string;
  esCapitan: boolean; esSuplente: boolean; discordTag: string;
}[]> = {
  'eq-1': [
    { jugadorId: 'j-1-1', nick: 'Shadow', idJuego: '12345678', serverId: '1002', esCapitan: true, esSuplente: false, discordTag: 'Shadow#1234' },
    { jugadorId: 'j-1-2', nick: 'ViperGuy', idJuego: '23456789', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'ViperGuy#5678' },
    { jugadorId: 'j-1-3', nick: 'BlazeMobile', idJuego: '34567890', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'Blaze#9001' },
    { jugadorId: 'j-1-4', nick: 'KiraMLBB', idJuego: '45678901', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'Kira#2020' },
    { jugadorId: 'j-1-5', nick: 'StormPro', idJuego: '56789012', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'Storm#4444' },
    { jugadorId: 'j-1-6', nick: 'SubMaster', idJuego: '67890123', serverId: '1002', esCapitan: false, esSuplente: true, discordTag: 'SubMaster#7777' },
  ],
  'eq-2': [
    { jugadorId: 'j-2-1', nick: 'Nexus', idJuego: '11112222', serverId: '1002', esCapitan: true, esSuplente: false, discordTag: 'Nexus#5678' },
    { jugadorId: 'j-2-2', nick: 'CyberZero', idJuego: '22223333', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'CyberZero#1111' },
    { jugadorId: 'j-2-3', nick: 'TitanX', idJuego: '33334444', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'TitanX#2222' },
    { jugadorId: 'j-2-4', nick: 'GamerOne', idJuego: '44445555', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'GamerOne#3333' },
    { jugadorId: 'j-2-5', nick: 'Hyper', idJuego: '55556666', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'Hyper#4444' },
    { jugadorId: 'j-2-6', nick: 'BackupCyber', idJuego: '66667777', serverId: '1002', esCapitan: false, esSuplente: true, discordTag: 'BackupC#9999' },
  ],
  'eq-3': [
    { jugadorId: 'j-3-1', nick: 'Viper', idJuego: '77778888', serverId: '1002', esCapitan: true, esSuplente: false, discordTag: 'Viper#3456' },
    { jugadorId: 'j-3-2', nick: 'Phantom', idJuego: '88889999', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'Phantom#5555' },
    { jugadorId: 'j-3-3', nick: 'WarlordZ', idJuego: '99990000', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'Warlord#6666' },
    { jugadorId: 'j-3-4', nick: 'IronFist', idJuego: '10001001', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'IronFist#7777' },
    { jugadorId: 'j-3-5', nick: 'SniperV', idJuego: '20002002', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'SniperV#8888' },
  ],
  'eq-4': [
    { jugadorId: 'j-4-1', nick: 'Kira', idJuego: '30003003', serverId: '1002', esCapitan: true, esSuplente: false, discordTag: 'Kira#9999' },
    { jugadorId: 'j-4-2', nick: 'NovaBolt', idJuego: '40004004', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'NovaBolt#1010' },
    { jugadorId: 'j-4-3', nick: 'GalaxyMKZ', idJuego: '50005005', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'GalaxyMKZ#2020' },
    { jugadorId: 'j-4-4', nick: 'PulsarX', idJuego: '60006006', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'Pulsar#3030' },
    { jugadorId: 'j-4-5', nick: 'CosmicPro', idJuego: '70007007', serverId: '1002', esCapitan: false, esSuplente: false, discordTag: 'Cosmic#4040' },
  ],
  'eq-5': [
    { jugadorId: 'j-5-1', nick: 'BlazeFF', idJuego: 'FF-998877', uid: '998877665', esCapitan: true, esSuplente: false, discordTag: 'BlazeFF#9999' },
    { jugadorId: 'j-5-2', nick: 'HunterFire', idJuego: 'FF-887766', uid: '887766554', esCapitan: false, esSuplente: false, discordTag: 'HunterFire#1234' },
    { jugadorId: 'j-5-3', nick: 'KillerPro', idJuego: 'FF-776655', uid: '776655443', esCapitan: false, esSuplente: false, discordTag: 'KillerPro#2345' },
    { jugadorId: 'j-5-4', nick: 'Sniper07', idJuego: 'FF-665544', uid: '665544332', esCapitan: false, esSuplente: false, discordTag: 'Sniper07#3456' },
    { jugadorId: 'j-5-5', nick: 'ReserveMan', idJuego: 'FF-554433', uid: '554433221', esCapitan: false, esSuplente: true, discordTag: 'Reserve#4567' },
  ],
  'eq-6': [
    { jugadorId: 'j-6-1', nick: 'ThorBeast', idJuego: 'FF-112233', uid: '112233445', esCapitan: true, esSuplente: false, discordTag: 'Thor#1111' },
    { jugadorId: 'j-6-2', nick: 'LokiKills', idJuego: 'FF-223344', uid: '223344556', esCapitan: false, esSuplente: false, discordTag: 'Loki#2222' },
    { jugadorId: 'j-6-3', nick: 'OdinStrike', idJuego: 'FF-334455', uid: '334455667', esCapitan: false, esSuplente: false, discordTag: 'Odin#3333' },
    { jugadorId: 'j-6-4', nick: 'Valkyrie', idJuego: 'FF-445566', uid: '445566778', esCapitan: false, esSuplente: false, discordTag: 'Valkyrie#4444' },
  ],
};

// ────────────────────────────────────────────
// TORNEOS (nuevo modelo ampliado)
// ────────────────────────────────────────────
export const MOCK_TORNEOS = [
  {
    id: 'torneo-1',
    nombre: 'Copa Latam Esports',
    slug: 'copa-latam-esports',
    descripcion: 'El torneo oficial de esports móviles de LATAM. Compite por la gloria y grandes premios en efectivo.',
    organizadorId: 'usr-1',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    estado: 'activo',
    logoUrl: null,
    bannerUrl: 'https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=1200&auto=format&fit=crop',
    edicionesCount: 2,
    createdAt: '2025-12-01T00:00:00Z',
  },
  {
    id: 'torneo-32',
    nombre: 'Torneo Continental MLBB (32 Slots)',
    slug: 'torneo-continental-32',
    descripcion: 'Gran certamen de 32 escuadras de toda la región en cuadro de eliminación simple de 5 rondas completadas.',
    organizadorId: 'usr-1',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    estado: 'finalizado',
    logoUrl: null,
    bannerUrl: 'https://images.unsplash.com/photo-1511512578047-dfb367046420?q=80&w=1200&auto=format&fit=crop',
    edicionesCount: 1,
    createdAt: '2026-06-10T00:00:00Z',
  },
  {
    id: 'torneo-64-triple',
    nombre: 'Copa Mundial Masters 64 (3 Fases Finalizadas)',
    slug: 'copa-mundial-64-triple',
    descripcion: 'Mega Torneo Finalizado: Fase 1 (16 Grupos de 4) ➔ Fase 2 (Octavos 16 a 8 BO3) ➔ Fase 3 (Gran Final Top 8 Doble Eliminación).',
    organizadorId: 'usr-1',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    estado: 'completada',
    logoUrl: null,
    bannerUrl: 'https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=1200&auto=format&fit=crop',
    edicionesCount: 1,
    createdAt: '2026-08-01T00:00:00Z',
  },
  {
    id: 'torneo-64',
    nombre: 'Copa Mayor Mobile Masters (64 Slots)',
    slug: 'copa-mayor-64',
    descripcion: 'El mega torneo más grande de la temporada con 64 escuadras y 6 rondas de bracket eliminatorio.',
    organizadorId: 'usr-1',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    estado: 'finalizado',
    logoUrl: null,
    bannerUrl: 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=1200&auto=format&fit=crop',
    edicionesCount: 1,
    createdAt: '2026-05-01T00:00:00Z',
  },
  {
    id: 'torneo-2',
    nombre: 'Free Fire Masters League',
    slug: 'free-fire-masters',
    descripcion: 'Gran Liga Battle Royale para los mejores equipos de Free Fire en la región.',
    organizadorId: 'usr-1',
    juegoId: 'juego-2',
    juego: MOCK_JUEGOS[1],
    estado: 'activo',
    logoUrl: null,
    bannerUrl: 'https://images.unsplash.com/photo-1511512578047-dfb367046420?q=80&w=1200&auto=format&fit=crop',
    edicionesCount: 4,
    createdAt: '2025-10-15T00:00:00Z',
  },
  {
    id: 'torneo-3',
    nombre: 'CODM Championship Series',
    slug: 'codm-championship',
    descripcion: 'Serie de campeonatos 5v5 para los mejores pelotones de CODM Mobile.',
    organizadorId: 'usr-1',
    juegoId: 'juego-3',
    juego: MOCK_JUEGOS[2],
    estado: 'borrador',
    logoUrl: null,
    bannerUrl: 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=1200&auto=format&fit=crop',
    edicionesCount: 1,
    createdAt: '2026-07-20T00:00:00Z',
  },
];

// ────────────────────────────────────────────
// EDICIONES
// ────────────────────────────────────────────
export const MOCK_EDICIONES: Edicion[] = [
  {
    id: 'ed-1',
    torneoId: 'torneo-1',
    torneoNombre: 'Copa Latam Esports',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    numero: 2,
    nombre: 'Copa Latam MLBB Season 2 - Finals',
    estado: 'en_curso',
    bolsaPremios: '$1,500 USD',
    moneda: 'USD',
    equiposInscritosCount: 8,
    maxEquipos: 8,
    fechaInicio: '2026-08-20',
    descripcion: 'El torneo oficial de Mobile Legends Bang Bang para LATAM con eliminación directa.',
    sistemasPuntaje: { victoria: 1, derrota: 0 }
  },
  {
    id: 'ed-32',
    torneoId: 'torneo-32',
    torneoNombre: 'Torneo Continental MLBB (32 Slots)',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    numero: 1,
    nombre: 'Torneo Continental MLBB (32 Equipos - Finalizado)',
    estado: 'finalizado',
    bolsaPremios: '$3,000 USD',
    moneda: 'USD',
    equiposInscritosCount: 32,
    maxEquipos: 32,
    fechaInicio: '2026-07-10',
    descripcion: 'Torneo continental completado con 32 escuadras en 5 rondas de bracket directo.',
    sistemasPuntaje: { victoria: 1, derrota: 0 }
  },
  {
    id: 'ed-64-triple',
    torneoId: 'torneo-64-triple',
    torneoNombre: 'Copa Mundial Masters 64 (3 Fases Finalizadas)',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    numero: 1,
    nombre: 'Copa Mundial Masters 64 - Grand Championship',
    estado: 'finalizado',
    bolsaPremios: '$5,000 USD',
    moneda: 'USD',
    equiposInscritosCount: 64,
    maxEquipos: 64,
    fechaInicio: '2026-08-01',
    descripcion: 'Mega Torneo Finalizado: Fase 1 (16 Grupos de 4) ➔ Fase 2 (Octavos 16 a 8 BO3) ➔ Fase 3 (Gran Final Top 8 Doble Eliminación).',
    sistemasPuntaje: { victoria: 3, derrota: 0 }
  },
  {
    id: 'ed-64',
    torneoId: 'torneo-64',
    torneoNombre: 'Copa Mayor Mobile Masters (64 Slots)',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    numero: 1,
    nombre: 'Copa Mayor Mobile Masters (64 Equipos - Finalizado)',
    estado: 'finalizado',
    bolsaPremios: '$5,000 USD',
    moneda: 'USD',
    equiposInscritosCount: 64,
    maxEquipos: 64,
    fechaInicio: '2026-06-01',
    descripcion: 'Mega campeonato de 64 equipos con 6 rondas de eliminatoria directa completadas.',
    sistemasPuntaje: { victoria: 1, derrota: 0 }
  },
  {
    id: 'ed-1b',
    torneoId: 'torneo-1',
    torneoNombre: 'Copa Latam Esports',
    juegoId: 'juego-1',
    juego: MOCK_JUEGOS[0],
    numero: 1,
    nombre: 'Copa Latam MLBB Season 1',
    estado: 'finalizado',
    bolsaPremios: '$800 USD',
    moneda: 'USD',
    equiposInscritosCount: 8,
    maxEquipos: 8,
    fechaInicio: '2026-04-10',
    descripcion: 'Primera edición del torneo oficial de MLBB.',
    sistemasPuntaje: { victoria: 1, derrota: 0 }
  },
  {
    id: 'ed-2',
    torneoId: 'torneo-2',
    torneoNombre: 'Free Fire Masters League',
    juegoId: 'juego-2',
    juego: MOCK_JUEGOS[1],
    numero: 4,
    nombre: 'Free Fire Clash of Titans S4',
    estado: 'inscripciones_abiertas',
    bolsaPremios: '$2,000 USD',
    moneda: 'USD',
    equiposInscritosCount: 12,
    maxEquipos: 24,
    fechaInicio: '2026-08-25',
    descripcion: 'Gran Liga Battle Royale de 5 caídas por jornada.',
    sistemasPuntaje: {
      posiciones: { 1: 12, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1, 11: 0, 12: 0 },
      puntosPorBaja: 1
    }
  },
  {
    id: 'ed-3',
    torneoId: 'torneo-3',
    torneoNombre: 'CODM Championship Series',
    juegoId: 'juego-3',
    juego: MOCK_JUEGOS[2],
    numero: 1,
    nombre: 'CODM Mobile Masters Season 1',
    estado: 'inscripciones_abiertas',
    bolsaPremios: '$800 USD',
    moneda: 'USD',
    equiposInscritosCount: 6,
    maxEquipos: 16,
    fechaInicio: '2026-09-01',
    descripcion: 'Torneo 5v5 Buscar y Destruir + Dominio.'
  }
];

// ────────────────────────────────────────────
// INSCRIPCIONES con rosters detallados
// ────────────────────────────────────────────
export const MOCK_INSCRIPCIONES_ADMIN = [
  {
    id: 'ins-1', equipoId: 'eq-1', edicionId: 'ed-1',
    equipo: MOCK_EQUIPOS[0], estado: 'aprobada', seed: 1,
    contactoWhatsapp: '+591 76543210', contactoDiscord: 'Shadow#1234',
    roster: MOCK_ROSTERS['eq-1'], createdAt: '2026-08-01T10:30:00Z',
  },
  {
    id: 'ins-2', equipoId: 'eq-2', edicionId: 'ed-1',
    equipo: MOCK_EQUIPOS[1], estado: 'aprobada', seed: 2,
    contactoWhatsapp: '+591 71234567', contactoDiscord: 'Nexus#5678',
    roster: MOCK_ROSTERS['eq-2'], createdAt: '2026-08-02T09:15:00Z',
  },
  {
    id: 'ins-3', equipoId: 'eq-3', edicionId: 'ed-1',
    equipo: MOCK_EQUIPOS[2], estado: 'aprobada', seed: 3,
    contactoWhatsapp: '+591 77778888', contactoDiscord: 'Viper#3456',
    roster: MOCK_ROSTERS['eq-3'], createdAt: '2026-08-02T14:00:00Z',
  },
  {
    id: 'ins-4', equipoId: 'eq-4', edicionId: 'ed-1',
    equipo: MOCK_EQUIPOS[3], estado: 'aprobada', seed: 4,
    contactoWhatsapp: '+591 79999000', contactoDiscord: 'Kira#9999',
    roster: MOCK_ROSTERS['eq-4'], createdAt: '2026-08-03T11:00:00Z',
  },
  {
    id: 'ins-5', equipoId: 'eq-5', edicionId: 'ed-2',
    equipo: MOCK_EQUIPOS[4], estado: 'pendiente', seed: null,
    contactoWhatsapp: '+591 79876543', contactoDiscord: 'BlazeFF#9999',
    roster: MOCK_ROSTERS['eq-5'], createdAt: '2026-08-10T16:00:00Z',
  },
  {
    id: 'ins-6', equipoId: 'eq-6', edicionId: 'ed-2',
    equipo: MOCK_EQUIPOS[5], estado: 'pendiente', seed: null,
    contactoWhatsapp: '+591 70011223', contactoDiscord: 'Thor#1111',
    roster: MOCK_ROSTERS['eq-6'], createdAt: '2026-08-11T08:30:00Z',
  },
  {
    id: 'ins-7', equipoId: 'eq-7', edicionId: 'ed-2',
    equipo: MOCK_EQUIPOS[6], estado: 'rechazada', seed: null,
    motivoRechazo: 'Roster incompleto: faltan 2 titulares.',
    contactoWhatsapp: '+591 70022334', contactoDiscord: 'Ghost#7890',
    roster: [], createdAt: '2026-08-09T20:00:00Z',
  },
];

// ────────────────────────────────────────────
// ────────────────────────────────────────────
// FASES
// ────────────────────────────────────────────
export const MOCK_FASES_MLBB: Fase[] = [
  {
    id: 'fase-bracket-main',
    edicionId: 'ed-1',
    orden: 1,
    nombre: '1 - Bracket Playoffs (Eliminación Simple / 8 Slots)',
    modeloCompetencia: 'enfrentamiento_directo',
    formato: 'eliminacion_simple',
    estado: 'en_curso',
    cuposAvance: 1,
    partidas: [
      // ── ROUND 1: CUARTOS DE FINAL (4 Partidas) ──
      {
        id: 'part-r1-1', faseId: 'fase-bracket-main', numeroRonda: 1, nombreGrupo: 'Cuartos Match #1', estado: 'confirmada',
        programadaPara: '2026-08-16T17:00:00Z', confirmadaAt: '2026-08-16T18:00:00Z', formatoBo: 3,
        participaciones: [
          { id: 'p-1', partidaId: 'part-r1-1', equipoId: 'eq-1', equipo: MOCK_EQUIPOS[0], mapasGanados: 2, esGanador: true, puntos: 2 },
          { id: 'p-2', partidaId: 'part-r1-1', equipoId: 'eq-2', equipo: MOCK_EQUIPOS[1], mapasGanados: 0, esGanador: false, puntos: 0 }
        ]
      },
      {
        id: 'part-r1-2', faseId: 'fase-bracket-main', numeroRonda: 1, nombreGrupo: 'Cuartos Match #2', estado: 'confirmada',
        programadaPara: '2026-08-16T18:15:00Z', confirmadaAt: '2026-08-16T19:10:00Z', formatoBo: 3,
        participaciones: [
          { id: 'p-3', partidaId: 'part-r1-2', equipoId: 'eq-3', equipo: MOCK_EQUIPOS[2], mapasGanados: 2, esGanador: true, puntos: 2 },
          { id: 'p-4', partidaId: 'part-r1-2', equipoId: 'eq-4', equipo: MOCK_EQUIPOS[3], mapasGanados: 1, esGanador: false, puntos: 1 }
        ]
      },
      {
        id: 'part-r1-3', faseId: 'fase-bracket-main', numeroRonda: 1, nombreGrupo: 'Cuartos Match #3', estado: 'confirmada',
        programadaPara: '2026-08-16T19:30:00Z', confirmadaAt: '2026-08-16T20:20:00Z', formatoBo: 3,
        participaciones: [
          { id: 'p-5', partidaId: 'part-r1-3', equipoId: 'eq-5', equipo: MOCK_EQUIPOS[4], mapasGanados: 2, esGanador: true, puntos: 2 },
          { id: 'p-6', partidaId: 'part-r1-3', equipoId: 'eq-6', equipo: MOCK_EQUIPOS[5], mapasGanados: 0, esGanador: false, puntos: 0 }
        ]
      },
      {
        id: 'part-r1-4', faseId: 'fase-bracket-main', numeroRonda: 1, nombreGrupo: 'Cuartos Match #4', estado: 'confirmada',
        programadaPara: '2026-08-16T20:45:00Z', confirmadaAt: '2026-08-16T21:40:00Z', formatoBo: 3,
        participaciones: [
          { id: 'p-7', partidaId: 'part-r1-4', equipoId: 'eq-7', equipo: MOCK_EQUIPOS[6], mapasGanados: 2, esGanador: true, puntos: 2 },
          { id: 'p-8', partidaId: 'part-r1-4', equipoId: 'eq-8', equipo: MOCK_EQUIPOS[7], mapasGanados: 1, esGanador: false, puntos: 1 }
        ]
      },

      // ── ROUND 2: SEMIFINALES (2 Partidas) ──
      {
        id: 'part-r2-1', faseId: 'fase-bracket-main', numeroRonda: 2, nombreGrupo: 'Semifinal #1', estado: 'confirmada',
        programadaPara: '2026-08-17T18:00:00Z', confirmadaAt: '2026-08-17T19:25:00Z', formatoBo: 3,
        participaciones: [
          { id: 'p-9', partidaId: 'part-r2-1', equipoId: 'eq-1', equipo: MOCK_EQUIPOS[0], mapasGanados: 2, esGanador: true, puntos: 2 },
          { id: 'p-10', partidaId: 'part-r2-1', equipoId: 'eq-3', equipo: MOCK_EQUIPOS[2], mapasGanados: 1, esGanador: false, puntos: 1 }
        ]
      },
      {
        id: 'part-r2-2', faseId: 'fase-bracket-main', numeroRonda: 2, nombreGrupo: 'Semifinal #2', estado: 'en_juego',
        programadaPara: '2026-08-17T19:45:00Z', formatoBo: 3,
        participaciones: [
          { id: 'p-11', partidaId: 'part-r2-2', equipoId: 'eq-5', equipo: MOCK_EQUIPOS[4], mapasGanados: 1, esGanador: false, puntos: 1 },
          { id: 'p-12', partidaId: 'part-r2-2', equipoId: 'eq-7', equipo: MOCK_EQUIPOS[6], mapasGanados: 1, esGanador: false, puntos: 1 }
        ]
      },

      // ── ROUND 3: GRAN FINAL (1 Partida) ──
      {
        id: 'part-r3-1', faseId: 'fase-bracket-main', numeroRonda: 3, nombreGrupo: 'Gran Final', estado: 'programada',
        programadaPara: '2026-08-18T20:00:00Z', formatoBo: 5,
        participaciones: [
          { id: 'p-13', partidaId: 'part-r3-1', equipoId: 'eq-1', equipo: MOCK_EQUIPOS[0], mapasGanados: 0, esGanador: false, puntos: 0 },
          { id: 'p-14', partidaId: 'part-r3-1', equipoId: null, equipo: undefined, mapasGanados: 0, esGanador: false, puntos: 0 }
        ]
      }
    ]
  },
  {
    id: 'fase-grupos',
    edicionId: 'ed-1',
    orden: 2,
    nombre: '2 - Fase Previa de Grupos (Round Robin)',
    modeloCompetencia: 'enfrentamiento_directo',
    formato: 'round_robin',
    estado: 'finalizada',
    cuposAvance: 4,
    partidas: [
      {
        id: 'part-g1', faseId: 'fase-grupos', numeroRonda: 1, estado: 'confirmada',
        programadaPara: '2026-08-10T18:00:00Z', formatoBo: 1,
        participaciones: [
          { id: 'pg1', partidaId: 'part-g1', equipoId: 'eq-1', equipo: MOCK_EQUIPOS[0], mapasGanados: 1, esGanador: true, puntos: 3 },
          { id: 'pg2', partidaId: 'part-g1', equipoId: 'eq-2', equipo: MOCK_EQUIPOS[1], mapasGanados: 0, esGanador: false, puntos: 0 }
        ]
      },
      {
        id: 'part-g2', faseId: 'fase-grupos', numeroRonda: 1, estado: 'confirmada',
        programadaPara: '2026-08-10T19:00:00Z', formatoBo: 1,
        participaciones: [
          { id: 'pg3', partidaId: 'part-g2', equipoId: 'eq-3', equipo: MOCK_EQUIPOS[2], mapasGanados: 1, esGanador: true, puntos: 3 },
          { id: 'pg4', partidaId: 'part-g2', equipoId: 'eq-4', equipo: MOCK_EQUIPOS[3], mapasGanados: 0, esGanador: false, puntos: 0 }
        ]
      }
    ]
  }
];

function generarBracketCompleto(faseId: string, edicionId: string, totalEquipos: number, nombreFase: string): Fase {
  const nombresBase = [
    'Alpha Esports', 'Cyber Titans', 'Viper Warriors', 'Nova Squad',
    'Phoenix Gaming', 'Immortal Beasts', 'Shadow Renegades', 'Apex Hunters',
    'Fury Kings', 'Vortex Legion', 'Solar Knights', 'Kraken Esports',
    'Thunder Wolves', 'Ghost Legion', 'Phantom Strike', 'Dragon Riders',
    'Iron Vanguard', 'Chaos Syndicate', 'Zenith Force', 'Nemesis Squad',
    'Oblivion Clan', 'Spectre Gaming', 'Titanium Wolves', 'Eclipse Gaming',
    'Aether Titans', 'Frostbite Esports', 'Havoc Unit', 'Valkyrie Prime',
    'Raptor Gaming', 'Quantum Shift', 'Zero Gravity', 'Inferno Esports',
    'Blackout Gaming', 'Samurai Esports', 'Nightshade Squad', 'Valiant Gaming',
    'Hydra Battalion', 'Starlight Gaming', 'Omega Protocol', 'Blizzard Force',
    'Crimson Tide', 'Reaper Elite', 'Tempest Gaming', 'Spartan Esports',
    'Glacier Kings', 'Sentinel Corps', 'Apex Legends BR', 'Rampage Squad',
    'Vanguard Prime', 'Pulse Gaming', 'Obsidian Wolves', 'Wildfire Esports',
    'Nexus Core', 'Overdrive Gaming', 'Galactic Force', 'Abyss Clan',
    'Solaris Gaming', 'Horizon Unit', 'Dynasty Esports', 'Raptor Claw',
    'Vindicator X', 'Alpha Centauri', 'Echo Battalion', 'Prime Titans'
  ];

  const equipos: Equipo[] = Array.from({ length: totalEquipos }).map((_, i) => ({
    id: `eq-gen-${totalEquipos}-${i + 1}`,
    nombre: nombresBase[i] || `Squad #${i + 1}`,
    tag: (nombresBase[i] ? nombresBase[i].split(' ').map(w => w[0]).join('').slice(0, 3) : `S${i + 1}`).toUpperCase(),
    estaActivo: true,
  }));

  const totalRondas = Math.log2(totalEquipos);
  const partidas: Partida[] = [];
  let equiposRondaActual = [...equipos];

  for (let r = 1; r <= totalRondas; r++) {
    const numPartidas = totalEquipos / Math.pow(2, r);
    const ganadoresRonda: Equipo[] = [];

    for (let m = 0; m < numPartidas; m++) {
      const eqA = equiposRondaActual[m * 2];
      const eqB = equiposRondaActual[m * 2 + 1];
      const esUltima = r === totalRondas;
      const esSemi = r === totalRondas - 1;
      const labelMatch = esUltima ? 'Gran Final' : esSemi ? `Semifinal #${m + 1}` : `Match R${r} #${m + 1}`;

      const scoreA = esUltima ? 3 : 2;
      const scoreB = esUltima ? 1 : (m % 2 === 0 ? 0 : 1);

      ganadoresRonda.push(eqA);

      partidas.push({
        id: `part-${totalEquipos}-r${r}-${m + 1}`,
        faseId,
        numeroRonda: r,
        nombreGrupo: labelMatch,
        estado: 'confirmada',
        formatoBo: esUltima ? 5 : 3,
        participaciones: [
          {
            id: `p-${totalEquipos}-r${r}-${m + 1}-a`,
            partidaId: `part-${totalEquipos}-r${r}-${m + 1}`,
            equipoId: eqA?.id || null,
            equipo: eqA,
            mapasGanados: scoreA,
            esGanador: true,
            puntos: scoreA
          },
          {
            id: `p-${totalEquipos}-r${r}-${m + 1}-b`,
            partidaId: `part-${totalEquipos}-r${r}-${m + 1}`,
            equipoId: eqB?.id || null,
            equipo: eqB,
            mapasGanados: scoreB,
            esGanador: false,
            puntos: scoreB
          }
        ]
      });
    }

    equiposRondaActual = ganadoresRonda;
  }

  return {
    id: faseId,
    edicionId,
    orden: 1,
    nombre: nombreFase,
    modeloCompetencia: 'enfrentamiento_directo',
    formato: 'eliminacion_simple',
    estado: 'finalizada',
    cuposAvance: 1,
    partidas
  };
}

// ──────────────────────────────────────────────────────────────────────────────
// GENERADOR DE OCTAVOS 16 → 8 (Solo 1 ronda, 8 partidas, 8 clasificados)
// Los 8 ganadores son los mismos que luego entran a la Fase 3 (Doble Elim)
// ──────────────────────────────────────────────────────────────────────────────
export function generarOctavos16a8(faseId: string, edicionId: string, nombreFase: string): Fase {
  // 8 ganadores (avanzan a Fase 3)
  const winners = [
    'Alpha Esports', 'Cyber Titans', 'Viper Warriors', 'Nova Squad',
    'Phoenix Gaming', 'Immortal Beasts', 'Shadow Renegades', 'Apex Hunters'
  ];
  // 8 eliminados en esta fase
  const losers = [
    'Fury Kings', 'Vortex Legion', 'Solar Knights', 'Kraken Esports',
    'Thunder Wolves', 'Ghost Legion', 'Phantom Strike', 'Dragon Riders'
  ];

  const makeEq = (nombre: string, idx: number) => ({
    id: `eq-oct-${idx + 1}`,
    nombre,
    tag: nombre.split(' ').map((w: string) => w[0]).join('').slice(0, 3).toUpperCase(),
    estaActivo: true,
  });

  const wEqs = winners.map(makeEq);
  const lEqs = losers.map((n, i) => makeEq(n, i + 8));

  const partidas: Partida[] = winners.map((_, i) => {
    const winner = wEqs[i];
    const loser = lEqs[i];
    return {
      id: `${faseId}-oct-${i + 1}`,
      faseId,
      numeroRonda: 1,
      nombreGrupo: `Octavos #${i + 1}`,
      estado: 'confirmada' as any,
      formatoBo: 3,
      participaciones: [
        { id: `${faseId}-oct-${i + 1}-a`, partidaId: `${faseId}-oct-${i + 1}`, equipoId: winner.id, equipo: winner, mapasGanados: 2, esGanador: true, puntos: 2 },
        { id: `${faseId}-oct-${i + 1}-b`, partidaId: `${faseId}-oct-${i + 1}`, equipoId: loser.id, equipo: loser, mapasGanados: (i % 3 === 0 ? 1 : 0), esGanador: false, puntos: 0 },
      ]
    };
  });

  return {
    id: faseId,
    edicionId,
    orden: 2,
    nombre: nombreFase,
    modeloCompetencia: 'enfrentamiento_directo',
    formato: 'eliminacion_simple',
    estado: 'finalizada',
    cuposAvance: 8,
    partidas
  };
}

// ──────────────────────────────────────────────────────────────────────────────
// GENERADOR DE DOBLE ELIMINACIÓN (Upper Bracket + Lower Bracket + Gran Final)
// Para 8 equipos: UB Cuartos, UB Semis, LB R1, LB R2 (Semis), LB Final, Gran Final
// ──────────────────────────────────────────────────────────────────────────────
export function generarDobleEliminacion(faseId: string, edicionId: string, nombreFase: string): Fase {
  const nombres8 = [
    'Alpha Esports',    // [0] UB Champion
    'Cyber Titans',     // [1] Pierde UB Final → LB Final → llega a GF
    'Viper Warriors',   // [2] Pierde UB SF → LB R2 → LB SF
    'Nova Squad',       // [3] Pierde UB SF → LB R2 → LB Final → pierde
    'Phoenix Gaming',   // [4] Pierde UB QF → LB R1 → pierde
    'Immortal Beasts',  // [5] Pierde UB QF → LB R1 → pierde
    'Shadow Renegades', // [6] Pierde UB QF → LB R1 → LB R2 → pierde
    'Apex Hunters',     // [7] Pierde UB QF → LB R1 → LB R2 → pierde
  ];
  const eqs = nombres8.map((n, i) => ({
    id: `eq-de-${i + 1}`,
    nombre: n,
    tag: n.split(' ').map((w: string) => w[0]).join('').slice(0, 3).toUpperCase(),
    estaActivo: true,
  }));

  const [alpha, cyber, viper, nova, phoenix, immortal, shadow, apex] = eqs;

  const makeMatch = (
    id: string, ronda: number, bracket: 'upper' | 'lower' | 'grand_final',
    nombreMatch: string, eqA: any, eqB: any, scoreA: number, scoreB: number,
    formatoBo: number = 3
  ): Partida => ({
    id,
    faseId,
    numeroRonda: ronda,
    nombreGrupo: nombreMatch,
    estado: 'confirmada' as any,
    formatoBo,
    bracket,
    participaciones: [
      { id: `${id}-a`, partidaId: id, equipoId: eqA?.id, equipo: eqA, mapasGanados: scoreA, esGanador: scoreA > scoreB, puntos: scoreA },
      { id: `${id}-b`, partidaId: id, equipoId: eqB?.id, equipo: eqB, mapasGanados: scoreB, esGanador: scoreB > scoreA, puntos: scoreB },
    ]
  });

  const partidas: Partida[] = [
    // ── UPPER BRACKET ──────────────────────────────────────
    // R1: Cuartos de Final (8 → 4 ganadores UB, 4 perdedores → LB R1)
    makeMatch(`${faseId}-ub-r1-1`, 1, 'upper', 'UB Cuartos #1',  alpha,  apex,     2, 0),
    makeMatch(`${faseId}-ub-r1-2`, 1, 'upper', 'UB Cuartos #2',  nova,   phoenix,  2, 1),
    makeMatch(`${faseId}-ub-r1-3`, 1, 'upper', 'UB Cuartos #3',  cyber,  shadow,   2, 1),
    makeMatch(`${faseId}-ub-r1-4`, 1, 'upper', 'UB Cuartos #4',  viper,  immortal, 2, 0),

    // R2: Semifinales (4 → 2 ganadores UB, 2 perdedores → LB R2)
    makeMatch(`${faseId}-ub-r2-1`, 2, 'upper', 'UB Semis #1', alpha, nova,  2, 1),
    makeMatch(`${faseId}-ub-r2-2`, 2, 'upper', 'UB Semis #2', cyber, viper, 2, 1),

    // R3: Final Upper Bracket (2 → 1 UB Campeón, 1 perdedor → LB Final)
    makeMatch(`${faseId}-ub-r3-1`, 3, 'upper', 'UB Final', alpha, cyber, 2, 1),

    // ── LOWER BRACKET ──────────────────────────────────────
    // LB R1: 4 perdedores de UB QF → 2 ganadores (apex, phoenix, shadow, immortal pierden UB)
    makeMatch(`${faseId}-lb-r1-1`, 1, 'lower', 'LB R1 #1', apex,   phoenix,  2, 0),
    makeMatch(`${faseId}-lb-r1-2`, 1, 'lower', 'LB R1 #2', shadow, immortal, 2, 1),

    // LB R2: 2 perdedores UB Semis (nova, viper) vs 2 ganadores LB R1 (apex, shadow)
    makeMatch(`${faseId}-lb-r2-1`, 2, 'lower', 'LB R2 #1', nova,  apex,   2, 1),
    makeMatch(`${faseId}-lb-r2-2`, 2, 'lower', 'LB R2 #2', viper, shadow, 2, 0),

    // LB Semis: 2 ganadores LB R2 (nova, viper)
    makeMatch(`${faseId}-lb-r3-1`, 3, 'lower', 'LB Semis', nova, viper, 2, 1),

    // LB Final: perdedor UB Final (cyber) vs ganador LB Semis (nova)
    makeMatch(`${faseId}-lb-r4-1`, 4, 'lower', 'LB Final', cyber, nova, 2, 1),

    // ── GRAN FINAL (UB Alpha vs LB Cyber) ──────────────────
    makeMatch(`${faseId}-gf-1`, 5, 'grand_final', 'Gran Final BO5 — Alpha Esports vs Cyber Titans', alpha, cyber, 3, 1, 5),
  ];

  return {
    id: faseId,
    edicionId,
    orden: 3,
    nombre: nombreFase,
    modeloCompetencia: 'enfrentamiento_directo',
    formato: 'eliminacion_doble',
    estado: 'finalizada',
    cuposAvance: 1,
    partidas
  };
}



// Devuelve la siguiente potencia de 2 mayor o igual a n
export function nextPowerOf2(n: number): number {
  if (n <= 1) return 1;
  let p = 1;
  while (p < n) p *= 2;
  return p;
}

// Genera el bracket en blanco con soporte de BYEs.
// equiposInscritos: cuántos equipos hay realmente.
// maxSlots: potencia de 2 del bracket (puede ser mayor que equiposInscritos).
// Si equiposInscritos < maxSlots → se generan BYEs para los primeros (maxSlots - equiposInscritos) matches.
// Los seeds TOP reciben BYE y avanzan directamente a Ronda 2.
export function generarBracketEnBlanco(
  faseId: string,
  edicionId: string,
  equiposInscritos: number,
  nombreFase: string,
  maxSlotsForzado?: number
): Fase {
  const safeEquipos = Math.max(2, equiposInscritos || 8);
  const maxSlots = maxSlotsForzado ?? nextPowerOf2(safeEquipos);
  const totalRondas = Math.log2(maxSlots);
  const numByes = maxSlots - safeEquipos; // cuántos BYEs necesitamos
  const partidas: Partida[] = [];

  // En Ronda 1: maxSlots/2 partidas.
  // Las primeras numByes partidas son BYEs (slot A = seed top, slot B = BYE).
  // Las restantes son enfrentamientos normales (Por Definir vs Por Definir).
  const r1Count = maxSlots / 2;

  for (let r = 1; r <= totalRondas; r++) {
    const numPartidas = Math.max(1, maxSlots / Math.pow(2, r));
    const esUltima = r === totalRondas;
    const esSemi = r === totalRondas - 1;

    for (let m = 0; m < numPartidas; m++) {
      const labelMatch = esUltima ? 'Gran Final' : esSemi ? `Semifinal #${m + 1}` : `Match R${r} #${m + 1}`;
      const isByeMatch = r === 1 && m < numByes; // Las primeras partidas de Ronda 1 son BYEs

      const eqA_label = isByeMatch ? `Seed #${m + 1}` : 'Por Definir';

      partidas.push({
        id: `part-blank-${edicionId}-r${r}-${m + 1}`,
        faseId,
        numeroRonda: r,
        nombreGrupo: isByeMatch ? `Ronda 1 — BYE (Seed #${m + 1} Pase Directo)` : labelMatch,
        estado: isByeMatch ? ('bye' as any) : 'programada',
        formatoBo: esUltima ? 5 : 3,
        isBye: isByeMatch,
        participaciones: [
          {
            id: `p-blank-${edicionId}-r${r}-${m + 1}-a`,
            partidaId: `part-blank-${edicionId}-r${r}-${m + 1}`,
            equipoId: null,
            equipo: isByeMatch ? { id: `bye-seed-${m + 1}`, nombre: eqA_label, tag: `S${m + 1}`, estaActivo: true } : undefined,
            mapasGanados: isByeMatch ? 1 : 0,
            esGanador: isByeMatch ? true : false,
            puntos: 0,
            esByeSeed: isByeMatch
          },
          {
            id: `p-blank-${edicionId}-r${r}-${m + 1}-b`,
            partidaId: `part-blank-${edicionId}-r${r}-${m + 1}`,
            equipoId: null,
            equipo: isByeMatch ? { id: `bye-slot-${m + 1}`, nombre: 'BYE', tag: 'BYE', estaActivo: false } : undefined,
            mapasGanados: 0,
            esGanador: false,
            puntos: 0,
            esBye: isByeMatch
          }
        ]
      });
    }
  }

  return {
    id: faseId,
    edicionId,
    orden: 1,
    nombre: nombreFase || 'Cuadro de Brackets (Por Jugar)',
    modeloCompetencia: 'enfrentamiento_directo',
    formato: 'eliminacion_simple',
    estado: 'inscripciones_abiertas',
    cuposAvance: 1,
    numByes,
    maxSlots,
    equiposInscritos: safeEquipos,
    partidas
  };
}


export const MOCK_FASES_32: Fase[] = [
  generarBracketCompleto('fase-32', 'ed-32', 32, '1 - Bracket (Finalizado) / 32 Slots')
];

export const MOCK_FASES_64: Fase[] = [
  generarBracketCompleto('fase-64', 'ed-64', 64, '1 - Bracket (Finalizado) / 64 Slots')
];

export const MOCK_FASES_64_TRIPLE: Fase[] = [
  {
    id: 'fase-64-t1',
    edicionId: 'ed-64-triple',
    orden: 1,
    nombre: 'Fase 1: 16 Grupos de 4 (Round Robin / 64 Equipos)',
    modeloCompetencia: 'grupos',
    formato: 'round_robin',
    estado: 'finalizada',
    cuposAvance: 16,
    numGrupos: 16,
    equiposPorGrupo: 4,
    clasificadosPorGrupo: 1,
    partidas: []
  },
  generarOctavos16a8('fase-64-t2', 'ed-64-triple', 'Fase 2: Octavos de Final BO3 (16 → 8 Clasificados)'),
  generarDobleEliminacion('fase-64-t3', 'ed-64-triple', 'Fase 3: Gran Final Doble Eliminación (Top 8)')
];

export const MOCK_FASES_POR_EDICION: Record<string, Fase[]> = {
  'ed-1': MOCK_FASES_MLBB,
  'ed-32': MOCK_FASES_32,
  'ed-64': MOCK_FASES_64,
  'ed-64-triple': MOCK_FASES_64_TRIPLE,
  'ed-2': [
    {
      id: 'fase-3',
      edicionId: 'ed-2',
      orden: 1,
      nombre: 'Jornada 1 - League Acumulativa',
      modeloCompetencia: 'multi_equipo',
      formato: 'round_robin',
      estado: 'en_curso',
      cuposAvance: 8,
      partidas: []
    }
  ],
  // ── Demo BYEs: 13 equipos en bracket de 16 (3 BYEs automáticos) ──
  'ed-bye-demo': [
    generarBracketEnBlanco('fase-bye-demo', 'ed-bye-demo', 13, 'Bracket BO3 (13 Equipos / 3 BYEs → 16 Slots)')
  ],
};

// ────────────────────────────────────────────
// DISPUTAS
// ────────────────────────────────────────────
export const MOCK_DISPUTAS = [
  {
    id: 'disp-1',
    partidaId: 'part-7',
    edicionId: 'ed-1',
    abiertaPor: 'eq-5',
    equipoA: MOCK_EQUIPOS[4],
    equipoB: MOCK_EQUIPOS[5],
    motivo: 'El equipo rival afirma haber ganado 2-1 pero nuestra captura muestra 2-0 a nuestro favor. Adjuntamos screenshot del marcador final.',
    evidenciaUrlA: 'https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?q=80&w=800',
    evidenciaUrlB: 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?q=80&w=800',
    estado: 'abierta',
    createdAt: '2026-08-20T21:00:00Z',
  },
  {
    id: 'disp-2',
    partidaId: 'part-2',
    edicionId: 'ed-1',
    abiertaPor: 'eq-4',
    equipoA: MOCK_EQUIPOS[2],
    equipoB: MOCK_EQUIPOS[3],
    motivo: 'El equipo Alpha reportó score incorrecto. Adjuntamos video completo de la partida donde se ve el marcador real.',
    evidenciaUrlA: 'https://images.unsplash.com/photo-1593642634443-44adaa06623a?q=80&w=800',
    evidenciaUrlB: null,
    estado: 'en_revision',
    createdAt: '2026-08-15T22:30:00Z',
  },
];

// ────────────────────────────────────────────
// TABLA DE POSICIONES MLBB (Fase Grupos)
// ────────────────────────────────────────────
export const MOCK_STANDINGS_MLBB = [
  { rank: 1, equipoId: 'eq-1', equipo: MOCK_EQUIPOS[0], pj: 3, pg: 3, pp: 0, pts: 9, difMaps: '+3', seed: 1 },
  { rank: 2, equipoId: 'eq-3', equipo: MOCK_EQUIPOS[2], pj: 3, pg: 2, pp: 1, pts: 6, difMaps: '+1', seed: 2 },
  { rank: 3, equipoId: 'eq-2', equipo: MOCK_EQUIPOS[1], pj: 3, pg: 1, pp: 2, pts: 3, difMaps: '-1', seed: 3 },
  { rank: 4, equipoId: 'eq-4', equipo: MOCK_EQUIPOS[3], pj: 3, pg: 0, pp: 3, pts: 0, difMaps: '-3', seed: 4 },
];

// ────────────────────────────────────────────
// FREE FIRE STANDINGS
// ────────────────────────────────────────────
export const MOCK_FREE_FIRE_STANDINGS = [
  { rank: 1, equipo: MOCK_EQUIPOS[0], caidas: [{ pos: 1, kills: 14, pts: 26 }, { pos: 2, kills: 8, pts: 17 }, { pos: 1, kills: 11, pts: 23 }], totalPts: 66, totalKills: 33, booyahs: 2 },
  { rank: 2, equipo: MOCK_EQUIPOS[2], caidas: [{ pos: 3, kills: 10, pts: 18 }, { pos: 1, kills: 12, pts: 24 }, { pos: 3, kills: 7, pts: 15 }], totalPts: 57, totalKills: 29, booyahs: 1 },
  { rank: 3, equipo: MOCK_EQUIPOS[1], caidas: [{ pos: 2, kills: 7, pts: 16 }, { pos: 4, kills: 6, pts: 13 }, { pos: 2, kills: 9, pts: 18 }], totalPts: 47, totalKills: 22, booyahs: 0 },
  { rank: 4, equipo: MOCK_EQUIPOS[3], caidas: [{ pos: 5, kills: 5, pts: 11 }, { pos: 3, kills: 8, pts: 16 }, { pos: 4, kills: 6, pts: 13 }], totalPts: 40, totalKills: 19, booyahs: 0 },
  { rank: 5, equipo: MOCK_EQUIPOS[4], caidas: [{ pos: 4, kills: 4, pts: 11 }, { pos: 6, kills: 5, pts: 10 }, { pos: 5, kills: 4, pts: 10 }], totalPts: 31, totalKills: 13, booyahs: 0 },
  { rank: 6, equipo: MOCK_EQUIPOS[5], caidas: [{ pos: 6, kills: 3, pts: 8 }, { pos: 5, kills: 3, pts: 9 }, { pos: 6, kills: 2, pts: 7 }], totalPts: 24, totalKills: 8, booyahs: 0 },
];

// ────────────────────────────────────────────
// USUARIOS DEMO (ROLES DIFERENCIADOS)
// ────────────────────────────────────────────
export const MOCK_ADMIN: Usuario = {
  id: 'usr-admin',
  nombre: 'Staff Organizador',
  email: 'admin@arenaesports.gg',
  avatarUrl: 'https://images.unsplash.com/photo-1566492031773-4f4e44671857?q=80&w=150&auto=format&fit=crop',
  discordId: '111122223333444455',
  rol: 'organizador'
};

export const MOCK_CAPITAN: Usuario = {
  id: 'usr-capitan',
  nombre: 'Viper (Capitán Alpha)',
  email: 'capitan@alphaesports.gg',
  avatarUrl: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?q=80&w=150&auto=format&fit=crop',
  discordId: '222233334444555566',
  rol: 'capitan'
};

export const MOCK_JUGADOR: Usuario = {
  id: 'usr-jugador',
  nombre: 'GamerPro_99',
  email: 'jugador@gmail.com',
  avatarUrl: 'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?q=80&w=150&auto=format&fit=crop',
  discordId: '333344445555666677',
  rol: 'jugador'
};

export const MOCK_USUARIOS_DEMO = [
  { ...MOCK_ADMIN, password: 'admin', desc: 'Panel Admin completo, sin equipo en torneo' },
  { ...MOCK_CAPITAN, password: 'capitan', desc: 'Capitán de Alpha Esports con squad activo' },
  { ...MOCK_JUGADOR, password: 'jugador', desc: 'Usuario libre para crear equipo desde cero' },
];

export const MOCK_USUARIO_ACTUAL: Usuario = MOCK_ADMIN;

