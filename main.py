"""Programa principal: ejecuta las tres fases sobre un archivo del lenguaje.

Uso:  python main.py ejemplos/demo.lp            análisis completo y resultados
      python main.py ejemplos/demo.lp --tokens   además muestra los tokens
      python main.py ejemplos/demo.lp --arbol    además muestra el árbol sintáctico
      python main.py ejemplos/demo.lp --traza    además muestra la traza del análisis
      python main.py --conjuntos                 PRIMEROS, SIGUIENTES, PREDICCIÓN y LL(1)
"""

import sys
from pathlib import Path

import conjuntos
import lexico
import semantico
import sintactico

CARPETA = Path(__file__).resolve().parent
GRAMATICA = CARPETA / "grammars" / "lenguaje.txt"


def mostrar_conjuntos():
    print(conjuntos.generar_reporte(conjuntos.leer_gramatica(GRAMATICA)))


def mostrar_traza(traza):
    ancho = max(len(a) for _, a, _ in traza)
    print(f"\n      {'Paso':<5} {'Función / acción':<{ancho}}   Entrada pendiente")
    for paso, accion, pendiente in traza:
        print(f"      {paso:<5} {accion:<{ancho}}   {pendiente}")


def procesar(ruta, ver_tokens=False, ver_arbol=False, ver_traza=False):
    texto = Path(ruta).read_text(encoding="utf-8-sig")

    print(f"===== {Path(ruta).name} =====\n")
    print(texto.strip(), "\n")

    tokens = lexico.analizar(texto)
    print(f"[1] Análisis léxico: {len(tokens) - 1} tokens reconocidos.")
    if ver_tokens:
        for t in tokens:
            print(f"      {t}")

    analizador = sintactico.Analizador(tokens, traza=ver_traza)
    arbol = analizador.prog()
    print(f"[2] Análisis sintáctico: {len(arbol)} sentencias, sin errores.")
    if ver_arbol:
        for sentencia in arbol:
            print(f"      {sentencia}")
    if ver_traza:
        mostrar_traza(analizador.traza)

    tabla = semantico.analizar(arbol)
    print("[3] Análisis semántico: tipos correctos y variables asignadas antes de usarse.")

    valores = semantico.ejecutar(arbol)
    ancho = max(len(n) for n in valores) if valores else 1
    print("\nResultados")
    for nombre, valor in valores.items():
        if isinstance(valor, float):
            valor = round(valor, 6)
        print(f"  {nombre:<{ancho}} = {valor}   ({tabla[nombre]})")
    print()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    argumentos = sys.argv[1:]
    if not argumentos:
        print(__doc__)
        return 1

    if "--conjuntos" in argumentos:
        mostrar_conjuntos()
        return 0

    ver_tokens = "--tokens" in argumentos
    ver_arbol = "--arbol" in argumentos
    ver_traza = "--traza" in argumentos
    archivos = [a for a in argumentos if not a.startswith("--")]

    hubo_errores = False
    for ruta in archivos:
        try:
            procesar(ruta, ver_tokens, ver_arbol, ver_traza)
        except (OSError, lexico.ErrorLexico, sintactico.ErrorSintactico,
                semantico.ErrorSemantico, semantico.ErrorEjecucion) as error:
            etiqueta = {
                lexico.ErrorLexico: "Error léxico",
                sintactico.ErrorSintactico: "Error sintáctico",
                semantico.ErrorSemantico: "Error semántico",
                semantico.ErrorEjecucion: "Error de ejecución",
            }.get(type(error), "Error")
            print(f"{etiqueta}: {error}\n")
            hubo_errores = True

    return 1 if hubo_errores else 0


if __name__ == "__main__":
    sys.exit(main())
