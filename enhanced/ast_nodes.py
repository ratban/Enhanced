import json

class ASTNode:
    def __init__(self):
        self.line = 0
        self.value_type = None

    def to_dict(self):
        result = {}
        result['type'] = self.__class__.__name__
        if hasattr(self, 'value_type') and self.value_type is not None:
            result['value_type'] = str(self.value_type)
        
        for k, v in self.__dict__.items():
            if k in ('line', 'value_type'):
                continue
            if isinstance(v, ASTNode):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [item.to_dict() if isinstance(item, ASTNode) else item for item in v]
            else:
                result[k] = v
        return result

class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

class PrintStatement(ASTNode):
    def __init__(self, value):
        self.value = value

class VarDecl(ASTNode):
    def __init__(self, var_type, name, value):
        self.var_type = var_type
        self.name = name
        self.value = value

class BinaryOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

class ForLoop(ASTNode):
    def __init__(self, item, collection, body):
        self.item = item
        self.collection = collection
        self.body = body

class IfStatement(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class ListDecl(ASTNode):
    def __init__(self, name):
        self.name = name

class ListAppend(ASTNode):
    def __init__(self, list_name, value):
        self.list_name = list_name
        self.value = value

class Identifier(ASTNode):
    def __init__(self, name):
        self.name = name

class LiteralNumber(ASTNode):
    def __init__(self, value):
        self.value = value

class LiteralString(ASTNode):
    def __init__(self, value):
        self.value = value

class GT(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

# Phase V Output Nodes
class FileRead(ASTNode):
    def __init__(self, path):
        self.path = path

class FileWrite(ASTNode):
    def __init__(self, path, content):
        self.path = path
        self.content = content

class FileAppend(ASTNode):
    def __init__(self, path, content):
        self.path = path
        self.content = content

class FileExists(ASTNode):
    def __init__(self, path):
        self.path = path

class UnaryOp(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

class ListSize(ASTNode):
    def __init__(self, list_name):
        self.list_name = list_name

class ListGet(ASTNode):
    def __init__(self, list_name, index):
        self.list_name = list_name
        self.index = index  # 0 for first, -1 for last

class ListRemove(ASTNode):
    def __init__(self, list_name, value):
        self.list_name = list_name
        self.value = value

class ListContains(ASTNode):
    def __init__(self, list_name, value):
        self.list_name = list_name
        self.value = value

class ListSort(ASTNode):
    def __init__(self, list_name):
        self.list_name = list_name

class Sleep(ASTNode):
    def __init__(self, ms):
        self.ms = ms

class Timestamp(ASTNode):
    def __init__(self):
        pass

class HttpGet(ASTNode):
    def __init__(self, url):
        self.url = url

class HttpResponseBody(ASTNode):
    def __init__(self):
        pass

class LoadLibrary(ASTNode):
    def __init__(self, library_name):
        self.library_name = library_name

class FFICall(ASTNode):
    def __init__(self, func_name, args):
        self.func_name = func_name
        self.args = args

# Phase VI Memory Safety Nodes

class HeapAlloc(ASTNode):
    def __init__(self, alloc_type, name):
        self.alloc_type = alloc_type  # e.g. "person", "user"
        self.name = name             # variable name string

class HeapFree(ASTNode):
    def __init__(self, name):
        self.name = name

class GenRefCheck(ASTNode):
    def __init__(self, name):
        self.name = name

class LinearOpen(ASTNode):
    def __init__(self, resource_type, path, name):
        self.resource_type = resource_type  # 'file', 'socket'
        self.path = path                     # expression for the path/address
        self.name = name                     # handle variable name

class LinearUse(ASTNode):
    def __init__(self, name, op, value=None):
        self.name = name    # handle name
        self.op = op        # 'read', 'write', 'send'
        self.value = value  # data to write/send (None for read)

class LinearConsume(ASTNode):
    def __init__(self, name):
        self.name = name

# Phase v2 — Custom Types, Generics, Methods, Maps, Optionals, Enums

class StructDef(ASTNode):
    def __init__(self, name, fields):
        self.name = name           # string
        self.fields = fields       # list of FieldDef

class FieldDef(ASTNode):
    def __init__(self, name, field_type):
        self.name = name           # string
        self.field_type = field_type  # string: 'int', 'str', 'bool', or struct name

class StructInit(ASTNode):
    def __init__(self, struct_type, name):
        self.struct_type = struct_type  # string
        self.name = name               # string

class FieldSet(ASTNode):
    def __init__(self, object_name, field_path, value):
        self.object_name = object_name  # string
        self.field_path = field_path    # list of strings e.g. ['name'] or ['profile','name']
        self.value = value              # ASTNode

class FieldGet(ASTNode):
    def __init__(self, object_name, field_path):
        self.object_name = object_name
        self.field_path = field_path    # list of strings

class MethodDef(ASTNode):
    def __init__(self, target_type, name, params, return_type, body):
        self.target_type = target_type  # string — struct type name
        self.name = name                # string — method name
        self.params = params            # list of param info
        self.return_type = return_type  # string or None
        self.body = body                # list of ASTNode

class MethodCall(ASTNode):
    def __init__(self, object_name, method_name, args):
        self.object_name = object_name
        self.method_name = method_name
        self.args = args                # list of ASTNode

class Return(ASTNode):
    def __init__(self, value):
        self.value = value

class MapDecl(ASTNode):
    def __init__(self, name, key_type=None, value_type=None):
        self.name = name
        self.key_type = key_type
        self.value_type_decl = value_type

class MapSet(ASTNode):
    def __init__(self, map_name, key, value):
        self.map_name = map_name
        self.key = key
        self.value = value

class MapGet(ASTNode):
    def __init__(self, map_name, key):
        self.map_name = map_name
        self.key = key

class MapContains(ASTNode):
    def __init__(self, map_name, key):
        self.map_name = map_name
        self.key = key

class MapRemove(ASTNode):
    def __init__(self, map_name, key):
        self.map_name = map_name
        self.key = key

class MapSize(ASTNode):
    def __init__(self, map_name):
        self.map_name = map_name

class OptionalDecl(ASTNode):
    def __init__(self, name, inner_type, value=None):
        self.name = name
        self.inner_type = inner_type
        self.value = value

class OptionalCheck(ASTNode):
    def __init__(self, name):
        self.name = name

class OptionalUnwrap(ASTNode):
    def __init__(self, name):
        self.name = name

class EnumDef(ASTNode):
    def __init__(self, name, variants):
        self.name = name
        self.variants = variants  # list of strings

class EnumValue(ASTNode):
    def __init__(self, enum_type, variant):
        self.enum_type = enum_type
        self.variant = variant

class EnumCheck(ASTNode):
    def __init__(self, variable, variant):
        self.variable = variable
        self.variant = variant

class LiteralBool(ASTNode):
    def __init__(self, value):
        self.value = value  # True or False

class OtherwiseBlock(ASTNode):
    def __init__(self, body):
        self.body = body

# --- Phase X: Backend Stack ---

# HTTP Server
class ServerStart(ASTNode):
    def __init__(self, port):
        super().__init__()
        self.port = port

class RouteHandler(ASTNode):
    def __init__(self, method, path, body):
        super().__init__()
        self.method = method  # "GET", "POST", "PUT", "DELETE"
        self.path = path
        self.body = body

class SendResponse(ASTNode):
    def __init__(self, value, is_json=False, status_code=200):
        super().__init__()
        self.value = value
        self.is_json = is_json
        self.status_code = status_code

class GetRequestBody(ASTNode):
    def __init__(self):
        super().__init__()

class GetUrlParam(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

class GetQueryParam(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

class GetRequestHeader(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

class ServerStop(ASTNode):
    def __init__(self):
        super().__init__()

# JSON
class JsonParse(ASTNode):
    def __init__(self, source):
        super().__init__()
        self.source = source

class JsonSerialize(ASTNode):
    def __init__(self, value):
        super().__init__()
        self.value = value

# Database
class DatabaseOpen(ASTNode):
    def __init__(self, path, name):
        super().__init__()
        self.path = path
        self.name = name

class DatabaseClose(ASTNode):
    def __init__(self, db_name):
        super().__init__()
        self.db_name = db_name

class DatabaseRun(ASTNode):
    def __init__(self, db_name, operation):
        super().__init__()
        self.db_name = db_name
        self.operation = operation

class DatabaseQuery(ASTNode):
    def __init__(self, db_name, table, conditions=None):
        super().__init__()
        self.db_name = db_name
        self.table = table
        self.conditions = conditions # None means 'all'

# Database Operations for DatabaseRun
class DbCreateTable(ASTNode):
    def __init__(self, table, fields):
        super().__init__()
        self.table = table
        self.fields = fields # list of (name, type)

class DbInsert(ASTNode):
    def __init__(self, table, values):
        super().__init__()
        self.table = table
        self.values = values # list of (field, expr_node)

class DbUpdate(ASTNode):
    def __init__(self, table, sets, conditions):
        super().__init__()
        self.table = table
        self.sets = sets # list of (field, expr_node)
        self.conditions = conditions

class DbDelete(ASTNode):
    def __init__(self, table, conditions):
        super().__init__()
        self.table = table
        self.conditions = conditions

# Middleware
class Middleware(ASTNode):
    def __init__(self, timing, body):
        super().__init__()
        self.timing = timing # "before" or "after"
        self.body = body

class StopMiddleware(ASTNode):
    def __init__(self):
        super().__init__()

# Environment Variables
class GetEnvVar(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

# --- Phase XII: UI Framework ---
class UICreateElement(ASTNode):
    def __init__(self, element_type, name):
        super().__init__()
        self.element_type = element_type # 'button', 'text', 'input', 'box'
        self.name = name

class UISetProperty(ASTNode):
    def __init__(self, element_name, property_name, value):
        super().__init__()
        self.element_name = element_name
        self.property_name = property_name # 'text', 'color'
        self.value = value

class UIEventHandler(ASTNode):
    def __init__(self, element_name, event_type, body):
        super().__init__()
        self.element_name = element_name
        self.event_type = event_type # 'clicked', 'hovered', 'changed'
        self.body = body

class UIAddToScreen(ASTNode):
    def __init__(self, element_name):
        super().__init__()
        self.element_name = element_name

# --- Phase XIII: Package Manager ---
class UsePackage(ASTNode):
    def __init__(self, package_name, module_name=None, version=None, source=None):
        super().__init__()
        self.package_name = package_name
        self.module_name = module_name
        self.version = version
        self.source = source

class Manifest(ASTNode):
    def __init__(self, package_name, version, author, dependencies):
        super().__init__()
        self.package_name = package_name
        self.version = version
        self.author = author
        self.dependencies = dependencies # List of UsePackage nodes

class GetPackage(ASTNode):
    def __init__(self, package_name):
        super().__init__()
        self.package_name = package_name

class PublishPackage(ASTNode):
    def __init__(self):
        super().__init__()

class FunctionCall(ASTNode):
    def __init__(self, target, args):
        super().__init__()
        self.target = target  # Can be an Identifier or FieldGet
        self.args = args      # list of ASTNode


