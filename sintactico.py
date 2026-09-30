"""Analizador sintáctico descendente recursivo (ASDR).

Construido con los cinco pasos vistos en clase:

  1. gramática y símbolo inicial: grammars/lenguaje.txt, símbolo inicial prog;
  2. conjuntos PRIMEROS, SIGUIENTES y PRED: los calcula conjuntos.py;
  3. verificación de que los PRED de cada no terminal son disjuntos;
  4. una función por no terminal y una operación emparejar() por terminal;
  5. tomar el primer token, llamar al símbolo inicial y comprobar el fin de entrada.

Cada función lleva arriba su regla y, al lado de cada rama, el conjunto de
predicción con el que se decide. Como la gramática es LL(1), basta mirar el
token de anticipación: no hay retroceso.

Las reglas expr' y term' salieron de eliminar la recursión izquierda, así que
repiten por la derecha. Para que la resta y la división sigan siendo
asociativas por la izquierda, esas funciones reciben un acumulador con lo que
ya se construyó y lo van envolviendo, igual que el acc del ejemplo 4 - 5 - 10.

El árbol se devuelve como tuplas:

    ('asig',  nombre, expr, linea)
    ('bin',   operador, izq, der, linea)      operador: + - * / %
    ('neg',   expr, linea)
    ('abs',   expr, linea)
    ('func',  nombre, expr, linea)            nombre: sin cos tan
    ('num',   valor, tipo, linea)             tipo: entero | real
    ('var',   nombre, linea)
"""

from lexico import analizar as analizar_lexico

# Conjuntos de predicción usados en las decisiones (salida de conjuntos.py).
PRED_UNIDAD = {"NUM", "ID", "abre", "barra", "abs", "sin", "cos", "tan"}
PRED_EXPR_R = {"mas", "menos"}
PRED_TERM_R = {"por", "entre", "modulo"}
PRED_FUNC = {"abs", "sin", "cos", "tan"}

OPERADORES = {"mas": "+", "menos": "-", "por": "*", "entre": "/", "modulo": "%"}
NOMBRES = {"asig": "'='", "fin": "';'", "abre": "'('", "cierra": "')'", "barra": "'|'"}


class ErrorSintactico(Exception):
    pass


