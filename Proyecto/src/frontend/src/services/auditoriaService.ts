// Registro de auditoría, compartido por todos los services que hacen
// ALTA/MODIFICACION/BAJA sobre alguna entidad (auth.spec.md y, ahora,
// sociosService). Vivía como función privada dentro de authService — se
// separó apenas un segundo service necesitó lo mismo, para no duplicar la
// lógica de "cómo se arma una fila de Auditoria".

import type { Auditoria } from '../types';
import { aTimestampISO } from '../utils/fechas';
import { auditoria, siguienteId } from './mockDb';

/**
 * Arma y guarda una fila de Auditoría. id_auditoria y fecha se completan
 * solos, el resto lo decide quien llama. id_usuario queda undefined cuando
 * no hay nadie logueado todavía (caso ALTA de auth.spec.md 3.1: el usuario
 * se está creando en esa misma llamada, no existe sesión previa).
 */
export function registrarAuditoria(entrada: Omit<Auditoria, 'id_auditoria' | 'fecha'>): void {
  auditoria.push({
    id_auditoria: siguienteId.auditoria(),
    fecha: aTimestampISO(new Date()),
    ...entrada,
  });
}
