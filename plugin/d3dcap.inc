// ---- Stage 15: D3D argument guard (SetTexture stage 177 = door crash), see stage15_args.inc.
// ---- Stage 14: lock guard (shadow copies with guard zones for VB/IB/2D-texture locks) + d3d9 stream-record check.
// ---- Stage 13: draw ring (last 64 draws dumped on crash), Release hooks -> released-object (use-after-free) guard,
//      pointer-keyed buffer map (stage 6-12 table stopped tracking after 16,384 buffers).
// ---- Stage 8: F9 capture adds per-draw occlusion pixel counts (OCC block) and vertex-position bounds / index ranges (VB/IB lines).
// ---- Stage 6: Direct3D 9 frame capture (+constants, sampler states, shader bytecode, small textures) (F9 = log every draw call of the next frame to SeveredLoader_d3d.log) ----
#include <d3d9.h>
static char g_d3dLogPath[MAX_PATH];
static CRITICAL_SECTION g_d3dCs;
static volatile LONG g_capture = 0;     // 1 = capturing this frame
static volatile LONG g_captureReq = 0;
static FILE* g_cap = nullptr;
static unsigned g_drawNo = 0, g_frameNo = 0;
struct TexInfo { void* p; UINT w, h, lv; DWORD fmt, usage, pool; };
struct BufInfo { void* p; UINT len; DWORD usage, pool, fvf, ifmt; };
struct DeclInfo { void* p; D3DVERTEXELEMENT9 el[24]; int n; };
static TexInfo g_tex[8192]; static int g_ntex = 0;
static DeclInfo g_decl[512]; static int g_ndecl = 0;
static void* g_curTex[8]; static void* g_curVS; static void* g_curPS; static void* g_curDecl; static DWORD g_curFVF;
static void* g_curVB[4]; static UINT g_curVBoff[4], g_curVBstride[4]; static void* g_curIB; static void* g_curRT;
static DWORD g_rs[256];
static TexInfo* FindTex(void* p){ for(int i=g_ntex-1;i>=0;--i) if(g_tex[i].p==p) return &g_tex[i]; return nullptr; }
static BufInfo* FindBuf(void* p);   // stage 13: pointer-keyed map in stage13_tables.inc
static DeclInfo* FindDecl(void* p){ for(int i=g_ndecl-1;i>=0;--i) if(g_decl[i].p==p) return &g_decl[i]; return nullptr; }

typedef HRESULT (STDMETHODCALLTYPE *PFN_Present)(IDirect3DDevice9*, const RECT*, const RECT*, HWND, const RGNDATA*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetRT)(IDirect3DDevice9*, DWORD, IDirect3DSurface9*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_Clear)(IDirect3DDevice9*, DWORD, const D3DRECT*, DWORD, D3DCOLOR, float, DWORD);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetRS)(IDirect3DDevice9*, D3DRENDERSTATETYPE, DWORD);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetTex)(IDirect3DDevice9*, DWORD, IDirect3DBaseTexture9*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_DP)(IDirect3DDevice9*, D3DPRIMITIVETYPE, UINT, UINT);
typedef HRESULT (STDMETHODCALLTYPE *PFN_DIP)(IDirect3DDevice9*, D3DPRIMITIVETYPE, INT, UINT, UINT, UINT, UINT);
typedef HRESULT (STDMETHODCALLTYPE *PFN_DPUP)(IDirect3DDevice9*, D3DPRIMITIVETYPE, UINT, const void*, UINT);
typedef HRESULT (STDMETHODCALLTYPE *PFN_DIPUP)(IDirect3DDevice9*, D3DPRIMITIVETYPE, UINT, UINT, UINT, const void*, D3DFORMAT, const void*, UINT);
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateDecl)(IDirect3DDevice9*, const D3DVERTEXELEMENT9*, IDirect3DVertexDeclaration9**);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetDecl)(IDirect3DDevice9*, IDirect3DVertexDeclaration9*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetFVF)(IDirect3DDevice9*, DWORD);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetVS)(IDirect3DDevice9*, IDirect3DVertexShader9*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetPS)(IDirect3DDevice9*, IDirect3DPixelShader9*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetSS)(IDirect3DDevice9*, UINT, IDirect3DVertexBuffer9*, UINT, UINT);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetIdx)(IDirect3DDevice9*, IDirect3DIndexBuffer9*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateTex)(IDirect3DDevice9*, UINT, UINT, UINT, DWORD, D3DFORMAT, D3DPOOL, IDirect3DTexture9**, HANDLE*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateVB)(IDirect3DDevice9*, UINT, DWORD, DWORD, D3DPOOL, IDirect3DVertexBuffer9**, HANDLE*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateIB)(IDirect3DDevice9*, UINT, DWORD, D3DFORMAT, D3DPOOL, IDirect3DIndexBuffer9**, HANDLE*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateDevice)(IDirect3D9*, UINT, D3DDEVTYPE, HWND, DWORD, D3DPRESENT_PARAMETERS*, IDirect3DDevice9**);
static PFN_Present o_Present; static PFN_SetRT o_SetRT; static PFN_Clear o_Clear; static PFN_SetRS o_SetRS; static PFN_SetTex o_SetTex;
static PFN_DP o_DP; static PFN_DIP o_DIP; static PFN_DPUP o_DPUP; static PFN_DIPUP o_DIPUP; static PFN_CreateDecl o_CreateDecl;
static PFN_SetDecl o_SetDecl; static PFN_SetFVF o_SetFVF; static PFN_SetVS o_SetVS; static PFN_SetPS o_SetPS; static PFN_SetSS o_SetSS;
static PFN_SetIdx o_SetIdx; static PFN_CreateTex o_CreateTex; static PFN_CreateVB o_CreateVB; static PFN_CreateIB o_CreateIB;
static PFN_CreateDevice o_CreateDevice;
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetC)(IDirect3DDevice9*, UINT, const float*, UINT);
typedef HRESULT (STDMETHODCALLTYPE *PFN_SetSamp)(IDirect3DDevice9*, DWORD, D3DSAMPLERSTATETYPE, DWORD);
static PFN_SetC o_SetVSC, o_SetPSC; static PFN_SetSamp o_SetSamp;
static void* g_shUsed[1024]; static int g_nsh = 0;
static void NoteShader(void* p){ if(!p) return; for(int i=0;i<g_nsh;++i) if(g_shUsed[i]==p) return; if(g_nsh<1024) g_shUsed[g_nsh++]=p; }
static void* g_texUsed[4096]; static int g_ntexUsed = 0;
static void NoteTex(void* p){ if(!p) return; for(int i=0;i<g_ntexUsed;++i) if(g_texUsed[i]==p) return; if(g_ntexUsed<4096) g_texUsed[g_ntexUsed++]=p; }
static bool IsVS(void* p);
static void* g_vsList[1024]; static int g_nvs = 0;
static bool IsVS(void* p){ for(int i=0;i<g_nvs;++i) if(g_vsList[i]==p) return true; return false; }


