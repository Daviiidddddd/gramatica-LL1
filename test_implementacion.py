"""Pruebas de implementación.  Ejecutar:  python -m unittest -v test_implementacion"""
import math
import unittest
from pathlib import Path

import conjuntos
import lexico
import semantico
import sintactico

RAIZ = Path(__file__).resolve().parent
GRAMATICA = RAIZ / "grammars" / "lenguaje.txt"


def clases(texto):
    return [t.clase for t in lexico.analizar(texto)]


def ejecutar(texto):
    """Analiza y evalúa un programa; devuelve la tabla de valores."""
    arbol = sintactico.analizar(texto)
    semantico.analizar(arbol)
    return semantico.ejecutar(arbol)


def tipos(texto):
    return semantico.analizar(sintactico.analizar(texto))


class TestLexico(unittest.TestCase):
    def test_tokens_de_una_sentencia(self):
        self.assertEqual(clases("x = 1 + 2;"),
                         ["ID", "asig", "NUM", "mas", "NUM", "fin", "$"])

    def test_todos_los_operadores(self):
        self.assertEqual(clases("a = 1 - 2 * 3 / 4 % 5;"),
                         ["ID", "asig", "NUM", "menos", "NUM", "por", "NUM",
                          "entre", "NUM", "modulo", "NUM", "fin", "$"])

    def test_comentarios_y_saltos_de_linea(self):
        tokens = lexico.analizar("# comentario\nx = 1;  # otro\n")
        self.assertEqual([t.clase for t in tokens],
                         ["ID", "asig", "NUM", "fin", "$"])
        self.assertEqual(tokens[0].linea, 2)

    def test_palabras_clave_y_similares(self):
        self.assertEqual(clases("x = sin(0) + coseno;"),
                         ["ID", "asig", "sin", "abre", "NUM", "cierra",
                          "mas", "ID", "fin", "$"])

    def test_simbolo_no_reconocido(self):
        with self.assertRaises(lexico.ErrorLexico):
            lexico.analizar("x = 4 @ 2;")

    def test_numero_real_incompleto(self):
        with self.assertRaises(lexico.ErrorLexico):
            lexico.analizar("x = 4.;")


class TestSintactico(unittest.TestCase):
    def test_precedencia_de_operadores(self):
        self.assertEqual(ejecutar("x = 2 + 3 * 4;")["x"], 14)
        self.assertEqual(ejecutar("x = 10 - 8 % 3;")["x"], 8)

    def test_asociatividad_izquierda(self):
        # el ejemplo de clase: (4 - 5) - 10 = -11, no 4 - (5 - 10) = 9
        self.assertEqual(ejecutar("x = 4 - 5 - 10;")["x"], -11)
        self.assertEqual(ejecutar("x = 10 - 3 - 2;")["x"], 5)
        self.assertEqual(ejecutar("x = 100 / 5 / 2;")["x"], 10.0)

    def test_la_traza_registra_el_analisis(self):
        _, traza = sintactico.analizar("x = 4 - 5;", traza=True)
        acciones = [accion for _, accion, _ in traza]
        self.assertEqual(acciones[0], "prog -> sents")
        self.assertIn("expr' -> - term expr'", acciones)
        self.assertIn("expr' -> ε", acciones)
        self.assertEqual(acciones[-1], "fin de entrada: aceptada")

    def test_sobran_tokens_despues_de_la_ultima_sentencia(self):
        with self.assertRaises(sintactico.ErrorSintactico):
            sintactico.analizar("x = 1; )")

    def test_parentesis(self):
        self.assertEqual(ejecutar("x = (2 + 3) * 4;")["x"], 20)

    def test_menos_unario(self):
        self.assertEqual(ejecutar("x = -3 + 1;")["x"], -2)
        self.assertEqual(ejecutar("x = - -3;")["x"], 3)
        self.assertEqual(ejecutar("x = 2 * -4;")["x"], -8)

    def test_valor_absoluto_en_sus_dos_formas(self):
        self.assertEqual(ejecutar("x = |3 - 10|;")["x"], 7)
        self.assertEqual(ejecutar("x = abs(-2.5);")["x"], 2.5)

    def test_varias_sentencias_encadenadas(self):
        valores = ejecutar("a = 2; b = a * 3; c = b - a;")
        self.assertEqual((valores["a"], valores["b"], valores["c"]), (2, 6, 4))

    def test_falta_punto_y_coma(self):
        with self.assertRaises(sintactico.ErrorSintactico):
            sintactico.analizar("x = 3 + 4\ny = 2;")

    def test_parentesis_sin_cerrar(self):
        with self.assertRaises(sintactico.ErrorSintactico):
            sintactico.analizar("x = (3 + 4;")

    def test_falta_el_igual(self):
        with self.assertRaises(sintactico.ErrorSintactico):
            sintactico.analizar("x 3;")


