#pragma once
#include <stddef.h>
extern "C" {
__declspec(dllimport) int __cdecl _stricmp(const char*, const char*);
__declspec(dllimport) char* __cdecl strstr(const char*, const char*);
__declspec(dllimport) char* __cdecl strrchr(const char*, int);
__declspec(dllimport) char* __cdecl strcpy(char*, const char*);
__declspec(dllimport) char* __cdecl strcat(char*, const char*);
__declspec(dllimport) char* __cdecl strncpy(char*, const char*, size_t);
__declspec(dllimport) int __cdecl strcmp(const char*, const char*);
__declspec(dllimport) int __cdecl strncmp(const char*, const char*, size_t);
__declspec(dllimport) size_t __cdecl strlen(const char*);
// memcpy/memset/memcmp are also emitted implicitly by the compiler, so they are linked through the import thunk
int __cdecl memcmp(const void*, const void*, size_t);
void* __cdecl memcpy(void*, const void*, size_t);
void* __cdecl memset(void*, int, size_t);
}
