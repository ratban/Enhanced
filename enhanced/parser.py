from ast_nodes import *

class ParserError(Exception):
    pass

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek_at(self, offset):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def consume(self):
        tok = self.peek()
        if tok:
            self.pos += 1
        return tok

    def match_type(self, token_type):
        tok = self.peek()
        if tok and tok.type == token_type:
            return self.consume()
        return None

    def match_val(self, token_type, value):
        tok = self.peek()
        if tok and tok.type == token_type and tok.value == value:
            return self.consume()
        return None

    def expect_type(self, token_type, msg):
        tok = self.match_type(token_type)
        if not tok:
            actual = self.peek()
            actual_str = f"{actual.type}('{actual.value}')" if actual else "EOF"
            raise ParserError(f"{msg}. Got {actual_str}")
        return tok

    def expect_val(self, token_type, value, msg):
        tok = self.match_val(token_type, value)
        if not tok:
            actual = self.peek()
            actual_str = f"{actual.type}('{actual.value}')" if actual else "EOF"
            raise ParserError(f"{msg}. Got {actual_str}")
        return tok

    def parse(self):
        statements = []
        while self.peek():
            # Skip stray punctuation between statements
            while self.peek() and self.peek().type == "PUNCTUATION" and self.peek().value == ":":
                self.consume()
            if not self.peek():
                break
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            while self.match_val("PUNCTUATION", ".") or self.match_val("CONNECTOR", "then"):
                pass
            while self.match_val("PUNCTUATION", ","):
                pass
        return Program(statements)

    def parse_statement(self):
        tok = self.peek()
        if not tok:
            return None
        line = tok.line
        stmt = self._parse_statement_inner()
        if stmt:
            stmt.line = line
        return stmt

    def _parse_statement_inner(self):
        tok = self.peek()
        if not tok:
            return None

        # --- v2: define struct or enum ---
        if self.match_val("KEYWORD", "define"):
            return self._parse_define()

        # --- v2: give back (return) ---
        if self.match_val("VERB", "give"):
            self.expect_val("VERB", "back", "Expected 'back' after 'give'")
            val = self.parse_expression()
            return Return(val)

        # --- v2: otherwise block ---
        if self.match_val("KEYWORD", "otherwise"):
            self.match_val("PUNCTUATION", ":")
            body = [self.parse_statement()]
            return OtherwiseBlock(body)

        # --- v2: "to <verb> a <type>:" → method definition ---
        if tok.type == "CONNECTOR" and tok.value == "to":
            return self._parse_method_def()

        elif self.match_val("VERB", "say"):
            # say [key] in [map].
            expr = self.parse_expression()
            if self.match_val("KEYWORD", "in"):
                map_expr = self.parse_expression()
                map_name = map_expr.name if isinstance(map_expr, Identifier) else "unknown"
                return PrintStatement(MapGet(map_name, expr))
            return PrintStatement(expr)

        elif self.match_val("KEYWORD", "the"):
            return self._parse_the()

        elif self.match_val("VERB", "add"):
            left = self.parse_expression()
            if self.match_val("CONNECTOR", "and"):
                right = self.parse_expression()
                return BinaryOp("+", left, right)
            elif self.match_val("CONNECTOR", "to"):
                # Check for "the screen"
                if self.peek() and self.peek().value == "the":
                    self.consume()
                    self.expect_val("NOUN", "screen", "Expected 'screen'")
                    if not isinstance(left, Identifier):
                        raise ParserError("Expected UI element name")
                    return UIAddToScreen(left.name)
                
                list_name = self.expect_type("IDENTIFIER", "Expected list name after 'to'")
                return ListAppend(Identifier(list_name.value), left)
            else:
                raise ParserError("Expected 'and' or 'to' after 'add X'")

        elif self.match_val("VERB", "subtract"):
            left = self.parse_expression()
            self.expect_val("CONNECTOR", "from", "Expected 'from' after subtract X")
            right = self.parse_expression()
            return BinaryOp("-", right, left)

        elif self.match_val("KEYWORD", "for"):
            self.expect_val("KEYWORD", "each", "Expected 'each' after 'for'")
            item_name = self.expect_type("IDENTIFIER", "Expected identifier after 'for each'")
            self.expect_val("KEYWORD", "in", "Expected 'in' after 'for each Z'")
            collection = self.parse_expression()
            body_stmt = self.parse_statement()
            return ForLoop(Identifier(item_name.value), collection, [body_stmt])

        elif self.match_val("KEYWORD", "if"):
            return self._parse_if()

        elif self.match_val("VERB", "create"):
            # UI Element: create a [UI_ELEMENT] called [NAME].
            # Element Types: button, text, input, box
            article = self.expect_type("KEYWORD", "Expected article after 'create'")
            if article.value not in ("a", "an"):
                raise ParserError(f"Expected 'a' or 'an', got {article.value}")
            
            ui_types = ["button", "text", "input", "box"]
            if self.peek() and self.peek().value in ui_types:
                ui_type = self.consume().value
                self.expect_val("VERB", "called", "Expected 'called'")
                name_tok = self.expect_type("IDENTIFIER", "Expected element name")
                return UICreateElement(ui_type, name_tok.value)

            return self._parse_create_legacy(article)

        elif self.match_val("VERB", "set"):
            # UI: set [NAME]'s [PROPERTY] to [VALUE].
            # Map: set [key] in [map] to [value].
            
            # Look ahead for possessive (UI)
            if self.peek() and self.peek().type == "IDENTIFIER" and self.peek_at(1) and self.peek_at(1).type == "POSSESSIVE":
                name_tok = self.consume()
                self.consume() # consume 's
                prop_tok = self.consume()
                self.expect_val("CONNECTOR", "to", "Expected 'to'")
                val = self.parse_expression()
                return UISetProperty(name_tok.value, prop_tok.value, val)

            # Map or legacy set
            key_expr = self.parse_expression()
            
            # Check for map set after parse_expression
            if self.match_val("KEYWORD", "in"):
                map_expr = self.parse_expression()
                map_name = map_expr.name if isinstance(map_expr, Identifier) else "unknown"
                self.expect_val("CONNECTOR", "to", "Expected 'to'")
                val_expr = self.parse_expression()
                return MapSet(map_name, key_expr, val_expr) # MapSet(map_name, key, value)
            
            # Legacy set (e.g. for struct fields)
            return self._parse_set_legacy(key_expr)

        elif self.match_val("VERB", "read"):
            return self._parse_read()

        elif self.match_val("VERB", "write"):
            content = self.parse_expression()
            self.expect_val("CONNECTOR", "to", "Expected 'to'")
            if self.peek() and self.peek().value == "the":
                self.consume()
                self.expect_val("NOUN", "file", "Expected 'file'")
                path = self.parse_expression()
                return FileWrite(path, content)
            else:
                handle_tok = self.expect_type("IDENTIFIER", "Expected handle name after 'write X to'")
                return LinearUse(handle_tok.value, 'write', content)

        elif self.match_val("VERB", "append"):
            content = self.parse_expression()
            self.expect_val("CONNECTOR", "to", "Expected 'to'")
            self.expect_val("KEYWORD", "the", "Expected 'the'")
            self.expect_val("NOUN", "file", "Expected 'file'")
            path = self.parse_expression()
            return FileAppend(path, content)

        elif self.match_val("VERB", "check"):
            self.expect_val("KEYWORD", "if", "Expected 'if'")
            return self._parse_check_if()

        elif self.match_val("VERB", "multiply"):
            left = self.parse_expression()
            self.expect_val("CONNECTOR", "and", "Expected 'and'")
            right = self.parse_expression()
            return BinaryOp("*", left, right)

        elif self.match_val("VERB", "divide"):
            left = self.parse_expression()
            self.expect_val("CONNECTOR", "by", "Expected 'by'")
            right = self.parse_expression()
            return BinaryOp("/", left, right)

        elif self.match_val("VERB", "remove"):
            val = self.parse_expression()
            self.expect_val("CONNECTOR", "from", "Expected 'from'")
            list_expr = self.parse_expression()
            return ListRemove(list_expr, val)

        elif self.match_val("VERB", "sort"):
            list_expr = self.parse_expression()
            return ListSort(list_expr)

        elif self.match_val("VERB", "wait"):
            ms_expr = self.parse_expression()
            self.expect_val("NOUN", "seconds", "Expected 'seconds'")
            return Sleep(ms_expr)

        elif self.match_val("VERB", "get"):
            self.expect_val("KEYWORD", "the", "Expected 'the'")
            self.expect_val("NOUN", "url", "Expected 'url'")
            url = self.parse_expression()
            return HttpGet(url)

        elif self.match_val("VERB", "load"):
            self.expect_val("KEYWORD", "the", "Expected 'the'")
            self.expect_val("NOUN", "library", "Expected 'library'")
            name = self.parse_expression()
            return LoadLibrary(name)

        elif self.match_val("VERB", "call"):
            func = self.parse_expression()
            self.expect_val("CONNECTOR", "with", "Expected 'with'")
            args = [self.parse_expression()]
            while self.match_val("CONNECTOR", "and"):
                args.append(self.parse_expression())
            return FFICall(func, args)

        elif self.match_val("VERB", "free"):
            name_tok = self.expect_type("IDENTIFIER", "Expected variable name after 'free'")
            return HeapFree(name_tok.value)

        elif self.match_val("VERB", "open"):
            self.expect_val("KEYWORD", "the", "Expected 'the'")
            resource_tok = self.peek()
            if resource_tok and resource_tok.value == "file":
                self.consume()
                path = self.parse_expression()
                self.expect_val("KEYWORD", "as", "Expected 'as'")
                handle_tok = self.expect_type("IDENTIFIER", "Expected handle name after 'as'")
                return LinearOpen('file', path, handle_tok.value)
            elif resource_tok and resource_tok.value == "connection":
                self.consume()
                self.expect_val("CONNECTOR", "to", "Expected 'to'")
                addr = self.parse_expression()
                self.expect_val("KEYWORD", "as", "Expected 'as'")
                handle_tok = self.expect_type("IDENTIFIER", "Expected handle name after 'as'")
                return LinearOpen('socket', addr, handle_tok.value)
            elif resource_tok and resource_tok.value == "database":
                self.consume()
                path = self.parse_expression()
                self.expect_val("KEYWORD", "as", "Expected 'as'")
                handle_tok = self.expect_type("IDENTIFIER", "Expected handle name after 'as'")
                from ast_nodes import DatabaseOpen
                return DatabaseOpen(path, handle_tok.value)
            else:
                raise ParserError("Expected 'file', 'connection', or 'database' after 'open the'")

        elif self.match_val("VERB", "close"):
            handle_tok = self.expect_type("IDENTIFIER", "Expected handle name after 'close'")
            return LinearConsume(handle_tok.value)

        elif self.match_val("VERB", "send"):
            data = self.parse_expression()
            self.expect_val("CONNECTOR", "through", "Expected 'through'")
            handle_tok = self.expect_type("IDENTIFIER", "Expected handle name after 'through'")
            return LinearUse(handle_tok.value, 'send', data)

        # --- Phase X: Backend Statements ---
        elif self.match_val("VERB", "start"):
            self.expect_val("KEYWORD", "a", "Expected 'a'")
            self.expect_val("NOUN", "server", "Expected 'server'")
            self.expect_val("CONNECTOR", "on", "Expected 'on'")
            self.expect_val("NOUN", "port", "Expected 'port'")
            port = self.parse_expression()
            from ast_nodes import ServerStart
            return ServerStart(port)

        elif self.match_val("KEYWORD", "when"):
            # UI Event: when [NAME] is [EVENT]:
            # Back-compat: when someone [verb] [path]:
            if self.peek() and self.peek().value == "someone":
                self.consume()
                method_tok = self.consume()
                if method_tok.value not in ["gets", "posts", "puts", "deletes"]:
                    raise ParserError("Expected 'gets', 'posts', 'puts', or 'deletes'")
                method = method_tok.value.upper()[:-1] # GETS -> GET
                path = self.parse_expression()
                self.expect_val("PUNCTUATION", ":", "Expected ':' after route path")
                body = self._parse_block()
                from ast_nodes import RouteHandler
                return RouteHandler(method, path, body)
            else:
                element_name = self.expect_type("IDENTIFIER", "Expected UI element name").value
                self.expect_val("VERB", "is", "Expected 'is' after UI element name")
                event_tok = self.consume()
                if event_tok.value not in ["clicked", "hovered", "changed"]:
                    raise ParserError("Expected 'clicked', 'hovered', or 'changed'")
                self.expect_val("PUNCTUATION", ":", "Expected ':'")
                body = self._parse_block()
                return UIEventHandler(element_name, event_tok.value, body)

        elif self.match_val("VERB", "send"):
            is_json = False
            status_code = 200
            
            if self.match_val("KEYWORD", "with"):
                self.expect_val("NOUN", "status", "Expected 'status'")
                status_code_tok = self.expect_type("LITERAL_NUMBER", "Expected status code")
                status_code = int(status_code_tok.value)
                
            if self.match_val("KEYWORD", "json"):
                is_json = True
                
            val = self.parse_expression()
            
            if self.match_val("CONNECTOR", "through"):
                handle_tok = self.expect_type("IDENTIFIER", "Expected handle name after 'through'")
                return LinearUse(handle_tok.value, 'send', val)
            else:
                from ast_nodes import SendResponse
                return SendResponse(val, is_json, status_code)

        elif self.match_val("VERB", "stop"):
            tok = self.peek()
            if tok and tok.value == "the":
                self.consume()
                self.expect_val("NOUN", "server", "Expected 'server'")
                from ast_nodes import ServerStop
                return ServerStop()
            else:
                from ast_nodes import StopMiddleware
                return StopMiddleware()

        elif self.match_val("VERB", "parse"):
            source = self.parse_expression()
            self.expect_val("KEYWORD", "as", "Expected 'as'")
            self.expect_val("KEYWORD", "json", "Expected 'json'")
            from ast_nodes import JsonParse
            return JsonParse(source)

        elif self.match_val("VERB", "serialize"):
            val = self.parse_expression()
            self.expect_val("KEYWORD", "as", "Expected 'as'")
            self.expect_val("KEYWORD", "json", "Expected 'json'")
            from ast_nodes import JsonSerialize
            return JsonSerialize(val)

        elif self.match_val("VERB", "run"):
            self.expect_val("CONNECTOR", "on", "Expected 'on'")
            db_name = self.expect_type("IDENTIFIER", "Expected db name").value
            self.expect_val("PUNCTUATION", ":", "Expected ':'")
            body = self._parse_block()
            # The body elements will parse as normal AST nodes, but we actually need to intercept "create", "add", "update", "remove" inside DbRun
            from ast_nodes import DatabaseRun
            return DatabaseRun(db_name, body)

        elif self.match_val("VERB", "ask"):
            db_name = self.expect_type("IDENTIFIER", "Expected db name after 'ask'").value
            self.expect_val("KEYWORD", "for", "Expected 'for'")
            
            conditions = None
            if self.match_val("KEYWORD", "all"):
                table = self.expect_type("NOUN", "Expected table name or identifier").value
            else:
                table = self.expect_type("NOUN", "Expected table name").value
                self.expect_val("KEYWORD", "where", "Expected 'where'")
                conditions = self.parse_expression()
            
            from ast_nodes import DatabaseQuery
            return DatabaseQuery(db_name, table, conditions)

        elif self.match_val("KEYWORD", "before"):
            self.expect_val("KEYWORD", "every", "Expected 'every'")
            self.expect_val("NOUN", "request", "Expected 'request'")
            self.expect_val("PUNCTUATION", ":", "Expected ':'")
            body = self._parse_block()
            from ast_nodes import Middleware
            return Middleware('before', body)

        elif self.match_val("KEYWORD", "after"):
            self.expect_val("KEYWORD", "every", "Expected 'every'")
            self.expect_val("NOUN", "response", "Expected 'response'")
            self.expect_val("PUNCTUATION", ":", "Expected ':'")
            body = self._parse_block()
            from ast_nodes import Middleware
            return Middleware('after', body)

        # --- v2: method call pattern: <method_name> <object> ---
        # Handled as identifiers that could be method calls in analyzer
        # Fall through to identifier handling

        raise ParserError(f"I don't understand '{tok.value}' \u2014 did you mean something else?")
    def _parse_block(self):
        body = []
        while self.peek():
            nxt = self.peek()
            if nxt.type == "KEYWORD" and nxt.value in ("when", "before", "after", "define"):
                break
            if nxt.type == "VERB" and nxt.value in ("start", "stop", "open", "close", "add"):
                # Special case: 'add X to the screen' is a top-level UI verb, but 'add X to Y' (list) might be in a block.
                # However, 'add' usually starts a new statement.
                # Let's check if it's 'add X to the screen'
                if nxt.value == "add":
                    # Look ahead: add [expr] to the screen
                    # This is tricky without full expression parsing.
                    # But in Enhanced, blocks are usually terminated by the next major keyword/verb.
                    break
            
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            while self.match_val("PUNCTUATION", ".") or self.match_val("CONNECTOR", "then"):
                pass
        return body

    def _parse_db_operation(self):
        if self.match_val("VERB", "create"):
            self.expect_val("NOUN", "table", "Expected 'table'")
            self.expect_val("KEYWORD", "if", "Expected 'if'")
            self.expect_val("KEYWORD", "not", "Expected 'not'")
            self.expect_val("VERB", "exists", "Expected 'exists'")
            table_name = self.expect_type("IDENTIFIER", "Expected table name").value
            self.expect_val("CONNECTOR", "with", "Expected 'with'")
            fields = []
            while True:
                field_name = self.expect_type("IDENTIFIER", "Expected field name").value
                self.expect_val("KEYWORD", "as", "Expected 'as'")
                field_type_word = self.consume().value
                if field_type_word == "auto" and self.peek() and self.peek().value == "number":
                    self.consume()
                    field_type = "auto number"
                else:
                    field_type = field_type_word
                fields.append((field_name, field_type))
                if not self.match_val("PUNCTUATION", ","):
                    break
            from ast_nodes import DbCreateTable
            return DbCreateTable(table_name, fields)
            
        elif self.match_val("VERB", "add"):
            self.expect_val("CONNECTOR", "to", "Expected 'to'")
            # Could be IDENTIFIER or NOUN
            table_tok = self.consume()
            table = table_tok.value
            values = []
            while self.peek() and self.peek().type in ("IDENTIFIER", "NOUN", "VERB"):
                field = self.consume().value
                if field in ("say", "ask", "run", "open", "close", "send"): # common verbs breaking out
                    self.pos -= 1 # unconsume
                    break
                # The word is a field name
                if self.peek() and self.peek().value == "is":
                    self.expect_val("VERB", "is", "Expected 'is'")
                else:
                    self.pos -=1
                    break
                expr = self.parse_expression()
                values.append((field, expr))
            from ast_nodes import DbInsert
            return DbInsert(table, values)
            
        elif self.match_val("VERB", "update"):
            table_tok = self.consume() # IDENTIFIER or NOUN
            table = table_tok.value
            self.expect_val("VERB", "set", "Expected 'set'")
            field_tok = self.consume()
            field = field_tok.value
            self.expect_val("CONNECTOR", "to", "Expected 'to'")
            expr = self.parse_expression()
            self.expect_val("KEYWORD", "where", "Expected 'where'")
            conditions = self.parse_expression()
            from ast_nodes import DbUpdate
            return DbUpdate(table, [(field, expr)], conditions)
            
        elif self.match_val("VERB", "remove"):
            self.expect_val("CONNECTOR", "from", "Expected 'from'")
            table_tok = self.consume()
            table = table_tok.value
            self.expect_val("KEYWORD", "where", "Expected 'where'")
            conditions = self.parse_expression()
            from ast_nodes import DbDelete
            return DbDelete(table, conditions)

    # ==== v2 Parse Helpers ====

    def _parse_define(self):
        """Parse 'define a <type> as:' for structs, or 'define a <type> as one of:' for enums."""
        article = self.expect_type("KEYWORD", "Expected article after 'define'")
        if article.value not in ("a", "an"):
            raise ParserError(f"Expected 'a' or 'an' after 'define', got '{article.value}'")

        # Read the type name — could be NOUN or IDENTIFIER
        name_tok = self.peek()
        if not name_tok:
            raise ParserError("Expected type name after 'define a'")
        self.consume()
        type_name = name_tok.value

        self.expect_val("KEYWORD", "as", "Expected 'as' after type name")

        # Check for enum: "as one of:"
        if self.match_val("KEYWORD", "one"):
            self.expect_val("CONNECTOR", "of", "Expected 'of' after 'one'")
            self.match_val("PUNCTUATION", ":")
            variants = self._parse_enum_variants()
            return EnumDef(type_name, variants)

        # Struct definition: "as:"
        self.match_val("PUNCTUATION", ":")
        fields = self._parse_struct_fields()
        return StructDef(type_name, fields)

    def _parse_struct_fields(self):
        """Parse struct field list: 'a text called name. a number called age.'"""
        fields = []
        while self.peek() and self.peek().value in ("a", "an"):
            self.consume()  # article
            type_tok = self.peek()
            if not type_tok:
                break
            self.consume()
            field_type_str = type_tok.value
            self.expect_val("VERB", "called", "Expected 'called'")
            name_tok = self.peek()
            if not name_tok:
                break
            self.consume()
            field_name = name_tok.value
            self.match_val("PUNCTUATION", ".")

            # Map English type names to internal types
            type_map = {"number": "int", "text": "str", "truth": "bool"}
            internal_type = type_map.get(field_type_str, field_type_str)
            fields.append(FieldDef(field_name, internal_type))
        return fields

    def _parse_enum_variants(self):
        """Parse enum variant list: 'pending. active. closed.'"""
        variants = []
        while self.peek() and self.peek().type in ("IDENTIFIER", "NOUN", "VERB"):
            tok = self.consume()
            variants.append(tok.value)
            self.match_val("PUNCTUATION", ".")
        return variants

    def _parse_method_def(self):
        """Parse 'to <verb> a <type>:' method definition."""
        self.consume()  # consume 'to'
        # Collect method name words until 'a' or 'an'
        method_words = []
        while self.peek() and self.peek().value not in ("a", "an"):
            tok_word = self.consume()
            # Stop before 'a'/'an' article but also handle 'of' before article
            if tok_word.value == "of" and self.peek() and self.peek().value in ("a", "an"):
                break
            method_words.append(tok_word.value)
        method_name = " ".join(method_words)

        article = self.expect_type("KEYWORD", "Expected article in method definition")
        type_tok = self.peek()
        if not type_tok:
            raise ParserError("Expected type name in method definition")
        self.consume()
        target_type = type_tok.value
        self.match_val("PUNCTUATION", ":")

        # Parse body statements until blank line or next top-level statement
        body = []
        while self.peek():
            # Stop at next 'define', or another 'to' at start
            nxt = self.peek()
            if nxt and nxt.value in ("define",) and nxt.type == "KEYWORD":
                break
            if nxt and nxt.value == "to" and nxt.type == "CONNECTOR":
                # Check if this is a new method def
                if self.peek_at(1) and self.peek_at(1).type in ("VERB", "IDENTIFIER"):
                    break
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            while self.match_val("PUNCTUATION", ".") or self.match_val("CONNECTOR", "then"):
                pass

        return MethodDef(target_type, method_name, [], None, body)

    def _parse_the(self):
        """Parse 'the ...' patterns: variable declarations, sizes, optionals, etc."""
        noun = self.peek()
        if not noun:
            raise ParserError("Expected something after 'the'")

        # Optional declaration: "the optional text called X is nothing"
        if noun.value == "optional":
            self.consume()
            inner_tok = self.peek()
            if not inner_tok:
                raise ParserError("Expected type after 'optional'")
            self.consume()
            type_map = {"number": "int", "text": "str", "truth": "bool"}
            inner_type = type_map.get(inner_tok.value, inner_tok.value)
            self.expect_val("VERB", "called", "Expected 'called'")
            name_tok = self.expect_type("IDENTIFIER", "Expected name")
            self.expect_val("VERB", "is", "Expected 'is'")
            val = self.parse_expression()
            return OptionalDecl(name_tok.value, inner_type, val)

        # Variable decl: "the number X is ..." or "the text X is ..."
        if noun.type == "NOUN" and noun.value in ("number", "text"):
            self.consume()
            name_tok = self.expect_type("IDENTIFIER", f"Expected name after {noun.value}")
            self.expect_val("VERB", "is", f"Expected 'is' after variable name")
            val = self.parse_expression()
            var_type = "int" if noun.value == "number" else "str"
            return VarDecl(var_type, Identifier(name_tok.value), val)

        # Truth variable: "the truth X is ..."
        if noun.type == "NOUN" and noun.value == "truth":
            self.consume()
            # Could be "the truth result is ..." or "the truth X is ..."
            name_tok = self.peek()
            if name_tok and name_tok.type in ("IDENTIFIER", "NOUN"):
                self.consume()
                self.expect_val("VERB", "is", "Expected 'is'")
                val = self.parse_expression()
                return VarDecl("bool", Identifier(name_tok.value), val)
            raise ParserError("Expected variable name after 'the truth'")

        # Enum variable: "the <enum_type> X is <variant>"
        # This is handled when the noun is an IDENTIFIER (custom type name)
        if noun.type == "IDENTIFIER":
            saved_pos = self.pos
            self.consume()
            next_tok = self.peek()
            if next_tok and next_tok.type == "IDENTIFIER":
                var_name_tok = self.consume()
                if self.match_val("VERB", "is"):
                    val = self.parse_expression()
                    return VarDecl(noun.value, Identifier(var_name_tok.value), val)
                self.pos = saved_pos
            else:
                self.pos = saved_pos

        # Fall through to expression parsing (the size of, the remainder of, etc.)
        self.consume()
        return self._parse_the_expression(noun)

    def _parse_the_expression(self, noun):
        """Parse 'the X' expressions after consuming noun."""
        if noun.value == "remainder":
            self.expect_val("CONNECTOR", "of", "Expected 'of'")
            left = self.parse_expression()
            self.expect_val("VERB", "divided", "Expected 'divided'")
            self.expect_val("CONNECTOR", "by", "Expected 'by'")
            right = self.parse_expression()
            return BinaryOp("%", left, right)

        elif noun.value == "absolute":
            self.expect_val("NOUN", "value", "Expected 'value'")
            self.expect_val("CONNECTOR", "of", "Expected 'of'")
            val = self.parse_expression()
            return UnaryOp("abs", val)

        elif noun.value == "size":
            self.expect_val("CONNECTOR", "of", "Expected 'of'")
            expr = self.parse_expression()
            return ListSize(expr)

        elif noun.value == "first":
            self.expect_val("NOUN", "item", "Expected 'item'")
            self.expect_val("KEYWORD", "in", "Expected 'in'")
            list_expr = self.parse_expression()
            return ListGet(list_expr, 0)

        elif noun.value == "last":
            self.expect_val("NOUN", "item", "Expected 'item'")
            self.expect_val("KEYWORD", "in", "Expected 'in'")
            list_expr = self.parse_expression()
            return ListGet(list_expr, -1)

        elif noun.value == "current":
            self.expect_val("NOUN", "timestamp", "Expected 'timestamp'")
            return Timestamp()

        elif noun.value == "response":
            self.expect_val("NOUN", "body", "Expected 'body'")
            from ast_nodes import HttpResponseBody
            return HttpResponseBody()

        elif noun.value == "request":
            next_tok = self.peek()
            if next_tok and next_tok.value == "body":
                self.consume()
                from ast_nodes import GetRequestBody
                return GetRequestBody()
            elif next_tok and next_tok.value == "header":
                self.consume()
                name_tok = self.expect_type("LITERAL_STRING", "Expected request header name")
                from ast_nodes import GetRequestHeader
                return GetRequestHeader(name_tok.value.strip('"'))
            else:
                raise ParserError("Expected 'body' or 'header' after 'request'")

        elif noun.value == "url":
            self.expect_val("NOUN", "param", "Expected 'param' after 'url'")
            name_tok = self.expect_type("LITERAL_STRING", "Expected param name")
            from ast_nodes import GetUrlParam
            return GetUrlParam(name_tok.value.strip('"'))

        elif noun.value == "query":
            self.expect_val("NOUN", "param", "Expected 'param' after 'query'")
            name_tok = self.expect_type("LITERAL_STRING", "Expected param name")
            from ast_nodes import GetQueryParam
            return GetQueryParam(name_tok.value.strip('"'))

        elif noun.value == "environment":
            self.expect_val("NOUN", "variable", "Expected 'variable'")
            name_tok = self.expect_type("LITERAL_STRING", "Expected env var name")
            from ast_nodes import GetEnvVar
            return GetEnvVar(name_tok.value.strip('"'))

        else:
            return Identifier(noun.value)

    def _parse_if(self):
        """Parse if statement with various conditions."""
        # Check for: 'if X has a value' (OptionalCheck)
        saved_pos = self.pos
        first = self.peek()
        if first and first.type == "IDENTIFIER":
            self.consume()
            if self.match_val("VERB", "has"):
                if self.match_val("KEYWORD", "a"):
                    if self.match_val("NOUN", "value"):
                        self.match_val("PUNCTUATION", ":")
                        body_stmt = self.parse_statement()
                        check_node = OptionalCheck(first.value)
                        check_node.line = first.line
                        return IfStatement(check_node, [body_stmt])
            self.pos = saved_pos

        # Check for: 'if X is <variant>' (enum check) or 'if X is still valid' (genref)
        if first and first.type == "IDENTIFIER":
            self.consume()
            if self.match_val("VERB", "is"):
                # GenRefCheck: 'still valid'
                if self.match_val("KEYWORD", "still"):
                    self.expect_val("KEYWORD", "valid", "Expected 'valid'")
                    self.match_val("PUNCTUATION", ":")
                    body_stmt = self.parse_statement()
                    return IfStatement(GenRefCheck(first.value), [body_stmt])
                # 'greater than'
                if self.match_val("KEYWORD", "greater"):
                    self.expect_val("KEYWORD", "than", "Expected 'than'")
                    right = self.parse_expression()
                    body_stmt = self.parse_statement()
                    return IfStatement(GT(Identifier(first.value), right), [body_stmt])
                # 'greater than or equal to'
                # 'in Y' (list contains)
                if self.match_val("KEYWORD", "in"):
                    list_expr = self.parse_expression()
                    self.match_val("PUNCTUATION", ":")
                    body_stmt = self.parse_statement()
                    return IfStatement(ListContains(list_expr, Identifier(first.value)), [body_stmt])
                # Enum check: 'if X is <variant>'
                variant_tok = self.peek()
                if variant_tok and variant_tok.type in ("IDENTIFIER", "NOUN", "VERB"):
                    self.consume()
                    self.match_val("PUNCTUATION", ":")
                    body_stmt = self.parse_statement()
                    return IfStatement(EnumCheck(first.value, variant_tok.value), [body_stmt])
            self.pos = saved_pos

        # 'if the file X exists'
        if self.peek() and self.peek().value == "the" and self.peek_at(1) and self.peek_at(1).value == "file":
            self.consume()
            self.consume()
            path = self.parse_expression()
            self.expect_val("VERB", "exists", "Expected 'exists'")
            self.match_val("PUNCTUATION", ":")
            body_stmt = self.parse_statement()
            return IfStatement(FileExists(path), [body_stmt])

        # Generic: if <expr> greater than <expr>
        left = self.parse_expression()
        if self.match_val("VERB", "is"):
            self.expect_val("KEYWORD", "greater", "Expected 'greater'")
            self.expect_val("KEYWORD", "than", "Expected 'than'")
            right = self.parse_expression()
            body_stmt = self.parse_statement()
            return IfStatement(GT(left, right), [body_stmt])

        # Simple if <expr>:
        self.match_val("PUNCTUATION", ":")
        body_stmt = self.parse_statement()
        return IfStatement(left, [body_stmt])

    def _parse_create_legacy(self, article):
        """Parse legacy 'create' statements (list, map, heap alloc, struct init)."""
        # 'create a new <type> called <name>' → StructInit or HeapAlloc
        if self.match_val("KEYWORD", "new"):
            type_tok = self.peek()
            if not type_tok:
                raise ParserError("Expected type name after 'new'")
            self.consume()
            self.expect_val("VERB", "called", "Expected 'called'")
            name_tok = self.expect_type("IDENTIFIER", "Expected variable name")
            return StructInit(type_tok.value, name_tok.value)

        # 'create a map ...'
        if self.match_val("NOUN", "map"):
            return self._parse_map_decl()

        # 'create a list ...'
        self.expect_val("NOUN", "list", "Expected 'list'")
        element_type = None
        if self.match_val("CONNECTOR", "of"):
            # Typed list: 'create a list of <type> called ...'
            type_tok = self.peek()
            if type_tok:
                self.consume()
                type_map = {"numbers": "int", "texts": "str", "truths": "bool",
                            "names": "str", "persons": "person", "products": "product"}
                element_type = type_map.get(type_tok.value, type_tok.value)
        self.expect_val("VERB", "called", "Expected 'called'")
        name_tok = self.peek()
        if name_tok and name_tok.type in ("IDENTIFIER", "NOUN"):
            self.consume()
        else:
            raise ParserError(f"Expected list name. Got {name_tok.type}('{name_tok.value}')" if name_tok else "Expected list name")
        node = ListDecl(Identifier(name_tok.value))
        node.element_type = element_type
        return node

    def _parse_map_decl(self):
        """Parse map declaration after 'create a map'."""
        key_type = None
        val_type = None
        if self.match_val("CONNECTOR", "of"):
            # 'of texts to numbers'
            kt = self.peek()
            if kt:
                self.consume()
                type_map = {"numbers": "int", "texts": "str", "truths": "bool"}
                key_type = type_map.get(kt.value, kt.value)
            self.expect_val("CONNECTOR", "to", "Expected 'to'")
            vt = self.peek()
            if vt:
                self.consume()
                val_type = type_map.get(vt.value, vt.value)
        self.expect_val("VERB", "called", "Expected 'called'")
        name_tok = self.expect_type("IDENTIFIER", "Expected map name")
        return MapDecl(name_tok.value, key_type, val_type)

    def _parse_set_legacy(self, first_expr):
        """Handle legacy set patterns for compatibility."""
        # Check for possessive: set alice's name to "Alice"
        if isinstance(first_expr, Identifier) and self.peek() and self.peek().type == "POSSESSIVE":
            self.consume() # consume 's
            field_name_tok = self.expect_type("IDENTIFIER", "Expected field name")
            field_path = [field_name_tok.value]
            while self.peek() and self.peek().type == "POSSESSIVE":
                self.consume()
                next_field_tok = self.expect_type("IDENTIFIER", "Expected field name")
                field_path.append(next_field_tok.value)
            self.expect_val("CONNECTOR", "to", "Expected 'to'")
            val = self.parse_expression()
            return FieldSet(first_expr.name, field_path, val)
        
        # Simple variable update: set X to 10.
        if isinstance(first_expr, Identifier):
            self.expect_val("CONNECTOR", "to", "Expected 'to'")
            val = self.parse_expression()
            # We map this to VarDecl with 'any' type to represent reassignment
            return VarDecl("any", first_expr, val)
            
        raise ParserError(f"Unexpected expression after 'set'")
        var_name = "_".join(var_parts)
        return VarDecl("any", Identifier(var_name), val)

    def _parse_read(self):
        """Parse 'read' statements."""
        if self.peek() and self.peek().value == "from":
            self.consume()
            handle_tok = self.expect_type("IDENTIFIER", "Expected handle name after 'read from'")
            return LinearUse(handle_tok.value, 'read')
        self.expect_val("KEYWORD", "the", "Expected 'the'")
        self.expect_val("NOUN", "file", "Expected 'file'")
        path = self.parse_expression()
        return FileRead(path)

    def _parse_check_if(self):
        """Parse 'check if ...' patterns."""
        # 'check if "Alice" is in scores'
        # 'check if X is still valid'
        # 'check if the file X exists'
        # 'check if X has a value' (optional)

        if self.peek() and self.peek().value == "the" and self.peek_at(1) and self.peek_at(1).value == "file":
            self.consume()
            self.consume()
            path = self.parse_expression()
            self.expect_val("VERB", "exists", "Expected 'exists'")
            return FileExists(path)

        name_tok = self.peek()
        if name_tok and name_tok.type == "IDENTIFIER":
            saved_pos = self.pos
            self.consume()
            # OptionalCheck: 'X has a value'
            if self.match_val("VERB", "has"):
                if self.match_val("KEYWORD", "a"):
                    if self.match_val("NOUN", "value"):
                        return OptionalCheck(name_tok.value)
            # GenRefCheck: 'X is still valid'
            if self.match_val("VERB", "is") and self.match_val("KEYWORD", "still") and self.match_val("KEYWORD", "valid"):
                return GenRefCheck(name_tok.value)
            self.pos = saved_pos

        # ListContains: 'X is in Y'
        val = self.parse_expression()
        self.expect_val("VERB", "is", "Expected 'is'")
        self.expect_val("KEYWORD", "in", "Expected 'in'")
        list_expr = self.parse_expression()
        return ListContains(list_expr, val)

    # ==== Expression Parsing ====

    def parse_expression(self):
        tok = self.peek()
        if not tok:
            raise ParserError("Expected expression but found end of file")
        line = tok.line
        expr = self._parse_primary()
        if expr:
            expr.line = line

        # [expression] in [expression]
        # Only parse 'in' if it's NOT followed by 'to' (which would be a 'set ... in ... to' statement)
        if self.peek() and self.peek().value == "in":
            if not (self.peek_at(2) and self.peek_at(2).value == "to"):
                self.consume() # in
                collection = self._parse_primary()
                if isinstance(collection, Identifier):
                    expr = MapGet(collection.name, expr)
                else:
                    expr = ListContains(collection, expr)
                expr.line = line

        while self.peek() and self.peek().type == "CONNECTOR" and self.peek().value == "to":
            if self.pos + 3 < len(self.tokens) and \
               self.tokens[self.pos+1].value == "the" and \
               self.tokens[self.pos+2].value == "power" and \
               self.tokens[self.pos+3].value == "of":
                self.consume()
                self.consume()
                self.consume()
                self.consume()
                right = self._parse_primary()
                expr = BinaryOp("pow", expr, right)
                expr.line = line
            else:
                break
        return expr

        # generic [expression] in [expression] as a primary access pattern
        return self._parse_primary_inner()

    def _parse_primary(self):
        return self._parse_primary_inner()

    def _parse_primary_inner(self):
        tok = self.peek()
        if not tok:
            raise ParserError("Expected expression but found end of file")

        if tok.type == "LITERAL_NUMBER":
            self.consume()
            return LiteralNumber(int(tok.value))

        elif tok.type == "LITERAL_STRING":
            self.consume()
            return LiteralString(tok.value)

        elif tok.type == "LITERAL_BOOL":
            self.consume()
            return LiteralBool(tok.value == "true")

        elif tok.type == "LITERAL_NOTHING":
            self.consume()
            return LiteralBool(None)  # represents 'nothing'

        elif tok.type == "KEYWORD" and tok.value == "the":
            self.consume()
            noun = self.peek()
            if not noun:
                raise ParserError("Expected noun after 'the'")
            # Check: 'the rectangle's width' → FieldGet
            if noun.type in ("IDENTIFIER", "NOUN"):
                saved_pos = self.pos
                self.consume()
                if self.peek() and self.peek().type == "POSSESSIVE":
                    self.consume()  # consume 's
                    field_path = []
                    f = self.peek()
                    if f:
                        self.consume()
                        field_path.append(f.value)
                    while self.peek() and self.peek().type == "POSSESSIVE":
                        self.consume()
                        f2 = self.peek()
                        if f2:
                            self.consume()
                            field_path.append(f2.value)
                    return FieldGet(noun.value, field_path)
                self.pos = saved_pos
            self.consume()  # consume the noun
            return self._parse_the_expression(noun)

        elif tok.type == "KEYWORD" and tok.value == "null":
            self.consume()
            return LiteralNumber(0)

        elif tok.type == "IDENTIFIER":
            self.consume()
            # Check for possessive field access: alice's name
            if self.peek() and self.peek().type == "POSSESSIVE":
                self.consume()  # consume 's
                field_path = []
                f = self.peek()
                if f:
                    self.consume()
                    field_path.append(f.value)
                while self.peek() and self.peek().type == "POSSESSIVE":
                    self.consume()
                    f2 = self.peek()
                    if f2:
                        self.consume()
                        field_path.append(f2.value)
                return FieldGet(tok.value, field_path)

            return Identifier(tok.value)

        elif tok.type == "NOUN":
            self.consume()
            return Identifier(tok.value)

        elif tok.type == "VERB":
            verb_val = tok.value
            saved_pos = self.pos
            self.consume()
            
            method_words = [verb_val]
            while self.peek() and self.peek().value != "of" and self.peek().type not in ("PUNCTUATION", "CONNECTOR"):
                method_words.append(self.consume().value)
                
            if self.match_val("CONNECTOR", "of"):
                method_name = " ".join(method_words)
                target_expr = self._parse_primary()
                obj_name = target_expr.name if getattr(target_expr, 'name', None) else "unknown"
                return MethodCall(obj_name, method_name, [])
                
            self.pos = saved_pos
            return Identifier(tok.value)

        raise ParserError(f"Expected expression, got {tok.type} '{tok.value}'")
