#!/usr/bin/env python3
import argparse
import sys
import os
import json

from lexer import Lexer
from parser import Parser
from printer import ast_to_json
from analyzer import SemanticAnalyzer
from codegen import IRGenerator
from wasm_codegen import WasmGenerator
from pipeline import Pipeline, PipelineError
from memory.mem_analyzer import MemoryAnalyzer, MemoryAnalysisError

VERSION = "0.1.0"

def main():
    parser = argparse.ArgumentParser(description="Enhanced Language Compiler", add_help=False)
    parser.add_argument("command", nargs="?", help="The command to run (get, publish, clean, or file path)")
    parser.add_argument("extra", nargs="*", help="Extra arguments for the command")
    parser.add_argument("--run", action="store_true", help="Compile and run immediately")
    parser.add_argument("--ir", action="store_true", help="Stop after IR generation and show .ll")
    parser.add_argument("--ast", action="store_true", help="Stop after parsing and show AST JSON")
    parser.add_argument("--check", action="store_true", help="Run semantic analysis only")
    parser.add_argument("--lsp", action="store_true", help="Start the Language Server (LSP)")
    parser.add_argument("--target", default="native", choices=["native", "web"], help="Compilation target (native or web)")
    parser.add_argument("--version", action="store_true", help="Print compiler version")
    parser.add_argument("--help", action="store_true", help="Print this help message")
    
    args = parser.parse_args()
    
    if args.version:
        print(f"Enhanced {VERSION}")
        sys.exit(0)

    if args.lsp:
        from lsp.server import LSPServer
        LSPServer().run()
        sys.exit(0)

    if args.command == "get":
        # enhc get the [name] package
        if len(args.extra) >= 3 and args.extra[0] == "the" and args.extra[2] == "package":
            pkg_name = args.extra[1]
            print(f"→ Getting the '{pkg_name}' package...")
            # Simulated Registry logic
            # Registry is at the project root
            registry_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Registry")
            packages_path = os.path.join(os.getcwd(), "enhanced_packages")
            if not os.path.exists(packages_path):
                os.makedirs(packages_path)
            
            src = os.path.join(registry_path, pkg_name)
            dst = os.path.join(packages_path, pkg_name)
            if os.path.exists(src):
                import shutil
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"[OK] Package '{pkg_name}' installed to enhanced_packages/")
            else:
                print(f"[Error] Package '{pkg_name}' not found in Registry at {registry_path}")
            sys.exit(0)

    if args.command == "publish":
        print("→ Publishing package...")
        # Simulated publish logic: bundle current folder into .enpkg
        import zipfile
        pkg_name = "my_package" # Should read from manifest.en
        if os.path.exists("manifest.en"):
            with open("manifest.en", "r") as f:
                for line in f:
                    if "this is the" in line:
                        pkg_name = line.split('"')[1]
                        break
        
        with zipfile.ZipFile(f"{pkg_name}.enpkg", 'w') as zipf:
            for root, dirs, files in os.walk("."):
                if "enhanced_packages" in root or ".git" in root:
                    continue
                for file in files:
                    if not file.endswith(".enpkg"):
                        zipf.write(os.path.join(root, file))
        print(f"[OK] Published as {pkg_name}.enpkg")
        sys.exit(0)

    if args.command == "clean":
        print("→ Cleaning enhanced_packages/...")
        import shutil
        if os.path.exists("enhanced_packages"):
            shutil.rmtree("enhanced_packages")
            print("[OK] Cleaned.")
        else:
            print("Nothing to clean.")
        sys.exit(0)
        
    if args.help or not args.command:
        print(f"Enhanced Compiler {VERSION}")
        print("Usage:")
        print("  enhc <file.en>              -> compile and produce executable")
        print("  enhc get the <pkg> package  -> download a package")
        print("  enhc publish                -> bundle current package")
        print("  enhc clean                  -> remove downloaded packages")
        print("  enhc <file.en> --target web -> compile for WebAssembly")
        print("  enhc <file.en> --run        -> compile and immediately run it")
        print("  enhc --lsp                  -> start the Language Server")
        print("  enhc --version              -> print version")
        print("  enhc --help                 -> print this message")
        sys.exit(0)

    source_path = args.command
    if not os.path.exists(source_path):
        print(f"[Error] I couldn't find the file '{source_path}'")
        sys.exit(1)
        
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
            
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        ast_parser = Parser(tokens)
        ast = ast_parser.parse()
        
        if args.ast:
            print(ast_to_json(ast))
            sys.exit(0)
            
        analyzer = SemanticAnalyzer()
        typed_ast = analyzer.analyze(ast)
        
        if args.check:
            print("[OK] Type checked -- no errors")
            sys.exit(0)

        # Memory Safety Analysis
        mem_analyzer = MemoryAnalyzer()
        typed_ast = mem_analyzer.analyze(typed_ast, analyzer.symtab)
            
        if args.target == "web":
            generator = WasmGenerator()
        else:
            generator = IRGenerator()
            
        ir_str = generator.generate(typed_ast)
        
        if args.ir:
            print(ir_str)
            sys.exit(0)
            
        pipe = Pipeline(keep_ll=True, target=args.target)
        exe_path, stats = pipe.run(source_path)
        
        print(f"[OK] Lexed {stats['tokens']} tokens")
        print(f"[OK] Parsed {stats['statements']} statements")
        print(f"[OK] Type checked — no errors")
        ll_name = os.path.basename(stats['ll_path'])
        obj_name = os.path.basename(stats['obj_path'])
        exe_name = os.path.basename(stats['exe_path'])
        print(f"[OK] Generated LLVM IR ({ll_name})")
        print(f"[OK] Compiled to object ({obj_name})")
        print(f"[OK] Linked executable ({exe_name})")
        
        if args.run:
            print(f"→ Running {exe_name}...")
            os.system(exe_path)
        else:
            print(f"→ Run it with: {exe_path}")
            
    except (PipelineError, MemoryAnalysisError) as e:
        print(f"[Error] {str(e)}")
        sys.exit(1)
    except Exception as e:
         print(f"[Error] {str(e)}")
         sys.exit(1)

if __name__ == "__main__":
    main()
