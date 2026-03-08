; LLVM IR for Enhanced Language (WebAssembly Target)
target datalayout = "e-m:e-p:32:32-i64:64-n32:64-S128"
target triple = "wasm32-unknown-unknown"

declare void @enhanced_print_str(i8*)
declare void @enhanced_print_int(i32)
declare void @enhanced_print_bool(i32)
declare {i64, i64} @enhanced_alloc(i64)
declare void @enhanced_free({i64, i64})
declare i8* @enhanced_deref({i64, i64})
declare i32 @enhanced_is_valid({i64, i64})
@str_0 = private unnamed_addr constant [8 x i8] c"test.db\00", align 1

define i32 @main() {
entry:
    ; DatabaseOpen
    %mydb = call i8* @enhanced_db_open(i8* getelementptr inbounds ([8 x i8], [8 x i8]* @str_0, i32 0, i32 0))
    ; LinearConsume 'mydb'
    %mydb_lv = load i8*, i8** %mydb
    call void @enhanced_close_file(i8* %mydb_lv)
    ret i32 0
}