// ---- Stage 8 diagnostics ----
#define VFN(obj, idx) (((void**)*(void**)(obj))[idx])
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateQuery)(IDirect3DDevice9*, DWORD, void**);   // device slot 118
typedef HRESULT (STDMETHODCALLTYPE *PFN_QIssue)(void*, DWORD);                           // query slot 6
typedef HRESULT (STDMETHODCALLTYPE *PFN_QGetData)(void*, void*, DWORD, DWORD);           // query slot 7
typedef HRESULT (STDMETHODCALLTYPE *PFN_BufLock)(void*, UINT, UINT, void**, DWORD);      // VB/IB slot 11
typedef HRESULT (STDMETHODCALLTYPE *PFN_BufUnlock)(void*);                               // VB/IB slot 12
static const int kMaxQ = 4096;
static void* g_qPool[kMaxQ]; static int g_qMade = 0;
static int g_qDraw[kMaxQ]; static int g_qUsed = 0;
static void* g_qCur = nullptr; static int g_qCurDraw = -1;
static void QueryBegin(IDirect3DDevice9* d)
{
    g_qCur = nullptr;
    if (g_qUsed >= kMaxQ) return;
    if (g_qUsed >= g_qMade)
    {
        void* q = nullptr;
        if (FAILED(((PFN_CreateQuery)VFN(d, 118))(d, 9 /*D3DQUERYTYPE_OCCLUSION*/, &q)) || !q) return;
        g_qPool[g_qMade++] = q;
    }
    g_qCur = g_qPool[g_qUsed];
    g_qCurDraw = (int)g_drawNo;
    ((PFN_QIssue)VFN(g_qCur, 6))(g_qCur, 2 /*D3DISSUE_BEGIN*/);
}
static void QueryEnd()
{
    if (!g_qCur) return;
    ((PFN_QIssue)VFN(g_qCur, 6))(g_qCur, 1 /*D3DISSUE_END*/);
    g_qDraw[g_qUsed++] = g_qCurDraw;
    g_qCur = nullptr;
}
static void WriteOcclusion()
{
    fprintf(g_cap, "OCC %d queries\n", g_qUsed);
    for (int i = 0; i < g_qUsed; ++i)
    {
        DWORD px = 0; HRESULT h = 1; DWORD t0 = 0;
        for (int k = 0; k < 200000 && h == 1 /*S_FALSE*/; ++k) { h = ((PFN_QGetData)VFN(g_qPool[i], 7))(g_qPool[i], &px, sizeof(px), 1 /*D3DGETDATA_FLUSH*/); if (h == 1 && (k & 255) == 255) Sleep(0); }
        (void)t0;
        if (h == 0) fprintf(g_cap, "Q D%d px%lu\n", g_qDraw[i], (unsigned long)px); else fprintf(g_cap, "Q D%d fail%08lX\n", g_qDraw[i], (unsigned long)h);
    }
    g_qUsed = 0;
}
static float Half(uint16_t h)
{
    uint32_t s = (h >> 15) & 1, e = (h >> 10) & 31, m = h & 1023, f;
    if (e == 0) { if (!m) f = s << 31; else { e = 127 - 15 + 1; while (!(m & 1024)) { m <<= 1; --e; } m &= 1023; f = (s << 31) | (e << 23) | (m << 13); } }
    else if (e == 31) f = (s << 31) | (255u << 23) | (m << 13);
    else f = (s << 31) | ((e - 15 + 127) << 23) | (m << 13);
    float r; memcpy(&r, &f, 4); return r;
}
// Decode one position (decl type t) into xyz; returns false for types not handled.
static bool DecodePos(const unsigned char* v, int t, float* o)
{
    switch (t)
    {
    case 2: case 3: memcpy(o, v, 12); return true;                                        // FLOAT3 / FLOAT4
    case 15: for (int k = 0; k < 3; ++k) o[k] = Half(((const uint16_t*)v)[k]); return true;  // FLOAT16_4
    case 10: for (int k = 0; k < 3; ++k) o[k] = ((const int16_t*)v)[k] / 32767.0f; return true; // SHORT4N
    case 6: for (int k = 0; k < 3; ++k) o[k] = ((const int16_t*)v)[k]; return true;          // SHORT4
    default: return false;
    }
}
static void InspectBuffers(int prim, int base, UINT minI, UINT numV, UINT start, UINT cnt)
{
    unsigned dn = g_drawNo;   // CapState increments afterwards; this is the same draw number
    // position element of the current declaration
    DeclInfo* di = FindDecl(g_curDecl);
    int ps = -1, po = 0, pt = -1;
    if (di) for (int k = 0; k < di->n; ++k) if (di->el[k].Usage == 0 && di->el[k].UsageIndex == 0) { ps = di->el[k].Stream; po = di->el[k].Offset; pt = di->el[k].Type; break; }
    if (ps >= 0 && ps < 4 && g_curVB[ps] && numV)
    {
        BufInfo* b = FindBuf(g_curVB[ps]);
        UINT stride = g_curVBstride[ps], n = numV < 200000 ? numV : 200000;
        UINT off = g_curVBoff[ps] + (UINT)(base + (int)minI) * stride, size = n * stride;
        if (b && (b->usage & 8 /*WRITEONLY*/) && b->pool == 0) fprintf(g_cap, "VB D%u s%d nolock usage%lX pool%lu\n", dn, ps, (unsigned long)b->usage, (unsigned long)b->pool);
        else if (b && off + size > b->len) fprintf(g_cap, "VB D%u s%d OUT_OF_RANGE off%u size%u len%u\n", dn, ps, off, size, b->len);
        else
        {
            void* p = nullptr;
            HRESULT h = ((PFN_BufLock)VFN(g_curVB[ps], 11))(g_curVB[ps], off, size, &p, D3DLOCK_READONLY);
            if (FAILED(h) || !p) fprintf(g_cap, "VB D%u s%d lockfail%08lX\n", dn, ps, (unsigned long)h);
            else
            {
                const unsigned char* q = (const unsigned char*)p;
                float mn[3] = { 1e30f, 1e30f, 1e30f }, mx[3] = { -1e30f, -1e30f, -1e30f }; unsigned bad = 0, zero = 0; bool ok = true;
                for (UINT i = 0; i < n && ok; ++i)
                {
                    float v[3];
                    if (!DecodePos(q + i * stride + po, pt, v)) { ok = false; break; }
                    if (!(v[0] == v[0] && v[1] == v[1] && v[2] == v[2]) || v[0] > 1e7f || v[0] < -1e7f || v[1] > 1e7f || v[1] < -1e7f || v[2] > 1e7f || v[2] < -1e7f) { ++bad; continue; }
                    if (v[0] == 0 && v[1] == 0 && v[2] == 0) ++zero;
                    for (int k = 0; k < 3; ++k) { if (v[k] < mn[k]) mn[k] = v[k]; if (v[k] > mx[k]) mx[k] = v[k]; }
                }
                fprintf(g_cap, "VB D%u s%d t%d o%d str%u n%u", dn, ps, pt, po, stride, n);
                if (ok) fprintf(g_cap, " min %g %g %g max %g %g %g bad%u zero%u", mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], bad, zero);
                fprintf(g_cap, " first");
                for (UINT k = 0; k < stride * 2 && k < size && k < 64; ++k) fprintf(g_cap, "%s%02x", (k % stride) ? "" : " ", q[k]);
                fputc('\n', g_cap);
                ((PFN_BufUnlock)VFN(g_curVB[ps], 12))(g_curVB[ps]);
            }
        }
    }
    else fprintf(g_cap, "VB D%u nopos decl%p\n", dn, g_curDecl);
    // index range actually referenced
    if (g_curIB && cnt)
    {
        BufInfo* b = FindBuf(g_curIB);
        UINT ni = prim == 4 ? cnt * 3 : prim == 5 || prim == 6 ? cnt + 2 : prim == 2 ? cnt * 2 : prim == 3 ? cnt + 1 : cnt;
        UINT isz = (b && b->ifmt == 102) ? 4 : 2;
        if (b && (b->usage & 8) && b->pool == 0) { fprintf(g_cap, "IB D%u nolock\n", dn); return; }
        if (b && (start + ni) * isz > b->len) { fprintf(g_cap, "IB D%u OUT_OF_RANGE start%u n%u len%u\n", dn, start, ni, b->len); return; }
        void* p = nullptr;
        HRESULT h = ((PFN_BufLock)VFN(g_curIB, 11))(g_curIB, start * isz, ni * isz, &p, D3DLOCK_READONLY);
        if (FAILED(h) || !p) { fprintf(g_cap, "IB D%u lockfail%08lX\n", dn, (unsigned long)h); return; }
        UINT lo = 0xFFFFFFFF, hi = 0, degen = 0;
        for (UINT i = 0; i < ni; ++i) { UINT v = isz == 4 ? ((const uint32_t*)p)[i] : ((const uint16_t*)p)[i]; if (v < lo) lo = v; if (v > hi) hi = v; }
        if (prim == 4) for (UINT t = 0; t < cnt; ++t) { UINT a, bb, c; if (isz == 4) { a = ((const uint32_t*)p)[3*t]; bb = ((const uint32_t*)p)[3*t+1]; c = ((const uint32_t*)p)[3*t+2]; } else { a = ((const uint16_t*)p)[3*t]; bb = ((const uint16_t*)p)[3*t+1]; c = ((const uint16_t*)p)[3*t+2]; } if (a == bb || bb == c || a == c) ++degen; }
        fprintf(g_cap, "IB D%u fmt%lu n%u idx %u..%u (declared min%u nv%u)%s degen%u first", dn, b ? (unsigned long)b->ifmt : 0, ni, lo, hi, minI, numV,
                (lo < minI || hi >= minI + numV) ? " RANGE_MISMATCH" : "", degen);
        for (UINT i = 0; i < ni && i < 9; ++i) fprintf(g_cap, " %u", isz == 4 ? ((const uint32_t*)p)[i] : ((const uint16_t*)p)[i]);
        fputc('\n', g_cap);
        ((PFN_BufUnlock)VFN(g_curIB, 12))(g_curIB);
    }
}


