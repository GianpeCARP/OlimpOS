No elijas ninguna de las 3 opciones tal cual. Tengo el esquema real
(v4, ya en producción en Postgres) con los tipos exactos de las 7 tablas
que auth.spec.md usa. Armá types.ts con ESTO, no con lo que interpretes
del spec en prosa:

interface Persona {
  id_persona: number;
  dni: string;                    // varchar(20), unique, not null
  apellido: string;                // varchar(100), not null
  nombre: string;                  // varchar(100), not null
  sexo?: string;                   // varchar(20)
  email?: string;                  // varchar(150), unique
  calle?: string;
  numero_calle?: string;
  localidad?: string;
  fecha_nacimiento?: string;       // date
  url_foto?: string;
  emergencia_nombre?: string;
  emergencia_telefono?: string;
  emergencia_parentesco?: string;
  fecha_alta: string;              // timestamp, default now()
  activo: boolean;                 // default true
}

interface Usuario {
  id_usuario: number;
  id_persona: number;              // FK -> Persona, unique, not null
  username: string;                // varchar(50), unique, not null
  password_hash: string;           // NUNCA exponer esto al frontend
  ultimo_acceso?: string;          // timestamp
  intentos_fallidos: number;       // default 0
  bloqueado: boolean;              // default false
  activo: boolean;                 // default true
}

interface Telefono {
  id_telefono: number;
  id_persona: number;              // FK -> Persona
  numero: string;                  // varchar(30), not null
  tipo: 'CELULAR' | 'FIJO';        // default CELULAR
  principal: boolean;              // default false
}

interface Socio {
  id_socio: number;
  id_persona: number;              // FK -> Persona, unique, not null
  id_sede: number;                 // FK -> Sede, not null
  id_entrenador_a_cargo?: number;  // FK -> Entrenador, opcional
  numero_socio?: string;           // varchar(20), unique
  fecha_alta: string;              // date, not null
  objetivo?: string;
  observaciones?: string;
  activo: boolean;                 // default true
}

interface Baja {
  id_baja: number;
  id_socio: number;                // FK -> Socio, not null
  fecha_baja: string;              // date, not null
  tipo?: 'VOLUNTARIA' | 'MORA' | 'ADMINISTRATIVA';
  motivo?: string;
  id_registrado_por?: number;      // FK -> Usuario
}

interface Auditoria {
  id_auditoria: number;
  id_usuario?: number;             // FK -> Usuario
  entidad: string;                 // varchar(50), not null
  id_entidad?: number;
  accion: 'ALTA' | 'MODIFICACION' | 'BAJA' | 'CONSULTA' | 'LOGIN';
  fecha: string;                   // timestamp, default now()
  detalle?: string;
  ip?: string;
}

interface Sede {
  id_sede: number;
  id_dueno: number;                // FK -> Dueno, not null
  nombre: string;                  // varchar(100), not null
  calle?: string;
  numero_calle?: string;
  localidad?: string;
  telefono?: string;
  capacidad_maxima?: number;
  hora_apertura?: string;          // time
  hora_cierre?: string;            // time
  abierto_24hs: boolean;           // default true
  activo: boolean;                 // default true
}

Notas al armar el archivo:
- Los campos marcados opcionales arriba (con "?") son NULLABLE en la base
  real — no los pongas como required en TypeScript.
- Usuario.password_hash: declaralo en el tipo por completitud, pero nunca
  debería viajar en una respuesta del backend al frontend. Marcalo con un
  comentario de advertencia en el código.
- Estos 7 tipos son los que auth.spec.md necesita HOY. El resto de las 33
  tablas del sistema se van a ir agregando a este mismo archivo a medida
  que implementemos cada spec siguiente (perfil-socio, cuotas, etc.) — no
  hace falta declarar las 33 ahora.
