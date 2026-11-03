// ---- Stage 14: lock guard + d3d9 stream-record integrity check ----------------------------------------------------
// Door crash analysis (d3d9 10.0, file MD5 648e3dbe…): d3d9 keeps 16 vertex-stream records (28 bytes, vtable
// d3d9+0x1978, built by d3d9+0x82250) in one heap array at [device+0x2EAC]. In both crashes one record's vtable was
// overwritten with d3d9+0x1490 (the texture class vtable) -> heap corruption of d3d9 memory. Managed-pool locks return
// pointers into d3d9's own heap, so an engine write past a locked range lands on d3d9 objects.
// Lock guard: every non-dynamic VB/IB lock and every whole-level 2D texture LockRect is redirected to a private copy
// with guard zones; on Unlock only the locked range is copied back, guard damage is logged and never reaches d3d9.
// Stream check: before each draw the 16 records are verified; the first bad one is logged with its contents.
static int g_lockGuard = 1;          // [Debug] LockGuard=0 turns the shadow copies off
typedef HRESULT (STDMETHODCALLTYPE *PFN_BufLock)(void*, UINT, UINT, void**, DWORD);
typedef HRESULT (STDMETHODCALLTYPE *PFN_BufUnlock)(void*);
typedef HRESULT (STDMETHODCALLTYPE *PFN_TexLock)(void*, UINT, D3DLOCKED_RECT*, const RECT*, DWORD);
typedef HRESULT (STDMETHODCALLTYPE *PFN_TexUnlock)(void*, UINT);
typedef HRESULT (STDMETHODCALLTYPE *PFN_GetLevelDesc)(void*, UINT, D3DSURFACE_DESC*);
struct LockVt { void** vt; void* lock; void* unlock; int kind; };
static LockVt g_lkVt[16]; static volatile LONG g_nlkVt = 0;
static const unsigned kPreGuard = 4096;
struct Shadow { void* obj; UINT level; unsigned char* real; unsigned char* blk; UINT size, post; uint32_t ret; DWORD flags; UINT off, len; int kind; DWORD usage, pool, fmt, w, h; INT pitch; };
static Shadow g_shadow[128]; static volatile LONG g_nShadow = 0;
static unsigned g_lockN = 0, g_overrunN = 0, g_lockRangeN = 0, g_shadowFail = 0;
static const uint32_t kGuardPat = 0xC5A5E5D5u;

