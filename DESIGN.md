---
name: OlimpOS Kinetic Carbon
version: 2.0
colors:
  # Superficies y Fondos (Dark Mode)
  surface-base: '#15171C'      # Fondo general de la app
  surface-card: '#1C1F26'      # Fondo de paneles y tarjetas
  surface-hover: '#242832'     # Estados activos y barras de navegación
  
  # Acentos de Energía (Neón)
  primary-volt: '#C6F135'      # Verde Lima (Acciones principales, movimiento, progreso)
  primary-dim: '#9BBE22'       # Verde Lima oscurecido para gradientes
  accent-coral: '#FF6B3D'      # Coral (Alertas, badges, acentos secundarios)
  accent-dim: '#D2542C'        # Coral oscurecido para gradientes
  
  # Bordes Extravagantes (Chau grises aburridos)
  border-idle: '#2A3324'       # Borde con tinte verdoso muy oscuro (Olive/Volt Tint)
  border-active: '#586A36'     # Borde iluminado para focus y hover
  border-glow: 'rgba(198, 241, 53, 0.25)' # Resplandor neón para destacar tarjetas VIP
  
  # Tipografía
  text-main: '#F2F3F5'         # Blanco roto para lectura cómoda
  text-secondary: '#A4A9B4'    # Gris plata para subtítulos
  text-muted: '#6C7280'        # Gris oscuro para metadatos y placeholders
  
  # Semántica de Estados
  status-ok: '#3DDC97'         # Verde menta (Pagos al día)
  status-warn: '#FFC24B'       # Amarillo (Cuotas por vencer)
  status-danger: '#FF5C5C'     # Rojo (Deudas)
typography:
  font-heading: 'Barlow Semi Condensed, sans-serif'
  font-body: 'Archivo, sans-serif'
rounded:
  sm: '6px'
  md: '10px'
  lg: '14px'       # Radios amplios y modernos para tarjetas
  full: '9999px'
---

## 1. Identidad de Marca y Filosofía Visual
El sistema OlimpOS está diseñado para ser el sistema de información central de la gestión del gimnasio. Su interfaz debe transmitir dos cosas: **precisión administrativa** y **adrenalina deportiva**. 
Abandonamos el aspecto de "software contable tradicional" para adoptar una estética "Kinetic Carbon": fondos inmersivos que simulan fibra de carbono, atravesados por destellos de luz neón (Volt y Coral) que imitan el movimiento, la vitalidad y la estética de la indumentaria deportiva de alto rendimiento.

## 2. Tipografía: El Ritmo Visual
El sistema utiliza una combinación tipográfica dual para maximizar el impacto y la legibilidad:
*   **Barlow Semi Condensed:** Exclusiva para números gigantes (métricas), títulos de paneles y logotipos. Su diseño condensado y alto transmite fuerza y velocidad. Usar en pesos altos (`700`, `800`, `900`).
*   **Archivo:** Exclusiva para lectura, tablas, listas de socios y descripciones. Es geométrica pero amable, ideal para interfaces de datos densos. Usar en pesos regulares a semibold (`400`, `500`, `600`).

## 3. Arquitectura de Color y "Bordes Vivos"
**PROHIBIDO usar bordes grises planos (`#333`, `#444`).**
Para que la interfaz se perciba como "Premium" y extravagante, el sistema de separación de componentes utiliza **Bordes Vivos**. 
*   Las tarjetas y paneles están delineados por `border-idle` (`#2A3324`), un color que parece gris a simple vista, pero que en realidad es un verde oliva extremadamente oscuro que armoniza con el color Lima principal.
*   Cuando un componente requiere atención (ej: un widget de ingresos), el borde proyecta una sombra de caja (box-shadow) sutil usando la variable `border-glow`, creando un efecto de luz LED derramada sobre el escritorio oscuro.

## 4. Componentes y Geometría
El diseño abraza formas fluidas con radios de borde pronunciados (`14px` para bloques principales).

*   **Tarjetas de Métricas (Widgets):** Deben incluir un artefacto visual excéntrico. La esquina superior derecha de las tarjetas principales alberga un círculo gigante desenfocado y con bajísima opacidad (7%) del color de la métrica (Volt, Coral, o Status), simulando un reflejo interno de luz.
*   **Botones:** Pill-shaped o con radio de `10px`. Los primarios usan fondo `primary-volt` con texto oscuro (`#15171C`) para máximo contraste. Los secundarios (Ghost) usan fondo transparente, texto blanco y un borde `border-active`.
*   **Gráficos (Charts):** Los gráficos de barras abandonan los colores sólidos aburridos. Deben utilizar gradientes lineales verticales. Una barra activa va de `primary-volt` a `primary-dim`, con los bordes superiores redondeados (`6px 6px 0 0`).
*   **Tablas y Listas:** Avatares y etiquetas flotantes (`tags`) con esquinas súper redondeadas (`20px`). El texto secundario debe tener buen contraste para escaneo rápido (buscar un socio en milisegundos).

## 5. Instrucción Crítica para el Generador (IA)
Al maquetar vistas basadas en este diseño:
1. Siempre respeta el Sidebar oscuro a la izquierda con íconos Outline.
2. Utiliza las clases de utilidad para pintar los "Bordes Vivos".
3. Asegura un "Gutter" (espacio entre columnas) de al menos `16px` a `18px` para que el panel de control respire y se vea lujoso, no amontonado.