class TestSemantico(unittest.TestCase):
    def test_tipos_de_las_operaciones(self):
        tabla = tipos("a = 2 + 3; b = 2 + 3.0; c = 7 / 2; d = 7 % 2; e = sin(0);")
        self.assertEqual(tabla, {"a": "entero", "b": "real", "c": "real",
                                 "d": "entero", "e": "real"})

    def test_division_siempre_da_real(self):
        self.assertEqual(ejecutar("x = 4 / 2;")["x"], 2.0)
        self.assertEqual(tipos("x = 4 / 2;")["x"], "real")

    def test_variable_usada_sin_asignar(self):
        with self.assertRaises(semantico.ErrorSemantico):
            tipos("x = 2 + y;")

    def test_modulo_solo_entre_enteros(self):
        with self.assertRaises(semantico.ErrorSemantico):
            tipos("x = 7.5 % 2;")

    def test_division_entre_cero(self):
        with self.assertRaises(semantico.ErrorSemantico):
            tipos("x = 5 / 0;")

    def test_valor_absoluto_conserva_el_tipo(self):
        self.assertEqual(tipos("x = |-3|; y = |-3.5|;"), {"x": "entero", "y": "real"})


class TestFunciones(unittest.TestCase):
    def test_trigonometricas_en_radianes(self):
        valores = ejecutar("a = sin(0); b = cos(0); c = tan(0);")
        self.assertEqual((valores["a"], valores["b"], valores["c"]), (0.0, 1.0, 0.0))

    def test_tangente_como_razon(self):
        valores = ejecutar("ang = 0.7853981634; r = sin(ang) / cos(ang);")
        self.assertAlmostEqual(valores["r"], 1.0, places=6)

    def test_funcion_sobre_expresion(self):
        self.assertAlmostEqual(ejecutar("x = abs(sin(0 - 1));")["x"], math.sin(1), places=9)


class TestGramatica(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = conjuntos.leer_gramatica(GRAMATICA)
        cls.prim, cls.sig, cls.pred = conjuntos.calcular_conjuntos(cls.g)

    def test_la_gramatica_es_ll1(self):
        self.assertEqual(conjuntos.buscar_conflictos(self.g, self.pred), [])

    def test_sin_prefijos_comunes(self):
        # dos alternativas del mismo no terminal no pueden empezar con el mismo símbolo
        vistos = {}
        for a, derecha in self.g.producciones:
            primero = derecha[0] if derecha else "ε"
            self.assertNotIn((a, primero), vistos, f"prefijo común en {a}")
            vistos[(a, primero)] = True

    def test_no_hay_recursion_izquierda(self):
        for a, derecha in self.g.producciones:
            self.assertNotEqual(derecha[:1], [a], f"recursión izquierda en {a}")

    def test_primeros_de_expr(self):
        self.assertEqual(self.prim["expr"],
                         {"NUM", "ID", "abre", "barra", "menos", "abs", "sin", "cos", "tan"})
        self.assertEqual(self.prim["expr_r"], {"mas", "menos", "ε"})

    def test_siguientes_de_expr(self):
        self.assertEqual(self.sig["expr"], {"fin", "cierra", "barra"})
        self.assertEqual(self.sig["func"], {"abre"})

    def test_prediccion_de_fact(self):
        for (a, derecha), prediccion in zip(self.g.producciones, self.pred):
            if a != "fact":
                continue
            if derecha == ["menos", "fact"]:
                self.assertEqual(prediccion, {"menos"})
            else:
                self.assertEqual(prediccion, self.prim["unidad"])


class TestTransformaciones(unittest.TestCase):
    """Los dos borradores previos sí tienen conflictos; por eso hubo que transformarlos."""

    def conflictos_de(self, archivo):
        g = conjuntos.leer_gramatica(RAIZ / "grammars" / archivo)
        _, _, pred = conjuntos.calcular_conjuntos(g)
        return {g.producciones[i][0] for i, _, _ in conjuntos.buscar_conflictos(g, pred)}

    def test_el_borrador_con_recursion_izquierda_no_es_ll1(self):
        self.assertEqual(self.conflictos_de("borrador1_recursion.txt"), {"expr", "term"})

    def test_el_borrador_con_prefijo_comun_no_es_ll1(self):
        self.assertEqual(self.conflictos_de("borrador2_prefijo.txt"), {"expr", "term"})


class TestEjemplos(unittest.TestCase):
    def test_demo_completo(self):
        valores = ejecutar((RAIZ / "ejemplos" / "demo.lp").read_text(encoding="utf-8"))
        self.assertEqual(valores["area"], 30.0)
        self.assertEqual(valores["resto"], 5)
        self.assertEqual(valores["desfase"], 7)
        self.assertAlmostEqual(valores["razon"], 1.0, places=6)

    def test_los_ejemplos_con_error_fallan_donde_deben(self):
        casos = [
            ("error_lexico.lp", lexico.ErrorLexico),
            ("error_sintactico.lp", sintactico.ErrorSintactico),
            ("error_semantico.lp", semantico.ErrorSemantico),
            ("error_modulo.lp", semantico.ErrorSemantico),
        ]
        for archivo, excepcion in casos:
            with self.subTest(archivo=archivo):
                texto = (RAIZ / "ejemplos" / archivo).read_text(encoding="utf-8")
                with self.assertRaises(excepcion):
                    ejecutar(texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
