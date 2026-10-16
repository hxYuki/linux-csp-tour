/* TourBox Console 5.12.0 Wine compatibility: bound HKL synchronization to one
 * ActivateKeyboardLayout attempt per observed foreground-layout change.
 * Expected original class SHA256:
 * 1578f764f13c509069b4d43b0100513bff6ab97b596862941af473c8d3fd0e45
 * No class dumping, device access, registry changes, or file logging.
 */
#include <jvmti.h>

typedef void *HANDLE;
typedef unsigned int DWORD;
typedef int BOOL;
__declspec(dllimport) HANDLE __stdcall GetStdHandle(DWORD);
__declspec(dllimport) BOOL __stdcall WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);

_Static_assert(sizeof(void *) == 8, "x64 required");
_Static_assert(sizeof(jint) == 4 && sizeof(jlong) == 8, "JNI ABI mismatch");
_Static_assert(sizeof(jvmtiCapabilities) == 16, "JVMTI ABI mismatch");

void *memset(void *dst, int value, __SIZE_TYPE__ count) {
    unsigned char *p = dst;
    for (__SIZE_TYPE__ i = 0; i < count; ++i) p[i] = (unsigned char)value;
    return dst;
}

#define EXPECTED_LENGTH 6312u
#define EXPECTED_FNV 0xf35891c3u
#define EXPECTED_CODE_LENGTH 672u
#define TARGET_CLASS "o0o002C239B88/O0o002C235C7A$1"
static unsigned int reported_patch;
static unsigned int reported_refusal;

static unsigned int length_of(const char *s) {
    unsigned int n = 0;
    while (s[n]) ++n;
    return n;
}

static int equal_text(const char *a, const char *b) {
    while (*a && *b && *a == *b) { ++a; ++b; }
    return *a == *b;
}

static int equal_bytes(const unsigned char *a, const unsigned char *b, unsigned int n) {
    for (unsigned int i = 0; i < n; ++i) if (a[i] != b[i]) return 0;
    return 1;
}

static void report(const char *line) {
    HANDLE err = GetStdHandle((DWORD)-12);
    if (err && err != (HANDLE)(long long)-1) {
        DWORD written;
        WriteFile(err, line, length_of(line), &written, 0);
    }
}

static void refuse(const char *line) {
    if (!__atomic_exchange_n(&reported_refusal, 1u, __ATOMIC_RELAXED)) report(line);
}

static unsigned int u2(const unsigned char *p) {
    return ((unsigned int)p[0] << 8) | p[1];
}

static unsigned int u4(const unsigned char *p) {
    return ((unsigned int)p[0] << 24) | ((unsigned int)p[1] << 16) |
           ((unsigned int)p[2] << 8) | p[3];
}

static int room(unsigned int offset, unsigned int count, unsigned int size) {
    return offset <= size && count <= size - offset;
}

static int utf8_is(const unsigned char *p, unsigned int n, const char *s) {
    return length_of(s) == n && equal_bytes(p, (const unsigned char *)s, n);
}

