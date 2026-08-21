'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Trophy, Download, Shield, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { ApiEdicion, ApiFase, ApiTablaGrupo, ApiTorneo } from '@/lib/api-types';
import GroupStageView from '@/components/torneos/GroupStageView';

export default function FaseTablaAdminPage() {
  const params = useParams();
  const torneoId = params.id as string;
  const edId = params.edId as string;
  const faseId = params.faseId as string;

  const [torneo, setTorneo] = useState<ApiTorneo | null>(null);
  const [edicion, setEdicion] = useState<ApiEdicion | null>(null);
  const [fase, setFase] = useState<ApiFase | null>(null);
  const [tabla, setTabla] = useState<ApiTablaGrupo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let activo = true;
    Promise.all([
      api.getTorneoById(torneoId),
      api.getEdicionById(edId),
      api.getFasesByEdicion(edId),
      api.getTablaFase(edId, faseId),
    ]).then(([t, ed, fs, tb]) => {
      if (!activo) return;
      setTorneo(t);
      setEdicion(ed);
      setFase(fs.find(f => String(f.id) === faseId) || null);
      setTabla(tb);
    }).finally(() => activo && setLoading(false));
    return () => { activo = false; };
  }, [torneoId, edId, faseId]);

  const handleExportCSV = () => {
    const rows = tabla.flatMap(g => g.filas);
    const csvContent = 'data:text/csv;charset=utf-8,'
      + ['Grupo,Rank,Equipo,PJ,PG,PE,PD,DifMapas,Puntos']
        .concat(tabla.flatMap(g => g.filas.map(f =>
          `${g.grupo ?? 'General'},${f.posicion},${f.equipo_nombre},${f.jugados},${f.victorias},${f.empates},${f.derrotas},${f.diferencia_mapas},${f.puntos}`
        )))
        .join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', `standings-${fase?.nombre || 'fase'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto flex items-center justify-center gap-2 text-white/40 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando tabla...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-2 text-xs text-white/30">
        <Link href="/admin/torneos" className="hover:text-white transition-colors">Torneos</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}`} className="hover:text-white transition-colors">{torneo?.nombre}</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases`} className="hover:text-white transition-colors">Fases</Link>
        <span>/</span>
        <span className="text-white/60">Tabla de Posiciones</span>
      </div>

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-xs text-white/40">{edicion?.nombre}</span>
          <h1 className="text-2xl font-black text-white flex items-center gap-2.5">
            <Trophy className="text-amber-400" /> Tabla de Posiciones ({fase?.nombre})
          </h1>
        </div>
        <button
          onClick={handleExportCSV}
          disabled={tabla.length === 0}
          className="flex items-center gap-2 px-3.5 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-semibold rounded-xl transition-all disabled:opacity-40 w-fit"
        >
          <Download size={14} /> Exportar CSV
        </button>
      </div>

      <div className="flex items-center gap-2 text-xs font-semibold text-white/50">
        <Shield size={14} className="text-cyan-400" />
        Criterios: Puntos → Diferencia de Mapas
      </div>

      <GroupStageView grupos={tabla} clasificadosPorGrupo={fase?.config?.clasificados_por_grupo || fase?.config?.cupos_avance || 1} />
    </div>
  );
}
