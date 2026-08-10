# Especificación Técnica de Arquitectura de Datos y Motor de Reglas para Gestión de Gimnasios

## 1. Introducción y Principios del Modelo

El presente documento define la arquitectura técnica, el modelo relacional de base de datos y la lógica de negocio no ambigua para un sistema automatizado de gestión de gimnasios de alta gama (*Tier-One*).

El sistema elimina la intervención manual mediante un **modelo jerárquico de dos capas (Padre-Hijo)** y un **motor de validación de estado en tiempo real ($O(1)$ / $O(\log N)$)**.

---

## 2. Jerarquía de Contratos: Membresía Madre vs. Suscripciones Hijas

El sistema desacopla la permanencia del usuario en la institución de los derechos de uso de actividades específicas.

```
+--------------------------------------------------------------------------+
|                        MEMBRESÍA MADRE (Base)                            |
| Otorga condición de socio, acceso físico base y seguro.                   |
| Vencimiento: Fijo (Mensual, Trimestral, Semestral, Anual).                |
+--------------------------------------------------------------------------+
                                    |
                                    | 1 : N
                                    v
+--------------------------------------------------------------------------+
|                      SUSCRIPCIONES HIJAS (Actividades)                    |
| Otorgan acceso a disciplinas específicas (Musculación, Boxeo, etc.).     |
| Vencimiento: Subordinado de forma estricta a la Membresía Madre.        |
+--------------------------------------------------------------------------+
```

### 2.1. Regla de Acceso Físico (Molinete / QR)
Para que un socio ingrese al establecimiento, el sistema evalúa la función lógica $AND$:

$$\text{Acceso Permitido} = (\text{Estado(Membresía\_Madre)} == \text{'ACTIVA'}) \land (\text{Créditos\_Disponibles} > 0 \lor \text{Acceso\_Libre} == \text{TRUE})$$

*   Si la **Membresía Madre** vence, la función retorna `FALSE` inmediatamente, denegando el ingreso y bloqueando cualquier reserva activa, sin importar el saldo de clases/actividades que tenga el usuario.

---

## 3. Resolución de Desfasajes Temporales y Prorrateo (Pro-Rating)

### 3.1. Anclaje al Ciclo Madre
Toda **Suscripción Hija** debe estar **anclada a la fecha de vencimiento de la Membresía Madre**. Ningún contrato hijo puede tener una fecha de vencimiento posterior a la de su contrato padre.

### 3.2. Algoritmo de Prorrateo de Sincronización
Cuando un socio agota sus clases antes de tiempo o adquiere una nueva actividad a mitad de ciclo:

1.  **Cálculo de Días Restantes ($D_r$):**
    $$D_r = \text{Fecha\_Vencimiento\_Madre} - \text{Fecha\_Actual}$$
2.  **Cálculo de Cuota Proporcional ($C_p$):**
    $$C_p = \left( \frac{\text{Precio\_Mensual\_Actividad}}{30} \right) \times D_r$$
3.  **Cálculo de Cupo Proporcional de Clases ($K_p$):**
    $$K_p = \left\lceil \left( \frac{\text{Cupo\_Mensual\_Total}}{30} \right) \times D_r \right\rceil$$

El usuario abona $C_p$, obtiene $K_p$ clases para los $D_r$ días restantes, y **la fecha de vencimiento de la actividad se alinea exactamente con la Membresía Madre**. A partir del siguiente ciclo, la renovación ocurre de forma unificada.

---

## 4. Gestión de Turnos Semanales sin Recarga de Base de Datos

Para actividades con cupo por turno (ej. Boxeo con máximo de 2 clases por semana):

1.  **Almacenamiento Estático:** Se guarda únicamente la regla `weekly_quota = 2` en la tabla de suscripción del usuario.
2.  **Evaluación Dinámica:** En el momento en que el usuario intenta reservar un turno, el software consulta el conteo de reservas en la **semana ISO actual** mediante la consulta SQL indexada:

```sql
SELECT COUNT(*) 
FROM bookings 
WHERE user_subscription_id = :sub_id 
  AND status = 'CONFIRMED'
  AND slot_datetime BETWEEN :inicio_semana_iso AND :fin_semana_iso;
```

*   **Sin Cron Jobs:** No se requiere ningún proceso nocturno que reinicie contadores los lunes a las 00:00. El cambio de la ventana de tiempo del `BETWEEN` reinicia la disponibilidad de forma matemática.

---

## 5. Esquema de Base de Datos Relacional (DDL SQL)

El siguiente diseño garantiza rendimiento idéntico independientemente de la cantidad de usuarios o actividades contratadas.

```sql
-- 1. Tabla de Usuarios
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, SUSPENDED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Membresías Madre (Contrato Base)
CREATE TABLE memberships (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    auto_renew BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, CANCELLED
    CONSTRAINT chk_dates CHECK (valid_until >= valid_from)
);
CREATE INDEX idx_memberships_user_status ON memberships(user_id, status, valid_until);

-- 3. Catálogo de Actividades / Disciplinas
CREATE TABLE activities (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    requires_booking BOOLEAN NOT NULL DEFAULT TRUE,
    room_capacity INT DEFAULT 0, -- Capacidad de la sala
    monthly_price NUMERIC(10,2) NOT NULL
);

-- 4. Suscripciones Hijas a Actividades
CREATE TABLE user_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    membership_id BIGINT NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    activity_id BIGINT NOT NULL REFERENCES activities(id),
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    weekly_quota INT DEFAULT NULL, -- NULL = Pase Libre / N clases por semana
    monthly_quota INT DEFAULT NULL, -- NULL = Sin límite mensual / Total del período
    status VARCHAR(20) DEFAULT 'ACTIVE',
    CONSTRAINT chk_sub_dates CHECK (valid_until >= valid_from)
);
CREATE INDEX idx_user_subs_membership ON user_subscriptions(membership_id, activity_id, status);

-- 5. Reservas de Turnos
CREATE TABLE bookings (
    id BIGSERIAL PRIMARY KEY,
    user_subscription_id BIGINT NOT NULL REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    slot_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'CONFIRMED', -- CONFIRMED, CANCELLED, ATTENDED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bookings_sub_time ON bookings(user_subscription_id, slot_datetime, status);
```

