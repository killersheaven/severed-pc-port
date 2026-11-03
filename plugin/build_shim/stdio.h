#pragma once
#include <stddef.h>
#include <stdarg.h>
typedef struct _iobuf FILE;
extern "C" {
__declspec(dllimport) FILE* __cdecl fopen(const char*, const char*);
__declspec(dllimport) int __cdecl fclose(FILE*);
__declspec(dllimport) int __cdecl fputc(int, FILE*);
__declspec(dllimport) int __cdecl fputs(const char*, FILE*);
__declspec(dllimport) size_t __cdecl fwrite(const void*, size_t, size_t, FILE*);
__declspec(dllimport) int __cdecl __stdio_common_vfprintf(unsigned long long, FILE*, const char*, void*, va_list);
__declspec(dllimport) int __cdecl __stdio_common_vsprintf(unsigned long long, char*, size_t, const char*, void*, va_list);
}
// UCRT: _CRT_INTERNAL_PRINTF_STANDARD_SNPRINTF_BEHAVIOR = 2
static inline int vfprintf(FILE* f, const char* fmt, va_list ap) { return __stdio_common_vfprintf(0, f, fmt, nullptr, ap); }
static inline int fprintf(FILE* f, const char* fmt, ...) { va_list ap; va_start(ap, fmt); int r = vfprintf(f, fmt, ap); va_end(ap); return r; }
static inline int vsnprintf(char* b, size_t n, const char* fmt, va_list ap) { int r = __stdio_common_vsprintf(2, b, n, fmt, nullptr, ap); return r < 0 ? -1 : r; }
static inline int snprintf(char* b, size_t n, const char* fmt, ...) { va_list ap; va_start(ap, fmt); int r = vsnprintf(b, n, fmt, ap); va_end(ap); return r; }
static inline int sprintf(char* b, const char* fmt, ...) { va_list ap; va_start(ap, fmt); int r = __stdio_common_vsprintf(0, b, (size_t)-1, fmt, nullptr, ap); va_end(ap); return r < 0 ? -1 : r; }
