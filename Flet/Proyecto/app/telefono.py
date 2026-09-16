# =============================================================================
# telefono.py — Teléfonos con código de país
# =============================================================================
# Gemelo de utils/telefono.ts de la PWA. Decisión del dueño (2026-09-16): con
# socios o empleados extranjeros un número sin país "se traspapela", así que
# todo campo de teléfono tiene selector de país (Argentina por defecto) y se
# guarda el número COMPLETO: "+54 3415551234".
#
# Sin migración: los números viejos no traen "+" y se leen como argentinos,
# que es lo que eran. El backend ya aceptaba el "+" y los espacios.

import re

# (nombre, prefijo con "+", bandera). Mismo orden que PAISES en la PWA.
PAISES = [
    ("Argentina", "+54", "🇦🇷"),
    ("Uruguay", "+598", "🇺🇾"),
    ("Chile", "+56", "🇨🇱"),
    ("Paraguay", "+595", "🇵🇾"),
    ("Bolivia", "+591", "🇧🇴"),
    ("Brasil", "+55", "🇧🇷"),
    ("Perú", "+51", "🇵🇪"),
    ("Colombia", "+57", "🇨🇴"),
    ("Venezuela", "+58", "🇻🇪"),
    ("Ecuador", "+593", "🇪🇨"),
    ("México", "+52", "🇲🇽"),
    ("Estados Unidos", "+1", "🇺🇸"),
    ("España", "+34", "🇪🇸"),
    ("Italia", "+39", "🇮🇹"),
]

PREFIJO_DEFAULT = "+54"


def limpiar_numero_local(valor: str) -> str:
    """Lo que se acepta tipear en la parte local del número (sin letras ni +)."""
    return re.sub(r"[^()\-\s0-9]", "", valor or "")


def separar_telefono(valor: str | None) -> tuple[str, str]:
    """
    "+54 3415551234" -> ("+54", "3415551234"). Sin "+", es un número cargado
    antes del selector: argentino. Gana el prefijo más largo que coincida, para
    no partir un "+598" como "+59" + "8…".
    """
    limpio = (valor or "").strip()
    if not limpio.startswith("+"):
        return PREFIJO_DEFAULT, limpio

    digitos = re.sub(r"\D", "", limpio[1:])
    for _, prefijo, _ in sorted(PAISES, key=lambda p: -len(p[1])):
        if digitos.startswith(prefijo[1:]):
            resto = limpio[1:].lstrip()
            quedan = len(prefijo) - 1
            while quedan > 0 and resto:
                if resto[0].isdigit():
                    quedan -= 1
                resto = resto[1:]
            return prefijo, resto.strip()
    return PREFIJO_DEFAULT, limpio


def unir_telefono(prefijo: str, numero: str) -> str:
    """Une país y número. Sin número, vacío: el país solo no es un teléfono."""
    numero = (numero or "").strip()
    return f"{prefijo or PREFIJO_DEFAULT} {numero}" if numero else ""
