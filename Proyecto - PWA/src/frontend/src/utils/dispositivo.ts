// Detección de "celular" para funciones que sólo tienen sentido con el teléfono
// en la mano —o parado apuntando—, como contar repeticiones con la cámara.
//
// No alcanza UNA sola señal: el user-agent miente, y una pantalla chica puede
// ser una ventana angosta en una compu. Se combinan tres, y todas tienen que
// dar: hay cámara, el puntero es "grueso" (dedo, no mouse) y la pantalla es
// angosta. En una laptop no aparece la función, que es justo lo que se quiere.

export function soportaCamara(): boolean {
  return typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;
}

export function esCelular(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  const punteroGrueso = window.matchMedia('(pointer: coarse)').matches;
  const pantallaAngosta = window.matchMedia('(max-width: 820px)').matches;
  return soportaCamara() && punteroGrueso && pantallaAngosta;
}