// ---- Stage 10: texture-pointer guard. The quarry door crash happens inside DrawIndexedPrimitive with a bound object
// whose fields are garbage (same pointer 0x15FFCF8F every run, pointing into loaded level data). Every SetTexture
// pointer must be a real D3D object: readable and its vtable inside the module that implements the device.
// A bad pointer is logged (caller, value, bytes) and replaced with NULL.
static uintptr_t g_d3dLo = 0, g_d3dHi = 0;
static void* g_okTex[4096];
static unsigned g_badTexN = 0;
static bool TexPtrOk(void* t)
{
    if (!t || !g_d3dHi) return true;
    unsigned h = ((uintptr_t)t >> 4) & 4095;
    if (g_okTex[h] == t) return true;
    uintptr_t p = (uintptr_t)t;
    if (!Readable(p, 8)) return false;
    uintptr_t vt = *(uintptr_t*)p;
    if (!Readable(vt, 4)) return false;
    uintptr_t fn = *(uintptr_t*)vt;
    bool ok = (vt >= g_d3dLo && vt < g_d3dHi) || (fn >= g_d3dLo && fn < g_d3dHi);
    if (ok) g_okTex[h] = t;
    return ok;
}
static void SetD3DModuleRange(void* codeAddr)
{
    MEMORY_BASIC_INFORMATION mbi;
    if (!VirtualQuery(codeAddr, &mbi, sizeof(mbi)) || !mbi.AllocationBase) return;
    uintptr_t b = (uintptr_t)mbi.AllocationBase;
    if (!Readable(b, 0x40)) return;
    uint32_t pe = *(uint32_t*)(b + 0x3C);
    if (!Readable(b + pe, 0x58)) return;
    g_d3dLo = b; g_d3dHi = b + *(uint32_t*)(b + pe + 0x50);
    char m[160]; ModOf(m, sizeof(m), (uintptr_t)codeAddr);
    Log("texture guard: D3D implementation module 0x%08X-0x%08X (%s)", (unsigned)g_d3dLo, (unsigned)g_d3dHi, m);
}

#include "stage13_tables.inc"
#include "stage14_lock.inc"

