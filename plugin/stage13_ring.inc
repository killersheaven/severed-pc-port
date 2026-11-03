// ---- Stage 13 (2/2): ring of the last 64 draw calls, dumped on a crash ---------------------------------------------
struct DrawRec
{
    uint32_t n, ret; DWORD tick; uint8_t kind, prim; uint16_t stale; INT base; UINT mi, nv, start, cnt;
    void* vb[2]; UINT vboff[2], vbstr[2], vblen[2]; void* ib; UINT iblen; DWORD ibfmt;
    void* decl; DWORD fvf; void* vs; void* ps; void* tex[4];
};
static DrawRec g_drawRing[64]; static volatile LONG g_drawN = 0;
static const char* kDrawKind[] = { "?", "DP", "DIP", "DPUP", "DIPUP" };
static void RecDraw(int kind, uintptr_t ret, int prim, INT b, UINT mi, UINT nv, UINT s, UINT c)
{
    LONG n = g_drawN; g_drawN = n + 1;
    CheckStreamRecords((uint32_t)n);
    DrawRec& r = g_drawRing[n & 63];
    r.n = (uint32_t)n; r.ret = (uint32_t)ret; r.tick = GetTickCount(); r.kind = (uint8_t)kind; r.prim = (uint8_t)prim; r.stale = (uint16_t)g_staleMask;
    r.base = b; r.mi = mi; r.nv = nv; r.start = s; r.cnt = c;
    for (int i = 0; i < 2; ++i) { r.vb[i] = g_curVB[i]; r.vboff[i] = g_curVBoff[i]; r.vbstr[i] = g_curVBstride[i]; BufInfo* x = FindBuf(g_curVB[i]); r.vblen[i] = x ? x->len : 0; }
    r.ib = g_curIB; { BufInfo* x = FindBuf(g_curIB); r.iblen = x ? x->len : 0; r.ibfmt = x ? x->ifmt : 0; }
    r.decl = g_curDecl; r.fvf = g_curFVF; r.vs = g_curVS; r.ps = g_curPS;
    for (int t = 0; t < 4; ++t) r.tex[t] = g_curTex[t];
}
// One-line description of a D3D object pointer: validity, vtable, what we know about it, dead mark.
static void ObjDesc(char* out, size_t n, void* p)
{
    out[0] = 0;
    if (!p) { snprintf(out, n, "null"); return; }
    int pos = 0;
    uintptr_t a = (uintptr_t)p;
    if (!Readable(a, 8)) pos += snprintf(out + pos, n - pos, "UNREADABLE");
    else
    {
        uintptr_t vt = *(uintptr_t*)a;
        char m[160]; ModOf(m, sizeof(m), vt);
        bool vtOk = Readable(vt, 12);
        uintptr_t f0 = vtOk ? *(uintptr_t*)vt : 0;
        bool inD3d = (vt >= g_d3dLo && vt < g_d3dHi) || (f0 >= g_d3dLo && f0 < g_d3dHi);
        pos += snprintf(out + pos, n - pos, "vt %08X (%s)%s", (unsigned)vt, m[0] ? m : "?", inD3d ? "" : " NOT-D3D");
        int kind = 0; for (LONG i = 0; i < g_nrel; ++i) if ((uintptr_t)g_rel[i].vt == vt) kind = g_rel[i].kind;
        if (kind) pos += snprintf(out + pos, n - pos, " %s", KindName(kind));
    }
    if (BufInfo* b = FindBuf(p)) pos += snprintf(out + pos, n - pos, " buf len %u usage %lX pool %lu%s", b->len, (unsigned long)b->usage, (unsigned long)b->pool, b->fvf == 0xFFFFFFFF ? (b->ifmt == 102 ? " idx32" : " idx16") : "");
    if (TexInfo* t = FindTex(p)) pos += snprintf(out + pos, n - pos, " tex %ux%u lv%u fmt %lu pool %lu", t->w, t->h, t->lv, (unsigned long)t->fmt, (unsigned long)t->pool);
    if (DeclInfo* d = FindDecl(p)) pos += snprintf(out + pos, n - pos, " decl %d elements", d->n);
    if (DeadObj* d = DeadFind(p)) pos += snprintf(out + pos, n - pos, " **RELEASED %lu ms ago from %08X (%s, x%u)**", (unsigned long)(GetTickCount() - d->tick), (unsigned)d->relRet, KindName(d->kind), (unsigned)d->nrel);
}
static void DrawLine(const DrawRec& r, char* out, size_t n)
{
    snprintf(out, n, "#%u %s ret %08X prim %u base %d min %u nv %u start %u cnt %u | vb0 %p+%u s%u len %u | vb1 %p+%u s%u len %u | ib %p len %u fmt %lu | decl %p fvf %lX vs %p ps %p | t0 %p t1 %p t2 %p t3 %p%s",
        r.n, r.kind < 5 ? kDrawKind[r.kind] : "?", r.ret, r.prim, r.base, r.mi, r.nv, r.start, r.cnt,
        r.vb[0], r.vboff[0], r.vbstr[0], r.vblen[0], r.vb[1], r.vboff[1], r.vbstr[1], r.vblen[1], r.ib, r.iblen, (unsigned long)r.ibfmt,
        r.decl, (unsigned long)r.fvf, r.vs, r.ps, r.tex[0], r.tex[1], r.tex[2], r.tex[3], r.stale ? " STALE-BOUND" : "");
}
static void DumpDrawDetail(const char* tag, const DrawRec& r)
{
    char line[1200]; DrawLine(r, line, sizeof(line));
    Log("    %s: %s", tag, line);
    char d[400];
    const char* nm[10] = { "vb0", "vb1", "ib", "decl", "vs", "ps", "t0", "t1", "t2", "t3" };
    void* ob[10] = { r.vb[0], r.vb[1], r.ib, r.decl, r.vs, r.ps, r.tex[0], r.tex[1], r.tex[2], r.tex[3] };
    for (int i = 0; i < 10; ++i)
        if (ob[i]) { ObjDesc(d, sizeof(d), ob[i]); Log("      %s %p: %s", nm[i], ob[i], d); HexLine("        bytes", (uintptr_t)ob[i], 48); }
    if (DeclInfo* x = FindDecl(r.decl))
    {
        char e[600]; int pos = 0;
        for (int i = 0; i < x->n; ++i)
            pos += snprintf(e + pos, sizeof(e) - pos, " [s%u off%u t%u m%u u%u i%u]", x->el[i].Stream, x->el[i].Offset, x->el[i].Type, x->el[i].Method, x->el[i].Usage, x->el[i].UsageIndex);
        Log("      decl elements:%s", e);
    }
    // vertex range check against VB0 (the engine's quad helper draws nv = [state+8] vertices from the 4 MB ring VB)
    if (r.vb[0] && r.vbstr[0] && r.vblen[0])
    {
        unsigned long long end = (unsigned long long)r.vboff[0] + (unsigned long long)((UINT)(r.base > 0 ? r.base : 0) + r.mi + r.nv) * r.vbstr[0];
        Log("      vb0 vertex range end %llu bytes of %u -> %s", end, r.vblen[0], end > r.vblen[0] ? "PAST END" : "ok");
    }
    if (r.ib && r.iblen && r.kind == 2)
    {
        UINT isz = r.ibfmt == 102 ? 4 : 2;
        UINT ni = r.prim == 4 ? r.cnt * 3 : (r.prim == 5 || r.prim == 6) ? r.cnt + 2 : r.prim == 2 ? r.cnt * 2 : r.prim == 3 ? r.cnt + 1 : r.cnt;
        unsigned long long end = (unsigned long long)(r.start + ni) * isz;
        Log("      ib index range end %llu bytes of %u -> %s", end, r.iblen, end > r.iblen ? "PAST END" : "ok");
    }
}
static volatile LONG g_ringDumped = 0;
static void DumpDrawRing()
{
    if (InterlockedIncrement(&g_ringDumped) > 1) { Log("    draw ring: already dumped above"); return; }
    LONG n = g_drawN; if (!n) { Log("    draw ring: no draws recorded"); return; }
    Log("    lock guard: %u guarded locks, %u OVERRUNS, %u lock ranges past end, %u shadow failures, %ld still locked; stream check %d, %u corrupted-record hits", g_lockN, g_overrunN, g_lockRangeN, g_shadowFail, (long)g_nShadow, g_streamChk, g_streamBadN);
    Log("    draw ring: last %d draws (oldest first); stale-guard counts: %u stale binds, %u double releases; %ld release hooks; buffer map %u live, %u rebuilds; dead table resets %u",
        n < 64 ? (int)n : 64, g_staleN, g_doubleRelN, (long)g_nrel, g_bufLive, g_bufRebuilds, g_deadResets);
    char line[1200];
    for (LONG i = (n > 64 ? n - 64 : 0); i < n; ++i) { DrawLine(g_drawRing[i & 63], line, sizeof(line)); Log("      %s", line); }
    const DrawRec& last = g_drawRing[(n - 1) & 63];
    DumpDrawDetail("LAST draw (the one being submitted when the crash happened, if the crash is inside d3d9)", last);
    // the previous draw from the same call site, for comparison
    for (LONG i = n - 2; i >= 0 && i >= n - 64; --i)
        if (g_drawRing[i & 63].ret == last.ret) { DumpDrawDetail("previous draw from the same call site", g_drawRing[i & 63]); break; }
}
// Identify D3D objects among registers and stack words (the d3d9 frames pass the object they are validating).
static void ScanD3DObjects(CONTEXT* c)
{
    char d[400]; int shown = 0;
    const DWORD regs[7] = { c->Eax, c->Ebx, c->Ecx, c->Edx, c->Esi, c->Edi, c->Ebp };
    const char* rn[7] = { "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP" };
    for (int i = 0; i < 7; ++i)
    {
        void* p = (void*)(uintptr_t)regs[i];
        if (FindBuf(p) || FindTex(p) || FindDecl(p) || DeadFind(p)) { ObjDesc(d, sizeof(d), p); Log("    d3d object in %s %p: %s", rn[i], p, d); }
    }
    void* seen[32]; int ns = 0;
    for (int i = 0; i < 512 && shown < 24; ++i)
    {
        uintptr_t a = c->Esp + 4 * i; if (!Readable(a, 4)) break;
        void* p = *(void**)a;
        if ((uintptr_t)p < 0x10000) continue;
        if (!(FindBuf(p) || FindTex(p) || FindDecl(p) || DeadFind(p) || IsVS(p))) continue;
        bool dup = false; for (int j = 0; j < ns; ++j) if (seen[j] == p) dup = true;
        if (dup) continue;
        if (ns < 32) seen[ns++] = p;
        ObjDesc(d, sizeof(d), p); Log("    d3d object at stack[%03X] %p: %s", i * 4, p, d); ++shown;
    }
    if (!shown) Log("    d3d objects on the stack: none recognised");
}
