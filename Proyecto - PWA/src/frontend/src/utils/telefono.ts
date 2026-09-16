// Teléfonos con código de país. Gemelo de app/telefono.py (Flet).
//
// Decisión del dueño (2026-09-16): con socios o empleados extranjeros, un
// número sin país "se traspapela" — el mismo 3415551234 puede ser de dos países
// y el botón de WhatsApp lo mandaría a cualquier lado. Todo campo de teléfono
// tiene un selector de país (Argentina por defecto) y se guarda el número
// COMPLETO: "+54 3415551234".
//
// No hizo falta tocar la base ni migrar nada: los números viejos no traen "+",
// y se leen como argentinos, que es lo que eran. El backend ya aceptaba el "+"
// y los espacios (_telefono_valido en schemas.py).

export interface Pais {
  nombre: string;
  /** Con el "+": "+54". */
  prefijo: string;
  bandera: string;
}

// Argentina primero (es el default) y después los que más probablemente
// aparezcan en un gimnasio argentino: la región, y los de afuera más comunes.
export const PAISES: Pais[] = [
  { nombre: 'Argentina', prefijo: '+54', bandera: '🇦🇷' },
  { nombre: 'Uruguay', prefijo: '+598', bandera: '🇺🇾' },
  { nombre: 'Chile', prefijo: '+56', bandera: '🇨🇱' },
  { nombre: 'Paraguay', prefijo: '+595', bandera: '🇵🇾' },
  { nombre: 'Bolivia', prefijo: '+591', bandera: '🇧🇴' },
  { nombre: 'Brasil', prefijo: '+55', bandera: '🇧🇷' },
  { nombre: 'Perú', prefijo: '+51', bandera: '🇵🇪' },
  { nombre: 'Colombia', prefijo: '+57', bandera: '🇨🇴' },
  { nombre: 'Venezuela', prefijo: '+58', bandera: '🇻🇪' },
  { nombre: 'Ecuador', prefijo: '+593', bandera: '🇪🇨' },
  { nombre: 'México', prefijo: '+52', bandera: '🇲🇽' },
  { nombre: 'Estados Unidos', prefijo: '+1', bandera: '🇺🇸' },
  { nombre: 'España', prefijo: '+34', bandera: '🇪🇸' },
  { nombre: 'Italia', prefijo: '+39', bandera: '🇮🇹' },
];

export const PREFIJO_DEFAULT = '+54';

/** Lo que se acepta tipear en la parte local del número (sin letras). */
export function limpiarNumeroLocal(valor: string): string {
  return valor.replace(/[^()\-\s0-9]/g, '');
}

/**
 * "+54 3415551234" -> { prefijo: "+54", numero: "3415551234" }.
 * Un número sin "+" es de los cargados antes del selector: argentino.
 * Si el prefijo no está en la lista, se elige el más largo que coincida para
 * no partir mal un "+598" como "+59" + "8…".
 */
export function separarTelefono(valor: string | undefined): { prefijo: string; numero: string } {
  const limpio = (valor ?? '').trim();
  if (!limpio.startsWith('+')) return { prefijo: PREFIJO_DEFAULT, numero: limpio };

  const digitos = limpio.slice(1).replace(/\D/g, '');
  const candidato = [...PAISES]
    .sort((a, b) => b.prefijo.length - a.prefijo.length)
    .find((p) => digitos.startsWith(p.prefijo.slice(1)));
  if (!candidato) return { prefijo: PREFIJO_DEFAULT, numero: limpio };

  // Se saca el prefijo de la cadena original (con sus espacios) y no de los
  // dígitos, para conservar cómo lo escribió la persona.
  let resto = limpio.slice(1).trimStart();
  let quedan = candidato.prefijo.length - 1;
  while (quedan > 0 && resto.length > 0) {
    if (/\d/.test(resto[0])) quedan -= 1;
    resto = resto.slice(1);
  }
  return { prefijo: candidato.prefijo, numero: resto.trim() };
}

/** Une país y número. Sin número, vacío: el país solo no es un teléfono. */
export function unirTelefono(prefijo: string, numero: string): string {
  const n = numero.trim();
  return n ? `${prefijo} ${n}` : '';
}
