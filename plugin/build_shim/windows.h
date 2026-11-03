// Minimal Win32 shim (i686) for building SeveredLoader without a Windows SDK.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#define WINAPI __stdcall
#define CALLBACK __stdcall
#define STDMETHODCALLTYPE __stdcall
#define TRUE 1
#define FALSE 0
#define MAX_PATH 260
typedef unsigned long DWORD; typedef long LONG; typedef unsigned long ULONG; typedef int BOOL; typedef unsigned int UINT;
typedef int INT; typedef unsigned short WORD; typedef unsigned char BYTE; typedef void* LPVOID; typedef void* PVOID;
typedef const char* LPCSTR; typedef char* LPSTR; typedef long HRESULT; typedef uintptr_t ULONG_PTR; typedef size_t SIZE_T;
typedef void* HANDLE; typedef struct HINSTANCE__* HINSTANCE; typedef HINSTANCE HMODULE; typedef struct HWND__* HWND;
typedef struct HMENU__* HMENU; typedef struct HICON__* HICON; typedef HICON HCURSOR; typedef struct HBRUSH__* HBRUSH;
typedef uintptr_t WPARAM; typedef intptr_t LPARAM; typedef intptr_t LRESULT; typedef unsigned short ATOM; typedef short SHORT;
typedef void* FARPROC;
#define FAILED(hr) (((HRESULT)(hr)) < 0)
#define SUCCEEDED(hr) (((HRESULT)(hr)) >= 0)
typedef struct { LONG left, top, right, bottom; } RECT;
typedef struct { DWORD dwSize, iType, nCount, nRgnSize; RECT rcBound; char Buffer[1]; } RGNDATA;
typedef struct { WORD wYear, wMonth, wDayOfWeek, wDay, wHour, wMinute, wSecond, wMilliseconds; } SYSTEMTIME;
typedef struct { PVOID BaseAddress; PVOID AllocationBase; DWORD AllocationProtect; SIZE_T RegionSize; DWORD State, Protect, Type; } MEMORY_BASIC_INFORMATION;
typedef struct { PVOID DebugInfo; LONG LockCount, RecursionCount; HANDLE OwningThread, LockSemaphore; ULONG_PTR SpinCount; } CRITICAL_SECTION;
typedef struct { DWORD ControlWord, StatusWord, TagWord, ErrorOffset, ErrorSelector, DataOffset, DataSelector; BYTE RegisterArea[80]; DWORD Cr0NpxState; } FLOATING_SAVE_AREA;
typedef struct _CONTEXT {
    DWORD ContextFlags, Dr0, Dr1, Dr2, Dr3, Dr6, Dr7; FLOATING_SAVE_AREA FloatSave;
    DWORD SegGs, SegFs, SegEs, SegDs, Edi, Esi, Ebx, Edx, Ecx, Eax, Ebp, Eip, SegCs, EFlags, Esp, SegSs;
    BYTE ExtendedRegisters[512];
} CONTEXT;
static_assert(offsetof(CONTEXT, Eax) == 0xB0 && offsetof(CONTEXT, Eip) == 0xB8 && offsetof(CONTEXT, Esp) == 0xC4 && sizeof(CONTEXT) == 0x2CC, "CONTEXT layout");
typedef struct _EXCEPTION_RECORD { DWORD ExceptionCode, ExceptionFlags; struct _EXCEPTION_RECORD* ExceptionRecord; PVOID ExceptionAddress; DWORD NumberParameters; ULONG_PTR ExceptionInformation[15]; } EXCEPTION_RECORD;
typedef struct { EXCEPTION_RECORD* ExceptionRecord; CONTEXT* ContextRecord; } EXCEPTION_POINTERS;
static_assert(sizeof(MEMORY_BASIC_INFORMATION) == 28 && sizeof(CRITICAL_SECTION) == 24 && sizeof(SYSTEMTIME) == 16 && sizeof(EXCEPTION_RECORD) == 80, "layouts");
typedef LONG (WINAPI *PVECTORED_EXCEPTION_HANDLER)(EXCEPTION_POINTERS*);
typedef LONG (WINAPI *LPTOP_LEVEL_EXCEPTION_FILTER)(EXCEPTION_POINTERS*);
typedef DWORD (WINAPI *LPTHREAD_START_ROUTINE)(LPVOID);
typedef LRESULT (CALLBACK *WNDPROC)(HWND, UINT, WPARAM, LPARAM);
typedef struct { UINT style; WNDPROC lpfnWndProc; int cbClsExtra, cbWndExtra; HINSTANCE hInstance; HICON hIcon; HCURSOR hCursor; HBRUSH hbrBackground; LPCSTR lpszMenuName, lpszClassName; } WNDCLASSA;
#define MEM_COMMIT 0x1000
#define MEM_RESERVE 0x2000
#define PAGE_NOACCESS 0x01
#define PAGE_GUARD 0x100
#define PAGE_EXECUTE_READWRITE 0x40
#define VK_F9 0x78
#define VK_F10 0x79
#define GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT 0x2
#define GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS 0x4
#define EXCEPTION_ACCESS_VIOLATION 0xC0000005UL
#define EXCEPTION_ARRAY_BOUNDS_EXCEEDED 0xC000008CUL
#define EXCEPTION_INT_DIVIDE_BY_ZERO 0xC0000094UL
#define EXCEPTION_PRIV_INSTRUCTION 0xC0000096UL
#define EXCEPTION_ILLEGAL_INSTRUCTION 0xC000001DUL
#define EXCEPTION_STACK_OVERFLOW 0xC00000FDUL
#define EXCEPTION_CONTINUE_SEARCH 0
#define DLL_PROCESS_ATTACH 1
#define WS_OVERLAPPEDWINDOW 0x00CF0000L
extern "C" {
__declspec(dllimport) PVOID WINAPI AddVectoredExceptionHandler(ULONG, PVECTORED_EXCEPTION_HANDLER);
__declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);
__declspec(dllimport) HANDLE WINAPI CreateThread(void*, SIZE_T, LPTHREAD_START_ROUTINE, LPVOID, DWORD, DWORD*);
__declspec(dllimport) BOOL WINAPI DisableThreadLibraryCalls(HMODULE);
__declspec(dllimport) void WINAPI InitializeCriticalSection(CRITICAL_SECTION*);
__declspec(dllimport) void WINAPI EnterCriticalSection(CRITICAL_SECTION*);
__declspec(dllimport) void WINAPI LeaveCriticalSection(CRITICAL_SECTION*);
__declspec(dllimport) BOOL WINAPI FlushInstructionCache(HANDLE, const void*, SIZE_T);
__declspec(dllimport) LPSTR WINAPI GetCommandLineA(void);
__declspec(dllimport) HANDLE WINAPI GetCurrentProcess(void);
__declspec(dllimport) DWORD WINAPI GetCurrentThreadId(void);
__declspec(dllimport) void WINAPI GetLocalTime(SYSTEMTIME*);
__declspec(dllimport) DWORD WINAPI GetTickCount(void);
__declspec(dllimport) DWORD WINAPI GetModuleFileNameA(HMODULE, LPSTR, DWORD);
__declspec(dllimport) HMODULE WINAPI GetModuleHandleA(LPCSTR);
__declspec(dllimport) BOOL WINAPI GetModuleHandleExA(DWORD, LPCSTR, HMODULE*);
__declspec(dllimport) UINT WINAPI GetPrivateProfileIntA(LPCSTR, LPCSTR, INT, LPCSTR);
__declspec(dllimport) DWORD WINAPI GetPrivateProfileStringA(LPCSTR, LPCSTR, LPCSTR, LPSTR, DWORD, LPCSTR);
__declspec(dllimport) FARPROC WINAPI GetProcAddress(HMODULE, LPCSTR);
__declspec(dllimport) HMODULE WINAPI LoadLibraryA(LPCSTR);
__declspec(dllimport) LPTOP_LEVEL_EXCEPTION_FILTER WINAPI SetUnhandledExceptionFilter(LPTOP_LEVEL_EXCEPTION_FILTER);
__declspec(dllimport) void WINAPI Sleep(DWORD);
__declspec(dllimport) LPVOID WINAPI VirtualAlloc(LPVOID, SIZE_T, DWORD, DWORD);
__declspec(dllimport) BOOL WINAPI VirtualProtect(LPVOID, SIZE_T, DWORD, DWORD*);
__declspec(dllimport) SIZE_T WINAPI VirtualQuery(const void*, MEMORY_BASIC_INFORMATION*, SIZE_T);
__declspec(dllimport) HWND WINAPI CreateWindowExA(DWORD, LPCSTR, LPCSTR, DWORD, int, int, int, int, HWND, HMENU, HINSTANCE, LPVOID);
__declspec(dllimport) LRESULT WINAPI DefWindowProcA(HWND, UINT, WPARAM, LPARAM);
__declspec(dllimport) SHORT WINAPI GetAsyncKeyState(int);
__declspec(dllimport) ATOM WINAPI RegisterClassA(const WNDCLASSA*);
}
#define CreateWindowA(c, n, s, x, y, w, h, p, m, i, l) CreateWindowExA(0, c, n, s, x, y, w, h, p, m, i, l)
static inline LONG InterlockedIncrement(volatile LONG* p) { return __atomic_add_fetch(p, 1, __ATOMIC_SEQ_CST); }
static inline LONG InterlockedExchange(volatile LONG* p, LONG v) { return __atomic_exchange_n(p, v, __ATOMIC_SEQ_CST); }