static LockVt* LkFind(void** vt) { LONG n = g_nlkVt; for (LONG i = 0; i < n; ++i) if (g_lkVt[i].vt == vt) return &g_lkVt[i]; return nullptr; }
static HRESULT STDMETHODCALLTYPE h_BufLock(void* o, UINT off, UINT sz, void** pp, DWORD fl);
static HRESULT STDMETHODCALLTYPE h_BufUnlock(void* o);
static HRESULT STDMETHODCALLTYPE h_TexLock(void* o, UINT lv, D3DLOCKED_RECT* lr, const RECT* rc, DWORD fl);
static HRESULT STDMETHODCALLTYPE h_TexUnlock(void* o, UINT lv);
// Hook Lock/Unlock on the vtable of p. kind: K_VB / K_IB (slots 11/12) or K_TEX for IDirect3DTexture9 (slots 19/20).
// Only called from CreateVertexBuffer / CreateIndexBuffer / CreateTexture, so the vtable type is certain.
static void LockHook(void* p, int kind)
{
    if (!p || !g_lockGuard) return;
    void** vt = *(void***)p;
    if (LkFind(vt)) return;
    EnterCriticalSection(&g_d3dCs);
    if (!LkFind(vt) && g_nlkVt < 16)
    {
        int sl = kind == K_TEX ? 19 : 11;
        void* nl = kind == K_TEX ? (void*)h_TexLock : (void*)h_BufLock;
        void* nu = kind == K_TEX ? (void*)h_TexUnlock : (void*)h_BufUnlock;
        if (vt[sl] != nl)
        {
            LONG n = g_nlkVt;
            g_lkVt[n].vt = vt; g_lkVt[n].lock = vt[sl]; g_lkVt[n].unlock = vt[sl + 1]; g_lkVt[n].kind = kind;
            InterlockedExchange(&g_nlkVt, n + 1);
            DWORD old; VirtualProtect(&vt[sl], 2 * sizeof(void*), PAGE_EXECUTE_READWRITE, &old);
            vt[sl] = nl; vt[sl + 1] = nu;
            VirtualProtect(&vt[sl], 2 * sizeof(void*), old, &old);
            char m[160]; ModOf(m, sizeof(m), (uintptr_t)vt);
            Log("lock guard: %s vtable %p (%s) Lock/Unlock hooked", KindName(kind), vt, m);
        }
    }
    LeaveCriticalSection(&g_d3dCs);
}
static unsigned char* ShadowAlloc(UINT size, UINT* post)
{
    *post = size < 65536 ? 65536 : size;                    // post guard = max(64 KB, locked size)
    unsigned long long tot = (unsigned long long)kPreGuard + size + *post;
    if (tot > 0x7FFFFFFF) return nullptr;
    unsigned char* b = (unsigned char*)malloc((size_t)tot);
    if (!b) return nullptr;
    uint32_t* w = (uint32_t*)b; for (UINT i = 0; i < kPreGuard / 4; ++i) w[i] = kGuardPat;
    uint32_t* q = (uint32_t*)(b + kPreGuard + size);
    if (((uintptr_t)q & 3) == 0) { for (UINT i = 0; i < *post / 4; ++i) q[i] = kGuardPat; }
    else { for (UINT i = 0; i < *post; ++i) b[kPreGuard + size + i] = ((const unsigned char*)&kGuardPat)[i & 3]; }
    return b;
}
static void ShadowAdd(const Shadow& s)
{
    EnterCriticalSection(&g_d3dCs);
    LONG n = g_nShadow;
    if (n < 128) { g_shadow[n] = s; InterlockedExchange(&g_nShadow, n + 1); }
    else { free(s.blk); ++g_shadowFail; }
    LeaveCriticalSection(&g_d3dCs);
}
static bool ShadowTake(void* o, UINT level, Shadow* out)   // removes the newest shadow of (o, level)
{
    if (!g_nShadow) return false;
    bool ok = false;
    EnterCriticalSection(&g_d3dCs);
    for (LONG i = g_nShadow - 1; i >= 0; --i)
        if (g_shadow[i].obj == o && g_shadow[i].level == level)
        { *out = g_shadow[i]; g_shadow[i] = g_shadow[g_nShadow - 1]; InterlockedExchange(&g_nShadow, g_nShadow - 1); ok = true; break; }
    LeaveCriticalSection(&g_d3dCs);
    return ok;
}
// Copy the locked range back, measure guard damage, log overruns. Returns nothing; frees the block.
static void ShadowFinish(const Shadow& s)
{
    const unsigned char* b = s.blk;
    const unsigned char* pat = (const unsigned char*)&kGuardPat;
    // pre guard: lowest damaged byte
    UINT before = 0;
    for (UINT i = 0; i < kPreGuard; ++i) if (b[i] != pat[i & 3]) { before = kPreGuard - i; break; }
    // post guard: highest damaged byte
    UINT after = 0;
    const unsigned char* pg = b + kPreGuard + s.size;
    for (UINT i = s.post; i > 0; --i) if (pg[i - 1] != pat[(i - 1) & 3]) { after = i; break; }
    memcpy(s.real, b + kPreGuard, s.size);
    if (before || after)
    {
        ++g_overrunN;
        if (g_overrunN <= 40 || (g_overrunN & 255) == 0)
        {
            char m[160]; ModOf(m, sizeof(m), s.ret);
            if (s.kind == K_TEX)
                Log("lock guard: OVERRUN #%u texture %p level %u (%lux%lu fmt %lu pool %lu, pitch %d, %u bytes locked) locked from 0x%08X (%s): %u bytes written past the end%s, %u before the start -> discarded",
                    g_overrunN, s.obj, s.level, (unsigned long)s.w, (unsigned long)s.h, (unsigned long)s.fmt, (unsigned long)s.pool, s.pitch, s.size, s.ret, m, after, after >= s.post ? " (guard full: at least)" : "", before);
            else
                Log("lock guard: OVERRUN #%u %s %p (len %u usage %lX pool %lu) locked off %u size %u flags %lX from 0x%08X (%s): %u bytes written past the end of the lock%s, %u before the start -> discarded",
                    g_overrunN, KindName(s.kind), s.obj, s.len, (unsigned long)s.usage, (unsigned long)s.pool, s.off, s.size, (unsigned long)s.flags, s.ret, m, after, after >= s.post ? " (guard full: at least)" : "", before);
            if (g_overrunN <= 6) { uintptr_t here; asm volatile("movl %%esp, %0" : "=r"(here)); LogStackRets("    lock guard (unlock) stack:", here, 16); FindMeshes("lock guard", here); }
            if (g_overrunN <= 3 && after) HexLine("    first bytes past the end", (uintptr_t)(pg), after < 64 ? after : 64);
        }
    }
    free(s.blk);
}
static HRESULT STDMETHODCALLTYPE h_BufLock(void* o, UINT off, UINT sz, void** pp, DWORD fl)
{
    LockVt* lv = LkFind(*(void***)o);
    PFN_BufLock orig = (PFN_BufLock)(lv ? lv->lock : g_lkVt[0].lock);
    uintptr_t ra = (uintptr_t)__builtin_return_address(0);
    HRESULT hr = orig(o, off, sz, pp, fl);
    if (FAILED(hr) || !pp || !*pp) return hr;
    ++g_lockN;
    BufInfo* bi = FindBuf(o);
    if (!bi || !bi->len) return hr;
    UINT len = bi->len;
    if (off > len || (sz && (unsigned long long)off + sz > len))
    {
        ++g_lockRangeN;
        if (g_lockRangeN <= 20) { char m[160]; ModOf(m, sizeof(m), ra); Log("lock guard: lock range past the end: %s %p len %u off %u size %u flags %lX from 0x%08X (%s)", lv ? KindName(lv->kind) : "buffer", o, len, off, sz, (unsigned long)fl, (unsigned)ra, m); }
    }
    if (!g_lockGuard || (fl & 0x10 /*READONLY*/) || (bi->usage & 0x200 /*DYNAMIC*/) || off >= len) return hr;
    UINT size = sz ? sz : len - off;
    if ((unsigned long long)off + size > len) size = len - off;
    if (!size) return hr;
    Shadow s = {}; s.obj = o; s.level = 0xFFFFFFFF; s.real = (unsigned char*)*pp; s.size = size; s.ret = (uint32_t)ra; s.flags = fl; s.off = off; s.len = len;
    s.kind = lv ? lv->kind : K_VB; s.usage = bi->usage; s.pool = bi->pool;
    s.blk = ShadowAlloc(size, &s.post);
    if (!s.blk) { ++g_shadowFail; return hr; }
    memcpy(s.blk + kPreGuard, s.real, size);
    ShadowAdd(s);
    *pp = s.blk + kPreGuard;
    return hr;
}
static HRESULT STDMETHODCALLTYPE h_BufUnlock(void* o)
{
    LockVt* lv = LkFind(*(void***)o);
    PFN_BufUnlock orig = (PFN_BufUnlock)(lv ? lv->unlock : g_lkVt[0].unlock);
    Shadow s;
    if (ShadowTake(o, 0xFFFFFFFF, &s)) ShadowFinish(s);
    return orig(o);
}
static UINT LevelBytes(DWORD fmt, UINT h, INT pitch, bool* dxt)
{
    *dxt = fmt == 0x31545844u || fmt == 0x32545844u || fmt == 0x33545844u || fmt == 0x34545844u || fmt == 0x35545844u;
    UINT rows = *dxt ? (h + 3) / 4 : h;
    return pitch > 0 ? (UINT)pitch * rows : 0;
}
static HRESULT STDMETHODCALLTYPE h_TexLock(void* o, UINT lvl, D3DLOCKED_RECT* lr, const RECT* rc, DWORD fl)
{
    LockVt* lv = LkFind(*(void***)o);
    PFN_TexLock orig = (PFN_TexLock)(lv ? lv->lock : g_lkVt[0].lock);
    uintptr_t ra = (uintptr_t)__builtin_return_address(0);
    HRESULT hr = orig(o, lvl, lr, rc, fl);
    if (FAILED(hr) || !lr || !lr->pBits || !g_lockGuard || rc || (fl & 0x10)) return hr;
    ++g_lockN;
    D3DSURFACE_DESC d = {};
    PFN_GetLevelDesc gld = (PFN_GetLevelDesc)(*(void***)o)[17];
    if (FAILED(gld(o, lvl, &d)) || (d.Usage & 0x200 /*DYNAMIC*/) || (d.Usage & 1 /*RENDERTARGET*/)) return hr;
    bool dxt; UINT size = LevelBytes((DWORD)d.Format, d.Height, lr->Pitch, &dxt);
    if (!size || size > 0x4000000) return hr;
    Shadow s = {}; s.obj = o; s.level = lvl; s.real = (unsigned char*)lr->pBits; s.size = size; s.ret = (uint32_t)ra; s.flags = fl; s.kind = K_TEX;
    s.usage = d.Usage; s.pool = (DWORD)d.Pool; s.fmt = (DWORD)d.Format; s.w = d.Width; s.h = d.Height; s.pitch = lr->Pitch;
    s.blk = ShadowAlloc(size, &s.post);
    if (!s.blk) { ++g_shadowFail; return hr; }
    memcpy(s.blk + kPreGuard, s.real, size);
    ShadowAdd(s);
    lr->pBits = s.blk + kPreGuard;
    return hr;
}
static HRESULT STDMETHODCALLTYPE h_TexUnlock(void* o, UINT lvl)
{
    LockVt* lv = LkFind(*(void***)o);
    PFN_TexUnlock orig = (PFN_TexUnlock)(lv ? lv->unlock : g_lkVt[0].unlock);
    Shadow s;
    if (ShadowTake(o, lvl, &s)) ShadowFinish(s);
    return orig(o, lvl);
}

