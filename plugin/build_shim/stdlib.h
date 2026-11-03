#pragma once
#include <stddef.h>
extern "C" {
__declspec(dllimport) double __cdecl atof(const char*);
__declspec(dllimport) void* __cdecl malloc(size_t);
__declspec(dllimport) void __cdecl free(void*);
}
