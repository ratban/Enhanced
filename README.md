# Enhanced

A programming language that uses plain English syntax and compiles to native binaries.

```
say "Hello, World"
```

```
the number x is 5.
the number y is 10.
add x and y then say the result.
```

That's real code. It compiles. It runs.

---

## What it is

Enhanced is a systems-level language where the syntax is plain English. No brackets, no semicolons, no symbols. You write code the way you'd explain something to another person, and the compiler turns it into a native binary that runs at C++ speed.

It uses LLVM as its backend — the same backend as Clang and Rust. The English is just the front door. The machine code underneath is identical to what a C++ compiler would produce.

## Why

Every language before this made a tradeoff. Python is readable but slow. C++ is fast but unreadable. Rust is safe but complex. Enhanced doesn't pick one. It targets all four at the same time: readable, fast, safe, and simple enough that you never have to fight the language to get work done.

## Features

- Compiles `.en` files to native executables via LLVM
- Memory safe without a garbage collector or borrow checker
- Built-in standard library for files, HTTP, lists, math, and time
- FFI system for calling any C or C++ library
- Interactive REPL (`enhanced` command)
- VSCode extension with syntax highlighting and live error detection
- Language Server Protocol (LSP) for any editor

## Install

**Linux / macOS**
```bash
git clone https://github.com/ayredev/Enhanced
cd enhanced
bash install.sh
```

**Windows**
```powershell
git clone https://github.com/ayredev/Enhanced
cd enhanced
.\installer\install.ps1
```

Requirements: Python 3.10+, LLVM/Clang

Verify the install worked:
```bash
enhanced --version
enhc examples/hello.en --run
```

## Usage

**Compile a file**
```bash
enhc hello.en
./hello
```

**Compile and run immediately**
```bash
enhc hello.en --run
```

**Open the REPL**
```bash
enhanced
```

**Check for errors only**
```bash
enhc hello.en --check
```

## Example programs

**Hello World**
```
say "Hello, World"
```

**Variables and math**
```
the number x is 5.
the number y is 10.
add x and y then say the result.
```

**Lists**
```
create a list of names called team.
add "Alice" to team.
add "Bob" to team.
for each name in team say name.
```

**File I/O**
```
open the file "notes.txt" as f.
write "Hello from Enhanced" to f.
close f.
say "Done."
```

**Discord RPC**
```
the text app_id is "123456789012345678".
load the library "discord_partner_sdk".
call "Discord_Initialize" with app_id and 1 and null and 0.
set the presence state to "Coding in Enhanced".
set the presence details to "Building something real".
call "Discord_UpdatePresence" with the presence.
wait 30 seconds.
call "Discord_Shutdown".
```

## Memory safety

Enhanced has two layers of memory safety.

**Generational References** prevent use-after-free at runtime. Every heap object carries a generation number. When you free it, the number increments. Any old pointer trying to access it sees a mismatch and gets a plain English error instead of a crash.

**Linear Types** prevent resource leaks at compile time. File handles, sockets, and connections are tracked by the compiler. If you forget to close one, the program won't compile. You get a plain English message telling you exactly where the problem is.

No garbage collector. No borrow checker. It just works.

## VSCode extension

Install `enhanced-lang-0.1.0.vsix` from the `enhanced-vscode/` folder via the Extensions tab in VSCode. You get syntax highlighting, live error squiggles, autocomplete, hover documentation, go-to-definition, and auto-formatting on save.

## Tests

```bash
make test
```

65 tests across all compiler phases. Lexer, parser, semantic analyzer, memory safety, codegen, REPL, and LSP.

## Project structure

```
enhanced/
├── lexer.py          tokenizer
├── parser.py         recursive descent parser
├── ast_nodes.py      AST node definitions
├── analyzer.py       semantic analysis + type checking
├── codegen.py        LLVM IR generation
├── enhc.py           compiler CLI
├── pipeline.py       full compile pipeline
├── memory/           generational refs + linear types
├── stdlib/           standard library
├── ffi/              foreign function interface
├── repl/             interactive shell
├── lsp/              language server
├── runtime/          C runtime linked into all binaries
├── enhanced-vscode/  VSCode extension
└── examples/         example .en programs
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