static void FindMeshes(const char* tag, uintptr_t esp);
static void CapState(const char* what, int prim, int base, UINT minI, UINT numV, UINT start, UINT cnt, HRESULT hr)
{
    if (!g_cap) return;
    NoteShader(g_curPS); if (g_curVS) { NoteShader(g_curVS); if (!IsVS(g_curVS) && g_nvs < 1024) g_vsList[g_nvs++] = g_curVS; }
    for (int t = 0; t < 8; ++t) NoteTex(g_curTex[t]);
    fprintf(g_cap, "D%u %s prim%d base%d min%u nv%u start%u cnt%u hr%08lX decl%p fvf%lX vs%p ps%p ib%p",
            g_drawNo++, what, prim, base, minI, numV, start, cnt, (unsigned long)hr, g_curDecl, (unsigned long)g_curFVF, g_curVS, g_curPS, g_curIB);
    for (int s = 0; s < 4; ++s) if (g_curVB[s]) { BufInfo* b = FindBuf(g_curVB[s]); fprintf(g_cap, " vb%d=%p/len%u/off%u/str%u", s, g_curVB[s], b ? b->len : 0, g_curVBoff[s], g_curVBstride[s]); }
    for (int t = 0; t < 8; ++t) if (g_curTex[t]) { TexInfo* x = FindTex(g_curTex[t]); if (x) fprintf(g_cap, " t%d=%p/%ux%u/f%lu", t, g_curTex[t], x->w, x->h, (unsigned long)x->fmt); else fprintf(g_cap, " t%d=%p/?", t, g_curTex[t]); }
    fprintf(g_cap, " rs cull%lu z%lu zw%lu zf%lu ab%lu sb%lu db%lu at%lu aref%lu cw%lX st%lu fill%lu sfn%lu sref%lu smask%lX swmask%lX sfail%lu szfail%lu spass%lu\n",
            (unsigned long)g_rs[D3DRS_CULLMODE], (unsigned long)g_rs[D3DRS_ZENABLE], (unsigned long)g_rs[D3DRS_ZWRITEENABLE], (unsigned long)g_rs[D3DRS_ZFUNC],
            (unsigned long)g_rs[D3DRS_ALPHABLENDENABLE], (unsigned long)g_rs[D3DRS_SRCBLEND], (unsigned long)g_rs[D3DRS_DESTBLEND], (unsigned long)g_rs[D3DRS_ALPHATESTENABLE],
            (unsigned long)g_rs[D3DRS_ALPHAREF], (unsigned long)g_rs[D3DRS_COLORWRITEENABLE], (unsigned long)g_rs[D3DRS_STENCILENABLE], (unsigned long)g_rs[D3DRS_FILLMODE],
            (unsigned long)g_rs[D3DRS_STENCILFUNC], (unsigned long)g_rs[D3DRS_STENCILREF], (unsigned long)g_rs[D3DRS_STENCILMASK], (unsigned long)g_rs[D3DRS_STENCILWRITEMASK],
            (unsigned long)g_rs[D3DRS_STENCILFAIL], (unsigned long)g_rs[D3DRS_STENCILZFAIL], (unsigned long)g_rs[D3DRS_STENCILPASS]);
}
#include "stage13_ring.inc"
#include "stage15_args.inc"
static unsigned g_staleSkipN = 0;
static bool StaleSkip(const char* what, uintptr_t ra)
{
    if (!g_staleGuard || !g_staleMask) return false;
    ++g_staleSkipN;
    if (g_staleSkipN <= 10 || (g_staleSkipN & 4095) == 0) { char m[160]; ModOf(m, sizeof(m), ra); Log("stale guard: SKIPPED %s #%u from 0x%08X (%s): released object bound (mask 0x%X)", what, g_staleSkipN, (unsigned)ra, m, (unsigned)g_staleMask); }
    return true;
}
static HRESULT STDMETHODCALLTYPE h_Present(IDirect3DDevice9* d, const RECT* a, const RECT* b, HWND w, const RGNDATA* r)
{
    HRESULT hr = o_Present(d, a, b, w, r);
    ++g_frameNo;
    if (g_capture) {
        g_capture = 0;
        if (g_cap) {
            fprintf(g_cap, "END frame %u, %u draws\n", g_frameNo, g_drawNo);
            WriteOcclusion();
            fprintf(g_cap, "DECLS\n");
            EnterCriticalSection(&g_d3dCs);
            for (int i = 0; i < g_ndecl; ++i) { fprintf(g_cap, "decl %p:", g_decl[i].p); for (int k = 0; k < g_decl[i].n; ++k) { const D3DVERTEXELEMENT9& e = g_decl[i].el[k]; fprintf(g_cap, " [s%u o%u t%u m%u u%u i%u]", e.Stream, e.Offset, e.Type, e.Method, e.Usage, e.UsageIndex); } fputc('\n', g_cap); }
            LeaveCriticalSection(&g_d3dCs);
            fprintf(g_cap, "SHADERS\n");
            for (int i = 0; i < g_nsh; ++i) {
                UINT sz = 0; HRESULT h2; bool vs = IsVS(g_shUsed[i]);
                if (vs) h2 = ((IDirect3DVertexShader9*)g_shUsed[i])->GetFunction(nullptr, &sz); else h2 = ((IDirect3DPixelShader9*)g_shUsed[i])->GetFunction(nullptr, &sz);
                if (FAILED(h2) || !sz || sz > 262144) { fprintf(g_cap, "%s %p fail %08lX\n", vs ? "VS" : "PS", g_shUsed[i], (unsigned long)h2); continue; }
                unsigned char* buf = (unsigned char*)malloc(sz);
                if (vs) ((IDirect3DVertexShader9*)g_shUsed[i])->GetFunction(buf, &sz); else ((IDirect3DPixelShader9*)g_shUsed[i])->GetFunction(buf, &sz);
                fprintf(g_cap, "%s %p %u ", vs ? "VS" : "PS", g_shUsed[i], sz); for (UINT k = 0; k < sz; ++k) fprintf(g_cap, "%02x", buf[k]); fputc('\n', g_cap); free(buf);
            }
            fprintf(g_cap, "SMALLTEX\n");
            for (int i = 0; i < g_ntexUsed; ++i) {
                TexInfo* x = FindTex(g_texUsed[i]); if (!x || x->w > 8 || x->h > 8) continue;
                IDirect3DTexture9* tx = (IDirect3DTexture9*)g_texUsed[i]; D3DLOCKED_RECT lr; HRESULT h3 = tx->LockRect(0, &lr, nullptr, D3DLOCK_READONLY);
                fprintf(g_cap, "tex %p %ux%u f%lu pool%lu usage%lX lock%08lX", tx, x->w, x->h, (unsigned long)x->fmt, (unsigned long)x->pool, (unsigned long)x->usage, (unsigned long)h3);
                if (SUCCEEDED(h3)) { unsigned char* b = (unsigned char*)lr.pBits; for (int k = 0; k < 16 && k < (int)(x->w * 4); ++k) fprintf(g_cap, " %02x", b[k]); tx->UnlockRect(0); }
                fputc('\n', g_cap);
            }
            g_nsh = 0; g_ntexUsed = 0;
            fclose(g_cap); g_cap = nullptr;
        }
        Log("d3d capture written: %s", g_d3dLogPath);
    }
    PollAmbientKey();
    if ((GetAsyncKeyState(VK_F9) & 0x8000) && !g_captureReq) { g_captureReq = 1; }
    else if (!(GetAsyncKeyState(VK_F9) & 0x8000) && g_captureReq == 1) {
        g_captureReq = 0;
        g_cap = fopen(g_d3dLogPath, "w");
        if (g_cap) { fprintf(g_cap, "FRAME %u device %p\n", g_frameNo + 1, d); g_drawNo = 0; g_capture = 1; }
    }
    return hr;
}
static HRESULT STDMETHODCALLTYPE h_SetRT(IDirect3DDevice9* d, DWORD i, IDirect3DSurface9* s)
{ if (g_capture && g_cap) { D3DSURFACE_DESC ds = {}; if (s) s->GetDesc(&ds); fprintf(g_cap, "RT%lu=%p %ux%u f%lu\n", (unsigned long)i, s, ds.Width, ds.Height, (unsigned long)ds.Format); } return o_SetRT(d, i, s); }
static HRESULT STDMETHODCALLTYPE h_Clear(IDirect3DDevice9* d, DWORD n, const D3DRECT* r, DWORD fl, D3DCOLOR c, float z, DWORD st)
{ if (g_capture && g_cap) fprintf(g_cap, "CLEAR flags%lX color%08lX z%.3f\n", (unsigned long)fl, (unsigned long)c, z); return o_Clear(d, n, r, fl, c, z, st); }
static HRESULT STDMETHODCALLTYPE h_SetRS(IDirect3DDevice9* d, D3DRENDERSTATETYPE s, DWORD v) { if ((unsigned)s >= 256) { ArgLog(4, (uintptr_t)__builtin_return_address(0), "state %u value 0x%08lX", (unsigned)s, (unsigned long)v); return 0; } g_rs[s] = v; return o_SetRS(d, s, v); }
static HRESULT STDMETHODCALLTYPE h_SetTex(IDirect3DDevice9* d, DWORD st, IDirect3DBaseTexture9* t)
{
    if (!TexStageOk(st)) { ArgCheckTex(st, t, (uintptr_t)__builtin_return_address(0)); return 0; }
    if (t && !TexPtrOk(t))
    {
        ++g_badTexN;
        if (g_badTexN <= 20 || (g_badTexN & 1023) == 0)
        {
            uintptr_t ra = (uintptr_t)__builtin_return_address(0);
            char m[160]; ModOf(m, sizeof(m), ra);
            Log("texture guard: BAD texture pointer 0x%08X on stage %lu from 0x%08X (%s), #%u -> replaced with NULL", (unsigned)(uintptr_t)t, (unsigned long)st, (unsigned)ra, m, g_badTexN);
            if (g_badTexN <= 3) { HexLine("bad-ptr-64", (uintptr_t)t - 64, 160); }
        }
        t = nullptr;
    }
    if (t) { WatchObj(t, K_TEX); if (StaleCheck("texture", t, st, (uintptr_t)__builtin_return_address(0)) && g_staleGuard) t = nullptr; }
    if (st < 8) g_curTex[st] = t;
    return o_SetTex(d, st, t);
}
static HRESULT STDMETHODCALLTYPE h_DP(IDirect3DDevice9* d, D3DPRIMITIVETYPE p, UINT s, UINT c) { uintptr_t ra = (uintptr_t)__builtin_return_address(0); RecDraw(1, ra, p, 0, 0, 0, s, c); if (StaleSkip("DrawPrimitive", ra)) return 0; bool cap = g_capture && g_cap; if (cap) QueryBegin(d); HRESULT hr = o_DP(d, p, s, c); if (cap) { QueryEnd(); CapState("DP", p, 0, 0, 0, s, c, hr); } return hr; }
// ---- Stage 11: DrawIndexedPrimitive parameter guard (quarry door crash = d3d9 error path on an invalid DIP).
static unsigned g_badDipN = 0;
static bool DipOk(D3DPRIMITIVETYPE p, INT b, UINT mi, UINT nv, UINT s, UINT c, char* why, size_t wn)
{
    why[0] = 0;
    if (!c) return true;
    UINT ni = p == 4 ? c * 3 : (p == 5 || p == 6) ? c + 2 : p == 2 ? c * 2 : p == 3 ? c + 1 : c;
    if (!g_curIB) { snprintf(why, wn, "no index buffer"); return false; }
    BufInfo* ib = FindBuf(g_curIB);
    if (ib) { UINT isz = ib->ifmt == 102 ? 4 : 2; if ((unsigned long long)(s + ni) * isz > ib->len) { snprintf(why, wn, "indices %u..%u past IB end (%u indices)", s, s + ni, ib->len / isz); return false; } }
    if (g_curVB[0])
    {
        BufInfo* vb = FindBuf(g_curVB[0]); UINT st = g_curVBstride[0];
        if (vb && st && b >= 0 && (unsigned long long)g_curVBoff[0] + (unsigned long long)((UINT)b + mi + nv) * st > vb->len)
        { static unsigned vbn = 0; if (++vbn <= 10) { Log("draw guard (log only, drawn): vertex range past VB end: base %d min %u nv %u stride %u VB %u bytes off %u", b, mi, nv, st, vb->len, g_curVBoff[0]); } }
    }
    if (b < 0 && (INT)mi + b < 0) { snprintf(why, wn, "negative base %d", b); return false; }
    return true;
}
static HRESULT STDMETHODCALLTYPE h_DIP(IDirect3DDevice9* d, D3DPRIMITIVETYPE p, INT b, UINT mi, UINT nv, UINT s, UINT c) {
    { uintptr_t ra = (uintptr_t)__builtin_return_address(0); RecDraw(2, ra, p, b, mi, nv, s, c); if (StaleSkip("DrawIndexedPrimitive", ra)) return 0; }
    { char why[200];
      if (!DipOk(p, b, mi, nv, s, c, why, sizeof(why)))
      {
          ++g_badDipN;
          if (g_badDipN <= 30 || (g_badDipN & 4095) == 0)
          {
              uintptr_t ra = (uintptr_t)__builtin_return_address(0); char m[160]; ModOf(m, sizeof(m), ra);
              BufInfo* vb = g_curVB[0] ? FindBuf(g_curVB[0]) : nullptr; BufInfo* ib = g_curIB ? FindBuf(g_curIB) : nullptr;
              Log("draw guard: SKIPPED invalid DrawIndexedPrimitive #%u from 0x%08X (%s): %s | prim %d base %d min %u nv %u start %u cnt %u | vb0 %p len %u usage %lX pool %lu str %u | ib %p len %u fmt %lu usage %lX tex0 %p",
                  g_badDipN, (unsigned)ra, m, why, (int)p, b, mi, nv, s, c, g_curVB[0], vb ? vb->len : 0, vb ? (unsigned long)vb->usage : 0, vb ? (unsigned long)vb->pool : 0, g_curVBstride[0],
                  g_curIB, ib ? ib->len : 0, ib ? (unsigned long)ib->ifmt : 0, ib ? (unsigned long)ib->usage : 0, g_curTex[0]);
              if (g_badDipN <= 4) { uintptr_t here; asm volatile("movl %%esp, %0" : "=r"(here)); FindMeshes("draw guard", here);
                  char st[600]; int pos = 0, f = 0; for (int i = 0; i < 400 && f < 16; ++i) { uintptr_t a2 = here + 4 * i; if (!Readable(a2, 4)) break; uintptr_t v = *(uintptr_t*)a2; if (v >= 0x401000 && v < 0x1B00000) { pos += snprintf(st + pos, sizeof(st) - pos, " %08X", (unsigned)v); ++f; } }
                  Log("    draw guard stack:%s", st); }
          }
          return 0;   // D3D_OK, draw skipped
      } } bool cap = g_capture && g_cap; if (cap) QueryBegin(d); HRESULT hr = o_DIP(d, p, b, mi, nv, s, c); if (cap) { QueryEnd(); InspectBuffers(p, b, mi, nv, s, c); CapState("DIP", p, b, mi, nv, s, c, hr); } return hr; }