/* Locate the run()V Code attribute structurally. No file offsets are baked in. */
static int find_run_code(const unsigned char *b, unsigned int size, unsigned int *result) {
    if (!room(0, 10, size) || u4(b) != 0xcafebabeu) return 0;
    unsigned int offset = 10, pool_count = u2(b + 8);
    unsigned int run_name = 0, void_desc = 0, code_name = 0;
    for (unsigned int i = 1; i < pool_count; ++i) {
        if (!room(offset, 1, size)) return 0;
        unsigned int tag = b[offset++], count;
        if (tag == 1) {
            if (!room(offset, 2, size)) return 0;
            count = u2(b + offset); offset += 2;
            if (!room(offset, count, size)) return 0;
            if (utf8_is(b + offset, count, "run")) run_name = i;
            if (utf8_is(b + offset, count, "()V")) void_desc = i;
            if (utf8_is(b + offset, count, "Code")) code_name = i;
        } else if (tag == 3 || tag == 4 || tag == 9 || tag == 10 ||
                   tag == 11 || tag == 12 || tag == 17 || tag == 18) count = 4;
        else if (tag == 5 || tag == 6) { count = 8; ++i; }
        else if (tag == 7 || tag == 8 || tag == 16 || tag == 19 || tag == 20) count = 2;
        else if (tag == 15) count = 3;
        else return 0;
        if (!room(offset, count, size)) return 0;
        offset += count;
    }
    if (!run_name || !void_desc || !code_name || !room(offset, 8, size)) return 0;
    offset += 6; // access_flags, this_class, super_class
    unsigned int interfaces = u2(b + offset); offset += 2;
    if (!room(offset, 2u * interfaces, size)) return 0;
    offset += 2u * interfaces;
    for (unsigned int group = 0; group < 2; ++group) { // fields, then methods
        if (!room(offset, 2, size)) return 0;
        unsigned int members = u2(b + offset); offset += 2;
        for (unsigned int member = 0; member < members; ++member) {
            if (!room(offset, 8, size)) return 0;
            int target = group == 1 && u2(b + offset + 2) == run_name &&
                         u2(b + offset + 4) == void_desc;
            unsigned int attributes = u2(b + offset + 6); offset += 8;
            for (unsigned int attr = 0; attr < attributes; ++attr) {
                if (!room(offset, 6, size)) return 0;
                unsigned int name = u2(b + offset), count = u4(b + offset + 2);
                offset += 6;
                if (!room(offset, count, size)) return 0;
                if (target && name == code_name) {
                    if (count < 8 || u4(b + offset + 4) != EXPECTED_CODE_LENGTH ||
                        !room(offset + 8, EXPECTED_CODE_LENGTH, size) ||
                        EXPECTED_CODE_LENGTH > count - 8) return 0;
                    *result = offset + 8;
                    return 1;
                }
                offset += count;
            }
        }
    }
    return 0;
}

static int check_original(const unsigned char *b, unsigned int size, unsigned int *code_offset) {
    if (size != EXPECTED_LENGTH) return 0;
    unsigned int hash = 2166136261u;
    for (unsigned int i = 0; i < size; ++i) hash = (hash ^ b[i]) * 16777619u;
    if (hash != EXPECTED_FNV || !find_run_code(b, size, code_offset)) return 0;
    const unsigned char *code = b + *code_offset;
    static const unsigned char entry[] = {
        0x09,0x37,0x08,0xb8,0x00,0xc7,0x37,0x0a,0xa7,0x00,0x3e
    }; // 447: returnHKL=0, start=time(), goto 517
    static const unsigned char invoke[] = {
        0x16,0x05,0x11,0x01,0x00,0xb8,0x00,0xcd,0x37,0x08
    }; // 491: ActivateKeyboardLayout(desiredHKL, 256), store result
    static const unsigned char backedge[] = {
        0x16,0x08,0x16,0x05,0xb8,0x00,0xd2,0x9a,0xff,0xbe
    }; // 517: compare result != desiredHKL, ifne 458
    static const unsigned char continuation[] = { 0xba,0x00,0xd6,0x00,0x00,0xb8,0x00,0x92 };
    return equal_bytes(code + 447, entry, sizeof(entry)) &&
           equal_bytes(code + 491, invoke, sizeof(invoke)) &&
           equal_bytes(code + 517, backedge, sizeof(backedge)) &&
           equal_bytes(code + 527, continuation, sizeof(continuation));
}