class Analizador:
    def __init__(self, tokens, traza=False):
        self.tokens = tokens
        self.pos = 0
        self.traza = [] if traza else None

    # ------------------------------------------------------- utilidades
    @property
    def token(self):
        """El token de anticipación: el único que se mira para decidir."""
        return self.tokens[self.pos]

    def emparejar(self, esperado):
        """Consume el token si es el esperado; si no, error de sintaxis."""
        if self.token.clase != esperado:
            self.error_sintaxis(NOMBRES.get(esperado, esperado))
        actual = self.token
        self.pos += 1
        self.anotar(f"emparejar {actual.lexema}")
        return actual

    def error_sintaxis(self, esperado):
        t = self.token
        encontrado = "el fin de la entrada" if t.clase == "$" else f"'{t.lexema}'"
        raise ErrorSintactico(
            f"línea {t.linea}, columna {t.columna}: se esperaba {esperado} "
            f"y se encontró {encontrado}."
        )

    def anotar(self, accion):
        """Guarda un paso de la traza: qué se hizo y qué quedaba por leer."""
        if self.traza is None:
            return
        pendiente = " ".join(t.lexema for t in self.tokens[self.pos:])
        self.traza.append((len(self.traza) + 1, accion, pendiente))

    # ------------------------------------------------------- prog y sentencias
    def prog(self):
        """prog -> sents"""
        self.anotar("prog -> sents")
        sentencias = self.sents()
        if self.token.clase != "$":                       # paso 5: sobran tokens
            self.error_sintaxis("el inicio de otra sentencia")
        self.anotar("fin de entrada: aceptada")
        return sentencias

    def sents(self):
        """sents -> sent sents | ε"""
        sentencias = []
        while self.token.clase == "ID":                   # PRED = { ID }
            self.anotar("sents -> sent sents")
            sentencias.append(self.sent())
        self.anotar("sents -> ε")                         # PRED = { $ }
        return sentencias

    def sent(self):
        """sent -> ID asig expr fin"""
        self.anotar("sent -> ID = expr ;")
        nombre = self.emparejar("ID")
        self.emparejar("asig")
        valor = self.expr()
        self.emparejar("fin")
        return ("asig", nombre.lexema, valor, nombre.linea)

    # ------------------------------------------------------- expresiones
    def expr(self):
        """expr -> term expr'"""
        self.anotar("expr -> term expr'")
        return self.expr_r(self.term())

    def expr_r(self, acc):
        """expr' -> mas term expr' | menos term expr' | ε

        acc guarda lo que ya se construyó a la izquierda. Al envolverlo en cada
        vuelta, 4 - 5 - 10 se agrupa como (4 - 5) - 10 = -11.
        """
        if self.token.clase in PRED_EXPR_R:               # PRED = { +, - }
            operador = self.token
            self.anotar(f"expr' -> {operador.lexema} term expr'")
            self.emparejar(operador.clase)
            derecha = self.term()
            nuevo = ("bin", OPERADORES[operador.clase], acc, derecha, operador.linea)
            return self.expr_r(nuevo)
        self.anotar("expr' -> ε")                         # PRED = { ; ) | }
        return acc

    def term(self):
        """term -> fact term'"""
        self.anotar("term -> fact term'")
        return self.term_r(self.fact())

    def term_r(self, acc):
        """term' -> por fact term' | entre fact term' | modulo fact term' | ε"""
        if self.token.clase in PRED_TERM_R:               # PRED = { *, /, % }
            operador = self.token
            self.anotar(f"term' -> {operador.lexema} fact term'")
            self.emparejar(operador.clase)
            derecha = self.fact()
            nuevo = ("bin", OPERADORES[operador.clase], acc, derecha, operador.linea)
            return self.term_r(nuevo)
        self.anotar("term' -> ε")                         # PRED = { ; + - ) | }
        return acc

    def fact(self):
        """fact -> menos fact | unidad"""
        if self.token.clase == "menos":                   # PRED = { - }
            self.anotar("fact -> - fact")
            signo = self.emparejar("menos")
            return ("neg", self.fact(), signo.linea)
        if self.token.clase in PRED_UNIDAD:               # PRED = PRIMEROS(unidad)
            self.anotar("fact -> unidad")
            return self.unidad()
        self.error_sintaxis("un número, una variable, '(', '|' o una función")

    def unidad(self):
        """unidad -> NUM | ID | abre expr cierra | barra expr barra
                   | func abre expr cierra
        """
        t = self.token

        if t.clase == "NUM":                              # PRED = { NUM }
            self.anotar("unidad -> NUM")
            self.emparejar("NUM")
            tipo = "real" if "." in t.lexema else "entero"
            valor = float(t.lexema) if tipo == "real" else int(t.lexema)
            return ("num", valor, tipo, t.linea)

        if t.clase == "ID":                               # PRED = { ID }
            self.anotar("unidad -> ID")
            self.emparejar("ID")
            return ("var", t.lexema, t.linea)

        if t.clase == "abre":                             # PRED = { ( }
            self.anotar("unidad -> ( expr )")
            self.emparejar("abre")
            dentro = self.expr()
            self.emparejar("cierra")
            return dentro                                 # el paréntesis ya cumplió su papel

        if t.clase == "barra":                            # PRED = { | }
            self.anotar("unidad -> | expr |")
            self.emparejar("barra")
            dentro = self.expr()
            self.emparejar("barra")
            return ("abs", dentro, t.linea)

        if t.clase in PRED_FUNC:                          # PRED = { abs, sin, cos, tan }
            self.anotar(f"unidad -> func ( expr )   [func -> {t.lexema}]")
            self.func()
            self.emparejar("abre")
            dentro = self.expr()
            self.emparejar("cierra")
            if t.clase == "abs":
                return ("abs", dentro, t.linea)
            return ("func", t.clase, dentro, t.linea)

        self.error_sintaxis("un número, una variable, '(', '|' o una función")

    def func(self):
        """func -> abs | sin | cos | tan"""
        return self.emparejar(self.token.clase)


def analizar(texto, traza=False):
    """Del texto del programa al árbol sintáctico (paso 5 del ASDR)."""
    analizador = Analizador(analizar_lexico(texto), traza=traza)
    arbol = analizador.prog()
    return (arbol, analizador.traza) if traza else arbol
