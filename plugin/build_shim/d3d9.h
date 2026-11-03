// Minimal Direct3D 9 shim: only the types, constants and interface slots SeveredLoader uses.
#pragma once
#include <windows.h>
typedef DWORD D3DCOLOR;
typedef enum { D3DPT_POINTLIST = 1, D3DPT_FORCE_DWORD = 0x7fffffff } D3DPRIMITIVETYPE;
typedef enum { D3DFMT_UNKNOWN = 0, D3DFMT_FORCE_DWORD = 0x7fffffff } D3DFORMAT;
typedef enum { D3DPOOL_DEFAULT = 0, D3DPOOL_FORCE_DWORD = 0x7fffffff } D3DPOOL;
typedef enum { D3DDEVTYPE_HAL = 1, D3DDEVTYPE_FORCE_DWORD = 0x7fffffff } D3DDEVTYPE;
typedef enum { D3DSAMP_ADDRESSU = 1, D3DSAMP_FORCE_DWORD = 0x7fffffff } D3DSAMPLERSTATETYPE;
typedef enum { D3DSWAPEFFECT_DISCARD = 1, D3DSWAPEFFECT_FORCE_DWORD = 0x7fffffff } D3DSWAPEFFECT;
typedef enum { D3DMULTISAMPLE_NONE = 0, D3DMULTISAMPLE_FORCE_DWORD = 0x7fffffff } D3DMULTISAMPLE_TYPE;
typedef enum { D3DRTYPE_SURFACE = 1, D3DRTYPE_FORCE_DWORD = 0x7fffffff } D3DRESOURCETYPE;
typedef enum {
    D3DRS_ZENABLE = 7, D3DRS_FILLMODE = 8, D3DRS_ZWRITEENABLE = 14, D3DRS_ALPHATESTENABLE = 15, D3DRS_SRCBLEND = 19,
    D3DRS_DESTBLEND = 20, D3DRS_CULLMODE = 22, D3DRS_ZFUNC = 23, D3DRS_ALPHAREF = 24, D3DRS_ALPHABLENDENABLE = 27,
    D3DRS_STENCILENABLE = 52, D3DRS_STENCILFAIL = 53, D3DRS_STENCILZFAIL = 54, D3DRS_STENCILPASS = 55, D3DRS_STENCILFUNC = 56,
    D3DRS_STENCILREF = 57, D3DRS_STENCILMASK = 58, D3DRS_STENCILWRITEMASK = 59, D3DRS_COLORWRITEENABLE = 168,
    D3DRS_FORCE_DWORD = 0x7fffffff } D3DRENDERSTATETYPE;
#define D3DADAPTER_DEFAULT 0
#define D3DCREATE_MULTITHREADED 0x00000004L
#define D3DCREATE_SOFTWARE_VERTEXPROCESSING 0x00000020L
#define D3D_SDK_VERSION 32
#define D3DLOCK_READONLY 0x00000010L
typedef struct { LONG x1, y1, x2, y2; } D3DRECT;
typedef struct { WORD Stream; WORD Offset; BYTE Type, Method, Usage, UsageIndex; } D3DVERTEXELEMENT9;
typedef struct { UINT BackBufferWidth, BackBufferHeight; D3DFORMAT BackBufferFormat; UINT BackBufferCount; D3DMULTISAMPLE_TYPE MultiSampleType;
    DWORD MultiSampleQuality; D3DSWAPEFFECT SwapEffect; HWND hDeviceWindow; BOOL Windowed, EnableAutoDepthStencil; D3DFORMAT AutoDepthStencilFormat;
    DWORD Flags; UINT FullScreen_RefreshRateInHz, PresentationInterval; } D3DPRESENT_PARAMETERS;
typedef struct { D3DFORMAT Format; D3DRESOURCETYPE Type; DWORD Usage; D3DPOOL Pool; D3DMULTISAMPLE_TYPE MultiSampleType; DWORD MultiSampleQuality; UINT Width, Height; } D3DSURFACE_DESC;
typedef struct { INT Pitch; void* pBits; } D3DLOCKED_RECT;
static_assert(sizeof(D3DPRESENT_PARAMETERS) == 56 && sizeof(D3DSURFACE_DESC) == 32 && sizeof(D3DVERTEXELEMENT9) == 8, "d3d layouts");
#define D3DSLOT(n) virtual HRESULT STDMETHODCALLTYPE _slot##n() = 0;
struct IDirect3D9; struct IDirect3DDevice9; struct IDirect3DBaseTexture9; struct IDirect3DVertexBuffer9; struct IDirect3DIndexBuffer9; struct IDirect3DVertexDeclaration9;
struct IDirect3DVertexShader9 { D3DSLOT(0) D3DSLOT(1) D3DSLOT(2) D3DSLOT(3)
    virtual HRESULT STDMETHODCALLTYPE GetFunction(void*, UINT*) = 0; };                       // slot 4
struct IDirect3DPixelShader9 { D3DSLOT(0) D3DSLOT(1) D3DSLOT(2) D3DSLOT(3)
    virtual HRESULT STDMETHODCALLTYPE GetFunction(void*, UINT*) = 0; };                       // slot 4
struct IDirect3DSurface9 { D3DSLOT(0) D3DSLOT(1) D3DSLOT(2) D3DSLOT(3) D3DSLOT(4) D3DSLOT(5) D3DSLOT(6) D3DSLOT(7) D3DSLOT(8) D3DSLOT(9) D3DSLOT(10) D3DSLOT(11)
    virtual HRESULT STDMETHODCALLTYPE GetDesc(D3DSURFACE_DESC*) = 0; };                       // slot 12
struct IDirect3DTexture9 { D3DSLOT(0) D3DSLOT(1) D3DSLOT(2) D3DSLOT(3) D3DSLOT(4) D3DSLOT(5) D3DSLOT(6) D3DSLOT(7) D3DSLOT(8) D3DSLOT(9) D3DSLOT(10)
    D3DSLOT(11) D3DSLOT(12) D3DSLOT(13) D3DSLOT(14) D3DSLOT(15) D3DSLOT(16) D3DSLOT(17) D3DSLOT(18)
    virtual HRESULT STDMETHODCALLTYPE LockRect(UINT, D3DLOCKED_RECT*, const RECT*, DWORD) = 0;  // slot 19
    virtual HRESULT STDMETHODCALLTYPE UnlockRect(UINT) = 0; };                                 // slot 20