#include "capture_patch.h"
static unsigned int capture_reported;
static void capture_patch(jvmtiEnv *env, jint length, const unsigned char *bytes,
    jint *new_length, unsigned char **new_bytes) {
    if (length != CAPTURE_ORIGINAL_LENGTH || !bytes) return;
    unsigned int hash = 2166136261u;
    for (unsigned int i=0; i<(unsigned int)length; ++i) hash=(hash^bytes[i])*16777619u;
    if (hash != CAPTURE_FNV || !equal_bytes(bytes+CAPTURE_CODE_OFFSET+108,
        capture_call_original,sizeof(capture_call_original))) {
        report("[tourbox-wine-compat] unsupported capture class; left unchanged\r\n");
        return;
    }
    unsigned int size=length+sizeof(capture_cp_extra)+CAPTURE_CODE_DELTA;
    unsigned char *copy=0;
    if ((*env)->Allocate(env,size,&copy)!=JVMTI_ERROR_NONE || !copy) return;
    unsigned int dst=0;
    for(unsigned int i=0;i<CAPTURE_CP_END;++i)copy[dst++]=bytes[i];
    for(unsigned int i=0;i<sizeof(capture_cp_extra);++i)copy[dst++]=capture_cp_extra[i];
    for(unsigned int i=CAPTURE_CP_END;i<CAPTURE_CODE_OFFSET+108;++i)copy[dst++]=bytes[i];
    for(unsigned int i=0;i<sizeof(capture_call_replacement);++i)copy[dst++]=capture_call_replacement[i];
    for(unsigned int i=CAPTURE_CODE_OFFSET+121;i<(unsigned int)length;++i)copy[dst++]=bytes[i];
    for(unsigned int i=0;i<sizeof(capture_fixups)/sizeof(capture_fixups[0]);++i)
        copy[capture_fixups[i].offset]=capture_fixups[i].value;
    *new_length=(jint)size;*new_bytes=copy;
    if(!__atomic_exchange_n(&capture_reported,1u,__ATOMIC_RELAXED))
        report("[tourbox-wine-compat] patched CSP QR capture to BitBlt\r\n");
}

static void JNICALL on_class(jvmtiEnv *env, JNIEnv *jni, jclass redef,
    jobject loader, const char *name, jobject domain, jint length,
    const unsigned char *bytes, jint *new_length, unsigned char **new_bytes) {
    (void)jni; (void)redef; (void)loader; (void)domain;
    if (name && equal_text(name,"o0o002C239B89/O0o002C231F41")) {
        capture_patch(env,length,bytes,new_length,new_bytes);return;
    }
    if (!name || !equal_text(name, TARGET_CLASS)) return;
    unsigned int code_offset = 0;
    if (length <= 0 || !bytes || !check_original(bytes, (unsigned int)length, &code_offset)) {
        refuse("[tourbox-wine-compat] unsupported HKL class bytes; left unchanged\r\n");
        return;
    }
    unsigned char *copy = 0;
    if ((*env)->Allocate(env, length, &copy) != JVMTI_ERROR_NONE || !copy) {
        refuse("[tourbox-wine-compat] JVMTI allocation failed; left unchanged\r\n");
        return;
    }
    for (jint i = 0; i < length; ++i) copy[i] = bytes[i];
    // 455: goto 458 rather than prechecking resultHKL=0 at 517.
    copy[code_offset + 456] = 0x00;
    copy[code_offset + 457] = 0x03;
    // 524: consume compare result and fall through; no retry backedge.
    copy[code_offset + 524] = 0x57; // pop
    copy[code_offset + 525] = 0x00; // nop
    copy[code_offset + 526] = 0x00; // nop
    *new_length = length;
    *new_bytes = copy;
    if (!__atomic_exchange_n(&reported_patch, 1u, __ATOMIC_RELAXED))
        report("[tourbox-wine-compat] patched HKL sync\r\n");
}

JNIEXPORT jint JNICALL Agent_OnLoad(JavaVM *vm, char *options, void *reserved) {
    (void)options; (void)reserved;
    jvmtiEnv *env = 0;
    if ((*vm)->GetEnv(vm, (void **)&env, JVMTI_VERSION_1_2) != JNI_OK || !env) {
        report("[tourbox-wine-compat] JVMTI unavailable\r\n");
        return JNI_ERR;
    }
    jvmtiCapabilities caps = {0};
    caps.can_generate_all_class_hook_events = 1;
    caps.can_retransform_classes = 1;
    jvmtiEventCallbacks callbacks = {0};
    callbacks.ClassFileLoadHook = on_class;
    if ((*env)->AddCapabilities(env, &caps) != JVMTI_ERROR_NONE ||
        (*env)->SetEventCallbacks(env, &callbacks, sizeof(callbacks)) != JVMTI_ERROR_NONE ||
        (*env)->SetEventNotificationMode(env, JVMTI_ENABLE, JVMTI_EVENT_CLASS_FILE_LOAD_HOOK, 0)
            != JVMTI_ERROR_NONE) {
        report("[tourbox-wine-compat] JVMTI hook initialization failed\r\n");
        return JNI_ERR;
    }
    return JNI_OK;
}
