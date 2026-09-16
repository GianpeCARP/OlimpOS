// Cómo se le escribe a una persona desde el sistema: un mailto: o un wa.me.
//
// Vive en un archivo propio porque son dos pantallas con la misma regla —el
// botón "Contactar" de la ficha de personal y el envío de credenciales del
// alta— y si cada una armara el link por su cuenta terminarían mandando el
// mismo mensaje a números formateados distinto.
//
// Gemelo de `app/contacto.py` en la app Flet: si cambia una regla acá, mirá
// la otra.

/**
 * Prefijo internacional que se asume cuando el teléfono viene sin uno.
 *
 * El gimnasio está en Argentina y nadie carga "+54" a mano: en la base los
 * números están como "3415551234". wa.me EXIGE el formato internacional
 * completo y sin símbolos, así que hay que completarlo.
 *
 * El 9 del medio (54 **9** 341 …) es el que Argentina pide para celulares, y
 * es el caso de todos los WhatsApp: una línea fija no tiene cuenta.
 */
const PREFIJO_INTERNACIONAL = '549';

/** Deja sólo los dígitos: wa.me rechaza espacios, guiones y paréntesis. */
export function soloDigitos(telefono: string): string {
  return telefono.replace(/\D/g, '');
}

/**
 * Link de WhatsApp con el mensaje ya escrito.
 *
 * LIMITACIÓN CONOCIDA: un número cargado en notación local con el 15
 * ("0341 15 555 1234") no se puede convertir de forma confiable, porque el 15
 * hay que sacarlo y el 9 ponerlo, y sin saber cuántos dígitos tiene la
 * característica no se distingue el 15 del principio del abonado. Se saca el
 * 0 inicial, que sí es inequívoco. Para el resto, el número va cargado en
 * formato internacional o directo sin el 15.
 */
export function linkWhatsapp(telefono: string, mensaje?: string): string {
  let numero = soloDigitos(telefono);
  if (numero.startsWith('0')) numero = numero.slice(1);
  if (!numero.startsWith('54')) numero = PREFIJO_INTERNACIONAL + numero;
  const texto = mensaje ? `?text=${encodeURIComponent(mensaje)}` : '';
  return `https://wa.me/${numero}${texto}`;
}

/**
 * Base del redactor de Gmail en el navegador. `view=cm` es el modo redacción y
 * `fs=1` lo abre en ventana completa en vez del recuadro chico de la esquina.
 */
const GMAIL_REDACTAR = 'https://mail.google.com/mail/?view=cm&fs=1';

/**
 * Link para escribirle un mail a alguien, con asunto y cuerpo ya cargados.
 *
 * Va al REDACTOR DE GMAIL, no a un `mailto:`, y es a propósito. Un `mailto:`
 * necesita que la máquina tenga un programa de correo asociado, y las PC del
 * gimnasio no lo tienen: el botón no hacía absolutamente nada. (Antes, encima,
 * el link iba con target="_blank" y quedaba una pestaña muerta mostrando el
 * "mailto:…", que fue como se descubrió todo esto.)
 *
 * El precio es que ata el botón a Gmail: quien lo use tiene que estar logueado
 * en Google en ese navegador, y con varias cuentas se abre en la que esté
 * activa. Es el canje que se eligió — un botón que anda siempre contra uno que
 * no andaba nunca.
 *
 * Como ahora es una página de verdad, este link SÍ va en pestaña nueva.
 */
export function linkMail(email: string, asunto?: string, cuerpo?: string): string {
  const params = [`to=${encodeURIComponent(email)}`];
  if (asunto) params.push(`su=${encodeURIComponent(asunto)}`);
  if (cuerpo) params.push(`body=${encodeURIComponent(cuerpo)}`);
  return `${GMAIL_REDACTAR}&${params.join('&')}`;
}

/**
 * Lo que se acepta tipear en un campo de teléfono.
 *
 * Espeja `_telefono_valido()` del backend (schemas.py). Filtrar mientras se
 * escribe, en vez de avisar al guardar, es lo que evita el caso que reportó
 * el gimnasio: el campo aceptaba letras y el error recién aparecía al mandar
 * el formulario entero.
 */
export function limpiarTelefono(valor: string): string {
  return valor.replace(/[^+()\-\s0-9]/g, '');
}
