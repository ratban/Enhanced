import unittest
from lexer import Lexer
from parser import Parser
from analyzer import SemanticAnalyzer
from wasm_codegen import WasmGenerator

class TestUI(unittest.TestCase):
    def test_map_syntax(self):
        code = 'create a map called scores. set 10 in scores to "Alice". say "Alice" in scores.'
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        SemanticAnalyzer().analyze(ast)
        # If no exception, it works.
        self.assertEqual(len(ast.statements), 3)

    def test_ui_grammar(self):
        code = '''
        create a button called btn.
        set btn's text to "Click Me".
        set btn's color to "red".
        when btn is clicked:
            say "Hello".
        add btn to the screen.
        '''
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        SemanticAnalyzer().analyze(ast)
        self.assertEqual(len(ast.statements), 5)
        self.assertIsInstance(ast.statements[0], UICreateElement)
        self.assertIsInstance(ast.statements[1], UISetProperty)
        self.assertIsInstance(ast.statements[2], UISetProperty)
        self.assertIsInstance(ast.statements[3], UIEventHandler)
        self.assertIsInstance(ast.statements[4], UIAddToScreen)

    def test_wasm_ui_codegen(self):
        code = 'create a button called btn. add btn to the screen.'
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        SemanticAnalyzer().analyze(ast)
        gen = WasmGenerator()
        ir = gen.generate(ast)
        self.assertIn("enhanced_ui_create_element", ir)
        self.assertIn("enhanced_ui_add_to_screen", ir)

if __name__ == '__main__':
    unittest.main()