static HRESULT STDMETHODCALLTYPE h_DPUP(IDirect3DDevice9* d, D3DPRIMITIVETYPE p, UINT c, const void* v, UINT str) { RecDraw(3, (uintptr_t)__builtin_return_address(0), p, 0, 0, 0, str, c); HRESULT hr = o_DPUP(d, p, c, v, str); if (g_capture) CapState("DPUP", p, 0, 0, 0, str, c, hr); return hr; }
static HRESULT STDMETHODCALLTYPE h_DIPUP(IDirect3DDevice9* d, D3DPRIMITIVETYPE p, UINT mi, UINT nv, UINT c, const void* i, D3DFORMAT f, const void* v, UINT str) { RecDraw(4, (uintptr_t)__builtin_return_address(0), p, 0, mi, nv, str, c); HRESULT hr = o_DIPUP(d, p, mi, nv, c, i, f, v, str); if (g_capture) CapState("DIPUP", p, 0, mi, nv, str, c, hr); return hr; }
static HRESULT STDMETHODCALLTYPE h_CreateDecl(IDirect3DDevice9* d, const D3DVERTEXELEMENT9* e, IDirect3DVertexDeclaration9** out)
{
    HRESULT hr = o_CreateDecl(d, e, out);
    if (SUCCEEDED(hr) && out && *out) { EnterCriticalSection(&g_d3dCs); if (g_ndecl < 512) { DeclInfo& x = g_decl[g_ndecl++]; x.p = *out; x.n = 0; while (x.n < 24 && e[x.n].Stream != 0xFF) { x.el[x.n] = e[x.n]; ++x.n; } } DeadClear(*out); LeaveCriticalSection(&g_d3dCs); WatchObj(*out, K_DECL); }
    return hr;
}
static HRESULT STDMETHODCALLTYPE h_SetVSC(IDirect3DDevice9* d, UINT r, const float* v, UINT n)
{ if ((unsigned long long)r + n > 256) { ArgLog(2, (uintptr_t)__builtin_return_address(0), "start %u count %u", r, n); if (r >= 256) return 0; n = 256 - r; } if (g_capture && g_cap && v) { fprintf(g_cap, "VSC %u %u", r, n); for (UINT i = 0; i < n * 4 && i < 1024; ++i) fprintf(g_cap, " %g", v[i]); fputc('\n', g_cap); } return o_SetVSC(d, r, v, n); }
static HRESULT STDMETHODCALLTYPE h_SetPSC(IDirect3DDevice9* d, UINT r, const float* v, UINT n)
{ if ((unsigned long long)r + n > 224) { ArgLog(3, (uintptr_t)__builtin_return_address(0), "start %u count %u", r, n); if (r >= 224) return 0; n = 224 - r; } if (g_capture && g_cap && v) { fprintf(g_cap, "PSC %u %u", r, n); for (UINT i = 0; i < n * 4 && i < 1024; ++i) fprintf(g_cap, " %g", v[i]); fputc('\n', g_cap); } return o_SetPSC(d, r, v, n); }
static HRESULT STDMETHODCALLTYPE h_SetSamp(IDirect3DDevice9* d, DWORD st, D3DSAMPLERSTATETYPE t, DWORD v)
{ if (g_capture && g_cap) fprintf(g_cap, "SAMP %lu %d %lu\n", (unsigned long)st, (int)t, (unsigned long)v); return o_SetSamp(d, st, t, v); }
static void StaleBit(int bit, bool on) { if (on) g_staleMask |= 1u << bit; else g_staleMask &= ~(1u << bit); }
static HRESULT STDMETHODCALLTYPE h_SetDecl(IDirect3DDevice9* d, IDirect3DVertexDeclaration9* v) { if (v) WatchObj(v, K_DECL); StaleBit(5, v && StaleCheck("vertex decl", v, 0, (uintptr_t)__builtin_return_address(0))); g_curDecl = v; return o_SetDecl(d, v); }
static HRESULT STDMETHODCALLTYPE h_SetFVF(IDirect3DDevice9* d, DWORD f) { g_curFVF = f; return o_SetFVF(d, f); }
static HRESULT STDMETHODCALLTYPE h_SetVS(IDirect3DDevice9* d, IDirect3DVertexShader9* s) { if (s) WatchObj(s, K_VS); StaleBit(6, s && StaleCheck("vertex shader", s, 0, (uintptr_t)__builtin_return_address(0))); g_curVS = s; return o_SetVS(d, s); }
static HRESULT STDMETHODCALLTYPE h_SetPS(IDirect3DDevice9* d, IDirect3DPixelShader9* s) { if (s) WatchObj(s, K_PS); StaleBit(7, s && StaleCheck("pixel shader", s, 0, (uintptr_t)__builtin_return_address(0))); g_curPS = s; return o_SetPS(d, s); }
static void BadObj(const char* what, void* p, unsigned slot, uintptr_t ra)
{
    ++g_badTexN;
    if (g_badTexN <= 20 || (g_badTexN & 1023) == 0) { char m[160]; ModOf(m, sizeof(m), ra); Log("object guard: BAD %s pointer 0x%08X slot %u from 0x%08X (%s), #%u -> replaced with NULL", what, (unsigned)(uintptr_t)p, slot, (unsigned)ra, m, g_badTexN); if (g_badTexN <= 3) HexLine("bad-ptr-64", (uintptr_t)p - 64, 160); }
}
static HRESULT STDMETHODCALLTYPE h_SetSS(IDirect3DDevice9* d, UINT n, IDirect3DVertexBuffer9* b, UINT o, UINT s) { if (n >= 16) { ArgLog(1, (uintptr_t)__builtin_return_address(0), "stream %u vb %p off %u stride %u", n, b, o, s); return 0; } if (b && !TexPtrOk(b)) { BadObj("vertex buffer", b, n, (uintptr_t)__builtin_return_address(0)); b = nullptr; } if (b) WatchObj(b, K_VB); if (n < 4) StaleBit(n, b && StaleCheck("vertex buffer", b, n, (uintptr_t)__builtin_return_address(0))); if (n < 4) { g_curVB[n] = b; g_curVBoff[n] = o; g_curVBstride[n] = s; } return o_SetSS(d, n, b, o, s); }
static HRESULT STDMETHODCALLTYPE h_SetIdx(IDirect3DDevice9* d, IDirect3DIndexBuffer9* b) { if (b && !TexPtrOk(b)) { BadObj("index buffer", b, 0, (uintptr_t)__builtin_return_address(0)); b = nullptr; } if (b) WatchObj(b, K_IB); StaleBit(4, b && StaleCheck("index buffer", b, 0, (uintptr_t)__builtin_return_address(0))); g_curIB = b; return o_SetIdx(d, b); }
static HRESULT STDMETHODCALLTYPE h_CreateTex(IDirect3DDevice9* d, UINT w, UINT h, UINT l, DWORD u, D3DFORMAT f, D3DPOOL p, IDirect3DTexture9** t, HANDLE* sh)
{
    HRESULT hr = o_CreateTex(d, w, h, l, u, f, p, t, sh);
    if (SUCCEEDED(hr) && t && *t) { EnterCriticalSection(&g_d3dCs); TexInfo& x = g_tex[g_ntex % 8192]; ++g_ntex; if (g_ntex > 8192) g_ntex = 8192; x.p = *t; x.w = w; x.h = h; x.lv = l; x.fmt = f; x.usage = u; x.pool = p; DeadClear(*t); LeaveCriticalSection(&g_d3dCs); WatchObj(*t, K_TEX); LockHook(*t, K_TEX); }
    return hr;
}
static HRESULT STDMETHODCALLTYPE h_CreateVB(IDirect3DDevice9* d, UINT len, DWORD u, DWORD fvf, D3DPOOL p, IDirect3DVertexBuffer9** b, HANDLE* sh)
{
    HRESULT hr = o_CreateVB(d, len, u, fvf, p, b, sh);
    if (SUCCEEDED(hr) && b && *b) { EnterCriticalSection(&g_d3dCs); DeadClear(*b); if (BufInfo* x = BufPut(*b)) { x->len = len; x->usage = u; x->pool = p; x->fvf = fvf; } LeaveCriticalSection(&g_d3dCs); WatchObj(*b, K_VB); LockHook(*b, K_VB); }
    return hr;
}
static HRESULT STDMETHODCALLTYPE h_CreateIB(IDirect3DDevice9* d, UINT len, DWORD u, D3DFORMAT f, D3DPOOL p, IDirect3DIndexBuffer9** b, HANDLE* sh)
{
    HRESULT hr = o_CreateIB(d, len, u, f, p, b, sh);
    if (SUCCEEDED(hr) && b && *b) { EnterCriticalSection(&g_d3dCs); DeadClear(*b); if (BufInfo* x = BufPut(*b)) { x->len = len; x->usage = u; x->pool = p; x->fvf = 0xFFFFFFFF; x->ifmt = f; } LeaveCriticalSection(&g_d3dCs); WatchObj(*b, K_IB); LockHook(*b, K_IB); }
    return hr;
}
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateVolTex)(IDirect3DDevice9*, UINT, UINT, UINT, UINT, DWORD, D3DFORMAT, D3DPOOL, void**, HANDLE*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateCubeTex)(IDirect3DDevice9*, UINT, UINT, DWORD, D3DFORMAT, D3DPOOL, void**, HANDLE*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_CreateShader)(IDirect3DDevice9*, const DWORD*, void**);
static PFN_CreateVolTex o_CreateVolTex; static PFN_CreateCubeTex o_CreateCubeTex; static PFN_CreateShader o_CreateVS, o_CreatePS;
static void NewObj(void* p, int kind) { if (!p) return; EnterCriticalSection(&g_d3dCs); DeadClear(p); LeaveCriticalSection(&g_d3dCs); WatchObj(p, kind); }
static HRESULT STDMETHODCALLTYPE h_CreateVolTex(IDirect3DDevice9* d, UINT w, UINT h, UINT dp, UINT l, DWORD u, D3DFORMAT f, D3DPOOL p, void** t, HANDLE* sh)
{ HRESULT hr = o_CreateVolTex(d, w, h, dp, l, u, f, p, t, sh); if (SUCCEEDED(hr) && t) NewObj(*t, K_TEX); return hr; }
static HRESULT STDMETHODCALLTYPE h_CreateCubeTex(IDirect3DDevice9* d, UINT e, UINT l, DWORD u, D3DFORMAT f, D3DPOOL p, void** t, HANDLE* sh)
{ HRESULT hr = o_CreateCubeTex(d, e, l, u, f, p, t, sh); if (SUCCEEDED(hr) && t) NewObj(*t, K_TEX); return hr; }
static HRESULT STDMETHODCALLTYPE h_CreateVS(IDirect3DDevice9* d, const DWORD* fn, void** s) { HRESULT hr = o_CreateVS(d, fn, s); if (SUCCEEDED(hr) && s) NewObj(*s, K_VS); return hr; }
static HRESULT STDMETHODCALLTYPE h_CreatePS(IDirect3DDevice9* d, const DWORD* fn, void** s) { HRESULT hr = o_CreatePS(d, fn, s); if (SUCCEEDED(hr) && s) NewObj(*s, K_PS); return hr; }
template <class T> static void PatchSlot(void** vt, int i, T hook, T* orig)
{
    if (vt[i] == (void*)hook) return;
    DWORD old; VirtualProtect(&vt[i], sizeof(void*), PAGE_EXECUTE_READWRITE, &old);
    *orig = (T)vt[i]; vt[i] = (void*)hook;
    VirtualProtect(&vt[i], sizeof(void*), old, &old);
}
static volatile LONG g_devHooked = 0;
static void HookDevice(IDirect3DDevice9* dev, const char* how)
{
    void** vt = *(void***)dev;
    if (vt[17] == (void*)h_Present) return;
    PatchSlot(vt, 17, (PFN_Present)h_Present, &o_Present);
    PatchSlot(vt, 37, (PFN_SetRT)h_SetRT, &o_SetRT);
    PatchSlot(vt, 43, (PFN_Clear)h_Clear, &o_Clear);
    PatchSlot(vt, 57, (PFN_SetRS)h_SetRS, &o_SetRS);
    PatchSlot(vt, 65, (PFN_SetTex)h_SetTex, &o_SetTex);
    PatchSlot(vt, 81, (PFN_DP)h_DP, &o_DP);
    PatchSlot(vt, 82, (PFN_DIP)h_DIP, &o_DIP);
    PatchSlot(vt, 83, (PFN_DPUP)h_DPUP, &o_DPUP);
    PatchSlot(vt, 84, (PFN_DIPUP)h_DIPUP, &o_DIPUP);
    PatchSlot(vt, 86, (PFN_CreateDecl)h_CreateDecl, &o_CreateDecl);
    PatchSlot(vt, 87, (PFN_SetDecl)h_SetDecl, &o_SetDecl);
    PatchSlot(vt, 89, (PFN_SetFVF)h_SetFVF, &o_SetFVF);
    PatchSlot(vt, 92, (PFN_SetVS)h_SetVS, &o_SetVS);
    PatchSlot(vt, 107, (PFN_SetPS)h_SetPS, &o_SetPS);
    PatchSlot(vt, 100, (PFN_SetSS)h_SetSS, &o_SetSS);
    PatchSlot(vt, 104, (PFN_SetIdx)h_SetIdx, &o_SetIdx);
    PatchSlot(vt, 23, (PFN_CreateTex)h_CreateTex, &o_CreateTex);
    PatchSlot(vt, 94, (PFN_SetC)h_SetVSC, &o_SetVSC);
    PatchSlot(vt, 109, (PFN_SetC)h_SetPSC, &o_SetPSC);
    PatchSlot(vt, 69, (PFN_SetSamp)h_SetSamp, &o_SetSamp);
    PatchSlot(vt, 26, (PFN_CreateVB)h_CreateVB, &o_CreateVB);
    PatchSlot(vt, 27, (PFN_CreateIB)h_CreateIB, &o_CreateIB);
    PatchSlot(vt, 24, (PFN_CreateVolTex)h_CreateVolTex, &o_CreateVolTex);
    PatchSlot(vt, 25, (PFN_CreateCubeTex)h_CreateCubeTex, &o_CreateCubeTex);
    PatchSlot(vt, 91, (PFN_CreateShader)h_CreateVS, &o_CreateVS);
    PatchSlot(vt, 106, (PFN_CreateShader)h_CreatePS, &o_CreatePS);
    InterlockedExchange(&g_devHooked, 1);
    if (!g_d3dHi) SetD3DModuleRange((void*)o_Present);
    Log("d3d9 device %p hooked (%s), vtable %p; press F9 in game to capture one frame", dev, how, vt);
}
static HRESULT STDMETHODCALLTYPE h_CreateDevice(IDirect3D9* d3d, UINT a, D3DDEVTYPE t, HWND w, DWORD fl, D3DPRESENT_PARAMETERS* pp, IDirect3DDevice9** out)
{
    HRESULT hr = o_CreateDevice(d3d, a, t, w, fl, pp, out);
    Log("IDirect3D9::CreateDevice type %d flags 0x%lX %ux%u fmt %lu windowed %d -> hr 0x%08lX", t, (unsigned long)fl, pp ? pp->BackBufferWidth : 0, pp ? pp->BackBufferHeight : 0, pp ? (unsigned long)pp->BackBufferFormat : 0, pp ? pp->Windowed : -1, (unsigned long)hr);
    if (SUCCEEDED(hr) && out && *out) { g_dev = *out; HookDevice(*out, "CreateDevice"); }
    return hr;
}
typedef IDirect3D9* (WINAPI *PFN_Create9)(UINT);
static PFN_Create9 o_Create9; static unsigned char* g_c9tramp = nullptr;
static IDirect3D9* WINAPI h_Create9(UINT sdk)
{
    IDirect3D9* d = o_Create9(sdk);
    if (d) { void** vt = *(void***)d; PatchSlot(vt, 16, (PFN_CreateDevice)h_CreateDevice, &o_CreateDevice); Log("Direct3DCreate9(%u) -> %p, CreateDevice hooked", sdk, d); }
    return d;
}
static void InstallD3DHooks()
{
    InitializeCriticalSection(&g_d3dCs);
    strcpy(g_d3dLogPath, g_logPath); char* dot = strrchr(g_d3dLogPath, '.'); if (dot) strcpy(dot, "_d3d.log");
    HMODULE m = LoadLibraryA("d3d9.dll");
    unsigned char* f = m ? (unsigned char*)GetProcAddress(m, "Direct3DCreate9") : nullptr;
    if (!f) { Log("d3d capture: Direct3DCreate9 not found"); return; }
    unsigned char* t = (unsigned char*)VirtualAlloc(nullptr, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (f[0] == 0x8B && f[1] == 0xFF && f[2] == 0x55 && f[3] == 0x8B && f[4] == 0xEC) {
        memcpy(t, f, 5); t[5] = 0xE9; *(int32_t*)(t + 6) = (int32_t)((f + 5) - (t + 10));
    } else if (f[0] == 0xE9) {
        unsigned char* tgt = f + 5 + *(int32_t*)(f + 1); t[0] = 0xE9; *(int32_t*)(t + 1) = (int32_t)(tgt - (t + 5));
    } else { Log("d3d capture: unexpected Direct3DCreate9 prologue %02X %02X %02X %02X %02X, not hooked", f[0], f[1], f[2], f[3], f[4]); return; }
    o_Create9 = (PFN_Create9)t; g_c9tramp = t;
    DWORD old; VirtualProtect(f, 5, PAGE_EXECUTE_READWRITE, &old);
    f[0] = 0xE9; *(int32_t*)(f + 1) = (int32_t)((unsigned char*)&h_Create9 - (f + 5));
    VirtualProtect(f, 5, old, &old); FlushInstructionCache(GetCurrentProcess(), f, 5);
    Log("d3d capture: Direct3DCreate9 hooked at %p", f);
}
static DWORD WINAPI D3DFallback(LPVOID)
{
    Sleep(15000);
    if (g_devHooked) return 0;
    Log("d3d capture: no CreateDevice seen after 15 s, hooking via a hidden dummy device");
    WNDCLASSA wc = {}; wc.lpfnWndProc = DefWindowProcA; wc.hInstance = GetModuleHandleA(nullptr); wc.lpszClassName = "SevD3DDummy";
    RegisterClassA(&wc);
    HWND w = CreateWindowA("SevD3DDummy", "", WS_OVERLAPPEDWINDOW, 0, 0, 8, 8, nullptr, nullptr, wc.hInstance, nullptr);
    HMODULE m = LoadLibraryA("d3d9.dll");
    PFN_Create9 c9 = o_Create9 ? o_Create9 : (PFN_Create9)GetProcAddress(m, "Direct3DCreate9");
    IDirect3D9* d = c9 ? c9(D3D_SDK_VERSION) : nullptr;
    if (!d) { Log("d3d capture: dummy Direct3DCreate9 failed"); return 0; }
    D3DPRESENT_PARAMETERS pp = {}; pp.Windowed = TRUE; pp.SwapEffect = D3DSWAPEFFECT_DISCARD; pp.BackBufferFormat = D3DFMT_UNKNOWN; pp.hDeviceWindow = w;
    IDirect3DDevice9* dev = nullptr;
    PFN_CreateDevice cd = o_CreateDevice ? o_CreateDevice : (PFN_CreateDevice)(*(void***)d)[16];
    HRESULT hr = cd(d, D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, w, D3DCREATE_SOFTWARE_VERTEXPROCESSING | D3DCREATE_MULTITHREADED, &pp, &dev);
    if (FAILED(hr) || !dev) { Log("d3d capture: dummy CreateDevice failed 0x%08lX", (unsigned long)hr); return 0; }
    HookDevice(dev, "dummy device (shared vtable)");
    return 0;   // dummy device intentionally kept alive (releasing could free the patched vtable's owner state)
}