// ---- d3d9 stream-record check (layout of d3d9 10.0 as above; skipped automatically if the layout does not match) ----
static IDirect3DDevice9* g_dev = nullptr;
static int g_streamChk = -1;          // -1 unknown, 0 off (layout mismatch), 1 on
static unsigned g_streamBadN = 0;
static uint32_t g_streamTabSeen = 0;
static void CheckStreamRecords(uint32_t drawNo)
{
    if (g_streamChk == 0 || !g_dev || !g_d3dLo) return;
    static uintptr_t owner = 0;
    if (!owner) owner = (uintptr_t)g_dev;
    uint32_t tab = Readable(owner + 0x2EAC, 4) ? *(const uint32_t*)(owner + 0x2EAC) : 0;
    if (!tab) return;
    const uint32_t vtOk = (uint32_t)g_d3dLo + 0x1978;
    if (g_streamChk < 0)
    {
        // first look: the layout must match (all 16 records carry vtable 0x1978 and stream index i)
        if (!Readable(tab, 16 * 28)) { g_streamChk = 0; Log("stream check: table %08X unreadable, off", tab); return; }
        for (int i = 0; i < 16; ++i)
        {
            const uint32_t* r = (const uint32_t*)(tab + 28 * i);
            if (r[0] != vtOk || r[4] != (uint32_t)i) {
                uintptr_t alt = Readable((uintptr_t)g_dev + 0x2BE0, 4) ? *(const uint32_t*)((uintptr_t)g_dev + 0x2BE0) : 0;
                alt = (alt && Readable(alt + 0x20, 4)) ? *(const uint32_t*)(alt + 0x20) : 0;
                if (alt && alt != owner && owner == (uintptr_t)g_dev) { Log("stream check: device %08X record %d = %08X, trying owner %08X", (unsigned)owner, i, r[0], (unsigned)alt); owner = alt; return; }
                g_streamChk = 0; Log("stream check: d3d9 layout differs (record %d = %08X idx %u, expected %08X), off", i, r[0], r[4], vtOk); return; }
        }
        g_streamChk = 1; g_streamTabSeen = tab;
        Log("stream check: on, d3d9 stream records at %08X (16 x 28 bytes)", tab);
        HexLine("stream records", tab, 16 * 28 < 448 ? 16 * 28 : 448);
        return;
    }
    if (tab != g_streamTabSeen) { Log("stream check: table moved %08X -> %08X", g_streamTabSeen, tab); g_streamTabSeen = tab; if (!Readable(tab, 16 * 28)) { g_streamChk = 0; return; } }
    for (int i = 0; i < 16; ++i)
    {
        const uint32_t* r = (const uint32_t*)(tab + 28 * i);
        if (r[0] == vtOk && r[4] == (uint32_t)i) continue;
        ++g_streamBadN;
        if (g_streamBadN <= 5)
        {
            Log("stream check: CORRUPTED d3d9 stream record %d at %08X before draw #%u (vt %08X idx %u, expected vt %08X); lock overruns so far %u, locks %u",
                i, (unsigned)(tab + 28 * i), drawNo, r[0], r[4], vtOk, g_overrunN, g_lockN);
            HexLine("record", tab + 28 * i, 28);
            HexLine("around", tab + 28 * i - 64, 28 + 128);
            if (g_streamBadN == 1) { uintptr_t here; asm volatile("movl %%esp, %0" : "=r"(here)); LogStackRets("    stream check stack:", here, 16); }
        }
        return;
    }
}