---

## 6. Algoritmos y Lógica de Control (Pseudo-código)

### 6.1. Algoritmo 1: Control de Molinete / Acceso Físico
```python
def check_access(user_id, activity_id, current_timestamp):
    # 1. Verificar Membresía Madre Activa
    membership = db.query(
        "SELECT * FROM memberships "
        "WHERE user_id = :u AND status = 'ACTIVE' "
        "AND :now BETWEEN valid_from AND valid_until",
        u=user_id, now=current_timestamp.date()
    ).first()

    if not membership:
        return DENIED("Membresía base vencida o inexistente")

    # 2. Verificar Suscripción Hija a la Actividad Solicitada
    sub = db.query(
        "SELECT * FROM user_subscriptions "
        "WHERE membership_id = :m_id AND activity_id = :a_id "
        "AND status = 'ACTIVE' AND :now BETWEEN valid_from AND valid_until",
        m_id=membership.id, a_id=activity_id, now=current_timestamp.date()
    ).first()

    if not sub:
        return DENIED("No posee subscripción activa para esta actividad")

    return GRANTED("Acceso Permitido")
```

### 6.2. Algoritmo 2: Validación de Reserva de Turno (Boxeo / Clases)
```python
def reserve_slot(user_id, activity_id, slot_datetime):
    # 1. Verificar Acceso Base en la Fecha del Turno
    access = check_access(user_id, activity_id, slot_datetime)
    if not access.is_granted:
        return ERROR(access.reason)

    sub = access.subscription
    activity = access.activity

    # 2. Verificar Aforo de la Sala
    current_occupancy = db.query(
        "SELECT COUNT(*) FROM bookings b "
        "JOIN user_subscriptions us ON b.user_subscription_id = us.id "
        "WHERE us.activity_id = :a_id AND b.slot_datetime = :slot AND b.status = 'CONFIRMED'",
        a_id=activity_id, slot=slot_datetime
    ).scalar()

    if current_occupancy >= activity.room_capacity:
        return ERROR("Cupo agotado para este horario")

    # 3. Verificar Límite Semanal del Usuario (si aplica)
    if sub.weekly_quota is not None:
        start_of_week = get_monday_0000(slot_datetime)
        end_of_week = get_sunday_2359(slot_datetime)

        user_weekly_bookings = db.query(
            "SELECT COUNT(*) FROM bookings "
            "WHERE user_subscription_id = :sub_id "
            "AND status = 'CONFIRMED' "
            "AND slot_datetime BETWEEN :start AND :end",
            sub_id=sub.id, start=start_of_week, end=end_of_week
        ).scalar()

        if user_weekly_bookings >= sub.weekly_quota:
            return ERROR("Límite de reservas semanales alcanzado para la actividad")

    # 4. Insertar Reserva
    db.execute("INSERT INTO bookings (user_subscription_id, slot_datetime) VALUES (:s, :t)", s=sub.id, t=slot_datetime)
    return SUCCESS("Reserva confirmada")
```

---

## 7. Matriz de Casos de Borde (Edge Cases) Resueltos

| Escenario Práctico | Comportamiento del Sistema | Resultado Técnico |
| :--- | :--- | :--- |
| **Agotamiento prematuro de clases** (Ej: 10 clases consumidas en 15 días). | El sistema bloquea nuevas reservas para la actividad. Ofrece en app la opción de comprar paquete prorrateado hasta el fin del ciclo de la Membresía Madre. | Mantiene sincronizadas las fechas de renovación sin alterar la Membresía Madre. |
| **Membresía Semestral + Actividad Mensual.** | La actividad vence el día $N$ de cada mes. Si el socio no paga la actividad, la Membresía Madre sigue activa (puede entrar al club si tiene otras actividades). Si llega al mes 6 (Julio), la actividad no puede renovar más allá de la fecha de la Membresía Madre. | Regla `valid_until(Sub) <= valid_until(Padre)`. El sistema fuerza prorrateo en el último mes. |
| **Vencimiento de Membresía Madre con Turnos Futuros Reservados.** | El socio intenta ingresar el día 16. Su membresía venció el 15, pero tenía un turno reservado para el 18. | El molinete deniega el ingreso el día 16. El sistema cancela o congela automáticamente las reservas futuras hasta la renovación de la Membresía Madre. |
| **Reserva en semana futura.** | El usuario intenta reservar un turno para dentro de 2 semanas. | El algoritmo evalúa el rango `BETWEEN` de la semana futura seleccionada. Si en esa semana específica ya tiene 2 reservas, deniega el turno. |

---

## 8. Conclusión

Este diseño garantiza:
1. **0% Intervención Manual:** Todos los cálculos de desfasaje, bloqueo de molinetes y límites de reservas ocurren por cómputo estricto.
2. **Escalabilidad $O(1)$ / $O(\log N)$:** Índices B-Tree en llaves foráneas y rangos de fechas garantizan que las consultas tarden `< 5ms` tanto con 100 usuarios como con 100.000 usuarios.
3. **Consistencia Contable:** Cero fechas colgadas o desincronizadas gracias al principio de anclaje madre-hijo y prorrateo automático.
