import os
import subprocess
from lexer import Lexer
from parser import Parser, ParserError
from analyzer import SemanticAnalyzer, SemanticError
from codegen import IRGenerator
from wasm_codegen import WasmGenerator
from wasm_compat import WasmCompatibilityChecker
from memory.mem_analyzer import MemoryAnalyzer, MemoryAnalysisError

class PipelineError(Exception):
    pass

class Pipeline:
    def __init__(self, keep_ll=False, target="native"):
        self.keep_ll = keep_ll
        self.target = target

    def run(self, source_path):
        if not os.path.exists(source_path):
            raise PipelineError(f"I couldn't find the file '{source_path}'")
        
        basename = os.path.splitext(os.path.basename(source_path))[0]
        dir_path = os.path.dirname(os.path.abspath(source_path))
        ll_path = os.path.join(dir_path, f"{basename}.ll")

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # 1. Lexing
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            
            # 2. Parsing
            parser = Parser(tokens)
            ast = parser.parse()
            
            # 3. Type Checking & Semantic Analysis
            analyzer = SemanticAnalyzer()
            typed_ast = analyzer.analyze(ast)

            # 3.1 WASM Compatibility Check
            if self.target == "web":
                compat_checker = WasmCompatibilityChecker()
                try:
                    compat_checker.check(typed_ast)
                except Exception as e:
                    raise PipelineError(f"Compatibility Error: {str(e)}")
            
            # 3.5. Memory Safety Analysis
            mem_analyzer = MemoryAnalyzer()
            typed_ast = mem_analyzer.analyze(typed_ast, analyzer.symtab)
            
            # 4. IR Generation
            if self.target == "web":
                generator = WasmGenerator()
            else:
                generator = IRGenerator()
            ir_str = generator.generate(typed_ast)
            
            with open(ll_path, 'w', encoding='utf-8') as f:
                f.write(ir_str)

            if self.target == "web":
                # WASM Pipeline
                wasm_path = os.path.join(dir_path, f"{basename}.wasm")
                html_path = os.path.join(dir_path, f"{basename}.html")
                
                # We compile LLVM IR to WASM using clang --target=wasm32
                try:
                    # Note: We don't link with a separate runtime .o for WASM yet, 
                    # we just compile the .ll. If needed we could include enhanced_wasm_stdlib.c
                    stdlib_c_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime", "enhanced_wasm_stdlib.c")
                    cmd = [
                        "clang",
                        "--target=wasm32",
                        "-nostdlib",
                        "-Wl,--no-entry",
                        "-Wl,--export-all",
                        "-o", wasm_path,
                        ll_path
                    ]
                    # If stdlib is needed, we'd add it here, but for now we export main from .ll
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                except FileNotFoundError:
                    raise PipelineError("I couldn't find 'clang' installed on your system.")
                except subprocess.CalledProcessError as e:
                    raise PipelineError(f"WASM Compilation Error: {e.stderr}")

                # Generate HTML shell
                self.generate_html_shell(html_path, f"{basename}.wasm", basename)

                if not self.keep_ll:
                    if os.path.exists(ll_path): os.remove(ll_path)

                return html_path, {
                    "tokens": len(tokens),
                    "statements": len(ast.statements),
                    "ll_path": ll_path,
                    "obj_path": wasm_path, # using obj_path to store wasm_path for stats
                    "exe_path": html_path
                }

            else:
                # 5. Native Compilation
                obj_path = os.path.join(dir_path, f"{basename}.o")
                exe_name = f"{basename}.exe" if os.name == 'nt' else basename
                exe_path = os.path.join(dir_path, exe_name)
                
                try:
                    subprocess.run(["clang", "-c", ll_path, "-o", obj_path], check=True, capture_output=True, text=True)
                except FileNotFoundError:
                     raise PipelineError("I couldn't find 'clang' installed on your system.")
                except subprocess.CalledProcessError as e:
                     raise PipelineError(f"Native Compilation Error: {e.stderr}")
                
                # 6. Linking
                runtime_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime", "enhanced_runtime.o")
                stdlib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime", "enhanced_stdlib.o")
                memory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime", "enhanced_memory.o")
                
                try:
                     subprocess.run(["clang", obj_path, runtime_path, stdlib_path, memory_path, "-o", exe_path], check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as e:
                     raise PipelineError(f"Native Linking Error: {e.stderr}")
                
                if not self.keep_ll:
                    if os.path.exists(ll_path): os.remove(ll_path)
                    if os.path.exists(obj_path): os.remove(obj_path)
                    
                stats = {
                    "tokens": len(tokens),
                    "statements": len(ast.statements),
                    "ll_path": ll_path,
                    "obj_path": obj_path,
                    "exe_path": exe_path
                }
                return exe_path, stats
            
        except (ParserError, SemanticError, MemoryAnalysisError) as e:
             raise PipelineError(str(e))
        except Exception as e:
             raise PipelineError(f"An unexpected error occurred: {str(e)}")

    def generate_html_shell(self, path, wasm_filename, title):
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced - {title}</title>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{
            background-color: #0f0f0f;
            color: #e0e0e0;
            font-family: 'IBM Plex Mono', monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }}
        .container {{
            width: 80%;
            max-width: 800px;
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }}
        h1 {{
            color: #00ff88;
            margin-top: 0;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }}
        #enhanced-output {{
            white-space: pre-wrap;
            background-color: #000;
            padding: 15px;
            border-radius: 4px;
            border: 1px solid #222;
            min-height: 200px;
            color: #00ff00;
        }}
        .footer {{
            margin-top: 20px;
            font-size: 0.8em;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Enhanced WASM: {title}</h1>
        <div id="enhanced-output"></div>
        <div class="footer">Built with Enhanced Compiler v0.1.0</div>
    </div>
    <script src="browser/enhanced_browser.js"></script>
    <script>
        window.addEventListener('load', () => {{
            EnhancedRuntime.loadAndRun('{wasm_filename}');
        }});
    </script>
</body>
</html>
"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
