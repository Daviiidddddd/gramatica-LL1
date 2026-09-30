"""Cálculo de los conjuntos PRIMEROS, SIGUIENTES y PREDICCIÓN, y verificación LL(1).

La gramática se lee desde un archivo de texto; el programa no pide datos por consola.

Uso:  python conjuntos.py                                  (la gramática de grammars/)
      python conjuntos.py grammars/lenguaje.txt             (un archivo)
      python conjuntos.py mi_gramatica.txt -o salida.txt    (además guarda el resultado)

Formato del archivo (una producción por línea):
      # comentario
      S -> A uno B C
      A -> B C D | ε          alternativas con '|'; ε también se escribe eps o epsilon

Los no terminales son los símbolos que aparecen a la izquierda de la flecha; el resto
son terminales. El símbolo inicial es el lado izquierdo de la primera producción.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

EPSILON = "ε"
FIN = "$"
ALIAS_EPSILON = {"ε", "eps", "epsilon", "λ", "lambda"}
FLECHA = re.compile(r"->|→")
CARPETA_PROGRAMA = Path(__file__).resolve().parent
ARCHIVOS_POR_DEFECTO = ["grammars/lenguaje.txt"]


class ErrorEntrada(Exception):
    """Error en el archivo de entrada (no existe o tiene un formato inválido)."""


@dataclass
class Gramatica:
    nombre: str
    producciones: list[tuple[str, list[str]]]  # (A, [X1, ..., Xk]); la lista vacía es ε
    no_terminales: list[str]
    terminales: list[str]
    advertencias: list[str]

    @property
    def inicial(self) -> str:
        return self.producciones[0][0]


# =============================================================================
# 1. Lectura de la gramática desde archivo
# =============================================================================
def ubicar_archivo(nombre: str) -> Path:
    """Busca el archivo en la carpeta actual y, si no está, junto al programa."""
    ruta = Path(nombre)
    if ruta.is_file():
        return ruta
    if not ruta.is_absolute() and (CARPETA_PROGRAMA / ruta).is_file():
        return CARPETA_PROGRAMA / ruta
    raise ErrorEntrada(
        f"no se encontró el archivo '{nombre}'. Verifique el nombre y que la "
        f"terminal esté ubicada en la carpeta del programa."
    )


def leer_lineas(ruta: Path) -> list[str]:
    """Lee el archivo en UTF-8 (con o sin BOM); si falla, intenta con Latin-1."""
    try:
        return ruta.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return ruta.read_text(encoding="latin-1").splitlines()


def interpretar_gramatica(lineas: list[str], nombre: str = "(texto)") -> Gramatica:
    """Convierte las líneas de un archivo de gramática en una Gramatica."""
    producciones: list[tuple[str, list[str]]] = []

    for num, linea in enumerate(lineas, start=1):
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue

        partes = FLECHA.split(linea, maxsplit=1)
        if len(partes) != 2:
            raise ErrorEntrada(f"{nombre}, línea {num}: falta la flecha '->' en «{linea}».")

        izquierda = partes[0].split()
        if len(izquierda) != 1 or izquierda[0] in ALIAS_EPSILON | {FIN}:
            raise ErrorEntrada(
                f"{nombre}, línea {num}: el lado izquierdo debe ser un único no terminal."
            )

        for alternativa in partes[1].split("|"):
            derecha = [s for s in alternativa.split() if s not in ALIAS_EPSILON]
            if FIN in derecha:
                raise ErrorEntrada(
                    f"{nombre}, línea {num}: '$' está reservado para el fin de entrada."
                )
            producciones.append((izquierda[0], derecha))

    if not producciones:
        raise ErrorEntrada(f"{nombre}: no contiene producciones.")

    no_terminales = list(dict.fromkeys(a for a, _ in producciones))
    terminales = list(dict.fromkeys(
        s for _, der in producciones for s in der if s not in no_terminales
    ))

    # Una letra mayúscula sin producciones suele ser un error de digitación.
    advertencias = [
        f"'{t}' no tiene producciones propias, así que se tomó como terminal."
        for t in terminales if len(t) == 1 and t.isupper()
    ]
    return Gramatica(nombre, producciones, no_terminales, terminales, advertencias)


def leer_gramatica(ruta: Path) -> Gramatica:
    return interpretar_gramatica(leer_lineas(Path(ruta)), Path(ruta).name)


def gramatica_desde_texto(texto: str, nombre: str = "(texto)") -> Gramatica:
    return interpretar_gramatica(texto.splitlines(), nombre)


# =============================================================================
# 2. PRIMEROS
# =============================================================================
def primeros_de_cadena(simbolos: list[str], primeros: dict[str, set[str]],
                       no_terminales: list[str]) -> set[str]:
    """
    PRIMEROS(X1 X2 ... Xk):
      - se agrega PRIMEROS(Xi) - {ε} de izquierda a derecha;
      - se detiene en el primer Xi que no es anulable (o que es terminal);
      - si todos los Xi son anulables (o la cadena es vacía), se agrega ε.
    """
    resultado: set[str] = set()
    for x in simbolos:
        if x not in no_terminales:          # terminal: aporta solo a sí mismo
            resultado.add(x)
            return resultado
        resultado |= primeros[x] - {EPSILON}
        if EPSILON not in primeros[x]:      # no anulable: aquí termina
            return resultado
    resultado.add(EPSILON)
    return resultado


def calcular_primeros(g: Gramatica) -> dict[str, set[str]]:
    """Algoritmo de punto fijo: se repite hasta que ningún conjunto cambie."""
    primeros: dict[str, set[str]] = {a: set() for a in g.no_terminales}
    hubo_cambios = True
    while hubo_cambios:
        hubo_cambios = False
        for a, derecha in g.producciones:
            nuevo = primeros_de_cadena(derecha, primeros, g.no_terminales)
            if not nuevo <= primeros[a]:
                primeros[a] |= nuevo
                hubo_cambios = True
    return primeros


# =============================================================================
# 3. SIGUIENTES
# =============================================================================
def calcular_siguientes(g: Gramatica, primeros: dict[str, set[str]]) -> dict[str, set[str]]:
    """
    - $ pertenece a SIGUIENTES del símbolo inicial.
    - Para cada A -> α B β:
        * se agrega PRIMEROS(β) - {ε} a SIGUIENTES(B);
        * si β es vacía o anulable, se agrega SIGUIENTES(A) a SIGUIENTES(B).
    - Se repite hasta el punto fijo. ε nunca pertenece a un SIGUIENTES.
    """
    siguientes: dict[str, set[str]] = {a: set() for a in g.no_terminales}
    siguientes[g.inicial].add(FIN)
    hubo_cambios = True
    while hubo_cambios:
        hubo_cambios = False
        for a, derecha in g.producciones:
            for i, b in enumerate(derecha):
                if b not in g.no_terminales:
                    continue
                primeros_beta = primeros_de_cadena(derecha[i + 1:], primeros, g.no_terminales)
                nuevo = primeros_beta - {EPSILON}
                if EPSILON in primeros_beta:
                    nuevo |= siguientes[a]
                if not nuevo <= siguientes[b]:
                    siguientes[b] |= nuevo
                    hubo_cambios = True
    return siguientes


# =============================================================================
# 4. PREDICCIÓN
# =============================================================================
def calcular_prediccion(g: Gramatica, primeros: dict[str, set[str]],
                        siguientes: dict[str, set[str]]) -> list[set[str]]:
    """
    PRED(A -> α) = PRIMEROS(α)                             si α no es anulable
                 = (PRIMEROS(α) - {ε}) ∪ SIGUIENTES(A)     si α es anulable
    """
    prediccion = []
    for a, derecha in g.producciones:
        primeros_alfa = primeros_de_cadena(derecha, primeros, g.no_terminales)
        conjunto = primeros_alfa - {EPSILON}
        if EPSILON in primeros_alfa:
            conjunto |= siguientes[a]
        prediccion.append(conjunto)
    return prediccion


def buscar_conflictos(g: Gramatica, prediccion: list[set[str]]):
    """Pares de reglas del mismo no terminal cuya predicción se cruza."""
    conflictos = []
    for i in range(len(g.producciones)):
        for j in range(i + 1, len(g.producciones)):
            if g.producciones[i][0] != g.producciones[j][0]:
                continue
            comun = prediccion[i] & prediccion[j]
            if comun:
                conflictos.append((i, j, comun))
    return conflictos


def calcular_conjuntos(g: Gramatica):
    """Devuelve (primeros, siguientes, prediccion) de la gramática."""
    primeros = calcular_primeros(g)
    siguientes = calcular_siguientes(g, primeros)
    return primeros, siguientes, calcular_prediccion(g, primeros, siguientes)


# =============================================================================
# 5. Reporte
# =============================================================================
def generar_reporte(g: Gramatica) -> str:
    primeros, siguientes, prediccion = calcular_conjuntos(g)

    # Los conjuntos se muestran en el orden en que aparecen los terminales en el archivo.
    orden = {s: k for k, s in enumerate(g.terminales + [FIN, EPSILON])}

    def conjunto(c: set[str]) -> str:
        return "{ " + ", ".join(sorted(c, key=orden.get)) + " }" if c else "∅"

    def regla(k: int) -> str:
        a, derecha = g.producciones[k]
        return f"{a} → {' '.join(derecha) if derecha else EPSILON}"

    ancho_nt = max(len(a) for a in g.no_terminales)
    ancho_regla = max(len(regla(k)) for k in range(len(g.producciones)))
    ancho_num = len(str(len(g.producciones)))
    separador = "=" * 64

    lineas = [
        separador,
        f" Gramática: {g.nombre}",
        separador,
        f"Símbolo inicial : {g.inicial}",
        f"No terminales   : {', '.join(g.no_terminales)}",
        f"Terminales      : {', '.join(g.terminales) if g.terminales else '(ninguno)'}",
    ]
    for aviso in g.advertencias:
        lineas.append(f"Advertencia     : {aviso}")

    lineas += ["", "REGLAS"]
    for k in range(len(g.producciones)):
        lineas.append(f"  {k + 1:>{ancho_num}}. {regla(k)}")

    lineas += ["", "PRIMEROS"]
    for a in g.no_terminales:
        lineas.append(f"  PRIMEROS({a}){' ' * (ancho_nt - len(a))} = {conjunto(primeros[a])}")

    lineas += ["", "SIGUIENTES"]
    for a in g.no_terminales:
        lineas.append(f"  SIGUIENTES({a}){' ' * (ancho_nt - len(a))} = {conjunto(siguientes[a])}")

    lineas += ["", "PREDICCIÓN"]
    for k in range(len(g.producciones)):
        lineas.append(
            f"  {k + 1:>{ancho_num}}. {regla(k):<{ancho_regla}}   {conjunto(prediccion[k])}"
        )

    conflictos = buscar_conflictos(g, prediccion)
    lineas.append("")
    if conflictos:
        lineas.append("¿ES LL(1)? NO. Reglas con predicción en común:")
        for i, j, comun in conflictos:
            lineas.append(f"  {g.producciones[i][0]}: reglas {i + 1} y {j + 1} comparten {conjunto(comun)}")
    else:
        lineas.append("¿ES LL(1)? SÍ: las reglas de cada no terminal tienen predicciones disjuntas.")

    return "\n".join(lineas) + "\n"


# =============================================================================
# 6. Programa principal
# =============================================================================
def main() -> int:
    # Salida en UTF-8 para que ε, → y las tildes se vean bien en cualquier sistema.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(
        prog="conjuntos.py",
        description="Calcula los conjuntos PRIMEROS, SIGUIENTES y PREDICCIÓN "
                    "de gramáticas leídas desde archivos de texto.",
    )
    parser.add_argument(
        "archivos", nargs="*",
        help="archivos de gramática (por defecto: los dos de grammars/)",
    )
    parser.add_argument(
        "-o", "--salida", metavar="ARCHIVO",
        help="además de mostrar el resultado, lo guarda en ARCHIVO",
    )
    args = parser.parse_args()

    reportes: list[str] = []
    hubo_errores = False
    for nombre in args.archivos or ARCHIVOS_POR_DEFECTO:
        try:
            reporte = generar_reporte(leer_gramatica(ubicar_archivo(nombre)))
        except (OSError, ErrorEntrada) as error:
            print(f"Error: {error}\n", file=sys.stderr)
            hubo_errores = True
            continue
        print(reporte)
        reportes.append(reporte)

    if args.salida and reportes:
        destino = Path(args.salida)
        destino.write_text("\n".join(reportes), encoding="utf-8")
        print(f"Resultado guardado en: {destino.resolve()}")

    return 1 if hubo_errores else 0


if __name__ == "__main__":
    sys.exit(main())
