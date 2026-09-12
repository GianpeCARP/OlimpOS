// Helpers de validación compartidos por los services. Viven acá y no
// duplicados en cada uno porque authService y sociosService validan las
// mismas cosas (DNI, email) sobre la misma tabla Persona.

/** Recorta espacios y normaliza `undefined` a ''. */
export function limpiar(valor: string | undefined): string {
  return (valor ?? '').trim();
}

// Chequeo de forma, no de existencia: algo@algo.algo sin espacios. No se usa
// una regex "completa" de RFC 5322 porque es ilegible y no aporta — el email
// real se valida mandando un mail, cosa que hará el backend.
export const FORMATO_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function esEmailValido(email: string): boolean {
  return FORMATO_EMAIL.test(email);
}
