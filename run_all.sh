#!/usr/bin/env bash
# Pruebas + conjuntos de los borradores y de la gramática final + ejemplos
set -e
cd "$(dirname "$0")"

echo "################ PRUEBAS DE IMPLEMENTACIÓN ################"
python3 -m unittest -v test_implementacion

echo; echo "################ BORRADORES: POR QUÉ HUBO QUE TRANSFORMAR ################"
python3 conjuntos.py grammars/borrador1_recursion.txt grammars/borrador2_prefijo.txt \
    | grep -A8 "ES LL(1)"

echo; echo "################ GRAMÁTICA FINAL: CONJUNTOS Y LL(1) ################"
python3 conjuntos.py grammars/lenguaje.txt -o conjuntos.txt

echo; echo "################ EJECUCIÓN DEL LENGUAJE ################"
python3 main.py ejemplos/demo.lp

echo "################ TRAZA DEL ANÁLISIS ################"
python3 main.py ejemplos/asociatividad.lp --traza

echo "################ MANEJO DE ERRORES ################"
for archivo in ejemplos/error_*.lp; do
    python3 main.py "$archivo" | tail -2 || true
done
