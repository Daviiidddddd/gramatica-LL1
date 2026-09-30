"""Analizador semántico y evaluación.

El análisis semántico recorre el árbol que entrega el analizador sintáctico y
revisa lo que la gramática no puede revisar por sí sola:

  1. que una variable esté asignada antes de usarse;
  2. los tipos de cada operación (entero y real);
  3. que el módulo '%' se use solo entre enteros;
  4. que no se divida entre la constante cero.

Reglas de tipos:
  +  -  *   enteros si los dos operandos son enteros; real en cualquier otro caso
  /          siempre real
  %          solo entre enteros
  - unario   conserva el tipo
  abs, |x|   conserva el tipo
  sin cos tan  reciben radianes y devuelven real

Después del análisis, ejecutar() calcula el valor de cada variable.
"""

import math


class ErrorSemantico(Exception):
    pass


class ErrorEjecucion(Exception):
    pass


def _tipo_resultado(operador, izq, der, linea):
    if operador == "%":
        if izq != "entero" or der != "entero":
            raise ErrorSemantico(
                f"línea {linea}: el módulo '%' solo se puede usar entre enteros "
                f"(se recibió {izq} y {der})."
            )
        return "entero"
    if operador == "/":
        return "real"
    return "entero" if izq == "entero" and der == "entero" else "real"


def _es_cero(nodo):
    return nodo[0] == "num" and nodo[1] == 0


def analizar(arbol):
    """Revisa el programa y devuelve la tabla de símbolos con el tipo de cada variable."""
    tabla = {}

    def tipo_de(nodo):
        etiqueta = nodo[0]

        if etiqueta == "num":
            return nodo[2]

        if etiqueta == "var":
            nombre, linea = nodo[1], nodo[2]
            if nombre not in tabla:
                raise ErrorSemantico(
                    f"línea {linea}: la variable '{nombre}' se usa sin haber sido asignada."
                )
            return tabla[nombre]

        if etiqueta == "neg":
            return tipo_de(nodo[1])

        if etiqueta == "abs":
            return tipo_de(nodo[1])

        if etiqueta == "func":
            tipo_de(nodo[2])
            return "real"

        if etiqueta == "bin":
            _, operador, izq, der, linea = nodo
            t_izq, t_der = tipo_de(izq), tipo_de(der)
            if operador in ("/", "%") and _es_cero(der):
                raise ErrorSemantico(f"línea {linea}: división entre cero.")
            return _tipo_resultado(operador, t_izq, t_der, linea)

        raise ErrorSemantico(f"nodo desconocido en el árbol: {etiqueta}")

    for _, nombre, expresion, _linea in arbol:
        tabla[nombre] = tipo_de(expresion)

    return tabla


def ejecutar(arbol):
    """Evalúa el programa y devuelve la tabla con el valor de cada variable."""
    valores = {}

    def valor_de(nodo):
        etiqueta = nodo[0]

        if etiqueta == "num":
            return nodo[1]

        if etiqueta == "var":
            return valores[nodo[1]]

        if etiqueta == "neg":
            return -valor_de(nodo[1])

        if etiqueta == "abs":
            return abs(valor_de(nodo[1]))

        if etiqueta == "func":
            funcion = {"sin": math.sin, "cos": math.cos, "tan": math.tan}[nodo[1]]
            return funcion(valor_de(nodo[2]))

        _, operador, izq, der, linea = nodo
        a, b = valor_de(izq), valor_de(der)
        if operador in ("/", "%") and b == 0:
            raise ErrorEjecucion(f"línea {linea}: división entre cero.")
        if operador == "+":
            return a + b
        if operador == "-":
            return a - b
        if operador == "*":
            return a * b
        if operador == "/":
            return a / b
        return a % b

    for _, nombre, expresion, _linea in arbol:
        valores[nombre] = valor_de(expresion)

    return valores
