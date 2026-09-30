"""Analizador léxico: convierte el texto del programa en una lista de tokens.

Cada token guarda su clase, su lexema y la línea y columna donde apareció, para
poder reportar los errores con la posición exacta.

Clases de token (coinciden con los terminales de grammars/lenguaje.txt):
    ID  NUM  asig  fin  mas  menos  por  entre  modulo
    abre  cierra  barra  abs  sin  cos  tan  $
"""


class ErrorLexico(Exception):
    pass


PALABRAS_CLAVE = {"abs": "abs", "sin": "sin", "cos": "cos", "tan": "tan"}

SIMBOLOS = {
    "=": "asig",
    ";": "fin",
    "+": "mas",
    "-": "menos",
    "*": "por",
    "/": "entre",
    "%": "modulo",
    "(": "abre",
    ")": "cierra",
    "|": "barra",
}

FIN_ENTRADA = "$"


class Token:
    def __init__(self, clase, lexema, linea, columna):
        self.clase = clase
        self.lexema = lexema
        self.linea = linea
        self.columna = columna

    def __repr__(self):
        return f"{self.clase}({self.lexema}) [{self.linea}:{self.columna}]"

    def __eq__(self, otro):  # para comparar en las pruebas
        return (self.clase, self.lexema) == (otro.clase, otro.lexema)


def analizar(texto):
    """Devuelve la lista de tokens del programa, terminada en el token $."""
    tokens = []
    linea = columna = 1
    i = 0

    while i < len(texto):
        c = texto[i]

        if c == "\n":
            linea += 1
            columna = 1
            i += 1
            continue

        if c in " \t\r":
            i += 1
            columna += 1
            continue

        if c == "#":                                    # comentario hasta fin de línea
            while i < len(texto) and texto[i] != "\n":
                i += 1
            continue

        if c.isdigit():                                 # NUM: entero o real
            inicio, col_inicio = i, columna
            while i < len(texto) and texto[i].isdigit():
                i += 1
                columna += 1
            if i < len(texto) and texto[i] == ".":
                i += 1
                columna += 1
                if i >= len(texto) or not texto[i].isdigit():
                    raise ErrorLexico(
                        f"línea {linea}, columna {columna}: falta la parte decimal del número."
                    )
                while i < len(texto) and texto[i].isdigit():
                    i += 1
                    columna += 1
            tokens.append(Token("NUM", texto[inicio:i], linea, col_inicio))
            continue

        if c.isalpha() or c == "_":                     # ID o palabra clave
            inicio, col_inicio = i, columna
            while i < len(texto) and (texto[i].isalnum() or texto[i] == "_"):
                i += 1
                columna += 1
            lexema = texto[inicio:i]
            clase = PALABRAS_CLAVE.get(lexema.lower(), "ID")
            tokens.append(Token(clase, lexema, linea, col_inicio))
            continue

        if c in SIMBOLOS:
            tokens.append(Token(SIMBOLOS[c], c, linea, columna))
            i += 1
            columna += 1
            continue

        raise ErrorLexico(f"línea {linea}, columna {columna}: símbolo no reconocido '{c}'.")

    tokens.append(Token(FIN_ENTRADA, "$", linea, columna))
    return tokens
