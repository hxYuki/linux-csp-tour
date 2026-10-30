/* TourBox Console 5.12.0: repeated modifiers and button release-cache ordering.
 * Private input fixture SHA256:
 * 49934fb99fb768815fd93d255474a1e0bcbb18adc1e651df621bebe3c03d2f24
 * Leaves vendor files and existing HKL / capture compatibility agent intact.
 */
#include <jvmti.h>
typedef void *HANDLE;
typedef unsigned int DWORD;
typedef int BOOL;
__declspec(dllimport) HANDLE __stdcall GetStdHandle(DWORD);
__declspec(dllimport) BOOL __stdcall WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);
_Static_assert(sizeof(void *) == 8, "x64 required");
_Static_assert(sizeof(jvmtiCapabilities) == 16, "JVMTI ABI mismatch");

void *memset(void *dst, int v, __SIZE_TYPE__ n) {
    unsigned char *p = dst;
    for (__SIZE_TYPE__ i = 0; i < n; ++i) p[i] = (unsigned char)v;
    return dst;
}
#define TARGET_CLASS "o0o002C239BA7/O0o002C234E69"
#define ORIGINAL_LENGTH 17801u
#define ORIGINAL_FNV 0x740fc755u
#define PATCH_OFFSET 14653u
#define BUTTON_EXIT_OFFSET 14411u
#define BUTTON_FRAMES_OFFSET 15738u
static const unsigned char button_frames_original[] = {
    0x1b,0xff,0x00,0x02,0x00,0x0a,0x01,0x01,0x01,0x01,
    0x01,0x01,0x01,0x01,0x01,0x07,0x02,0x9a,0x00,0x00
};
static const unsigned char button_frames_patched[] = {
    0xff,0x00,0x1b,0x00,0x0a,0x01,0x01,0x01,0x01,0x01,
    0x01,0x01,0x01,0x01,0x07,0x02,0x9a,0x00,0x00,0x02
};
static unsigned int reported;
static int same(const char *a, const char *b) {
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}
static void report(const char *s) {
    unsigned int n = 0;
    while (s[n]) ++n;
    HANDLE h = GetStdHandle((DWORD)-12);
    if (h && h != (HANDLE)(long long)-1) {
        DWORD done;
        WriteFile(h, s, n, &done, 0);
    }
}
static int supported(jint n, const unsigned char *b) {
    if (!b || n != ORIGINAL_LENGTH) return 0;
    unsigned int h = 2166136261u;
    for (unsigned int i = 0; i < ORIGINAL_LENGTH; ++i) h = (h ^ b[i]) * 16777619u;
    static const unsigned char old[] = {0x1c,0x03,0xb8,0x01,0x57,0x57};
    if (h != ORIGINAL_FNV) return 0;
    for (unsigned int i = 0; i < sizeof(old); ++i)
        if (b[PATCH_OFFSET+i] != old[i]) return 0;
    if (b[BUTTON_EXIT_OFFSET] != 0xa7 || b[BUTTON_EXIT_OFFSET+1] != 0x02 ||
        b[BUTTON_EXIT_OFFSET+2] != 0x37) return 0;
    for (unsigned int i=0; i<sizeof(button_frames_original); ++i)
        if (b[BUTTON_FRAMES_OFFSET+i] != button_frames_original[i]) return 0;
    return 1;
}
#include "picker_patch.h"
static void patch_picker(jvmtiEnv *env,jint n,const unsigned char *b,jint *new_n,unsigned char **new_b) {
    if(!b || n!=PICKER_INPUT_LENGTH){report("[tourbox-modifier-fix] unsupported picker class; left unchanged\r\n");return;}
    unsigned int hash=2166136261u;
    for(unsigned int i=0;i<PICKER_INPUT_LENGTH;i++)hash=(hash^b[i])*16777619u;
    if(hash!=PICKER_FNV){report("[tourbox-modifier-fix] unsupported picker hash; left unchanged\r\n");return;}
    unsigned char *copy=0;
    if((*env)->Allocate(env,PICKER_OUTPUT_LENGTH,&copy)!=JVMTI_ERROR_NONE || !copy)return;
    unsigned int src=0,dst=0;
    for(unsigned int e=0;e<sizeof(picker_edits)/sizeof(picker_edits[0]);e++) {
        const PickerEdit *edit=&picker_edits[e];
        while(src<edit->offset)copy[dst++]=b[src++];
        src+=edit->remove;
        for(unsigned int i=0;i<edit->add;i++)copy[dst++]=edit->data[i];
    }
    while(src<PICKER_INPUT_LENGTH)copy[dst++]=b[src++];
    *new_n=PICKER_OUTPUT_LENGTH;*new_b=copy;
    report("[tourbox-modifier-fix] guarded delayed picker Alt restore v3\r\n");
}
static void JNICALL on_class(jvmtiEnv *env, JNIEnv *jni, jclass redef,
    jobject loader, const char *name, jobject domain, jint n,
    const unsigned char *b, jint *new_n, unsigned char **new_b) {
    (void)jni; (void)redef; (void)loader; (void)domain;
    if(name && same(name,PICKER_CLASS)){patch_picker(env,n,b,new_n,new_b);return;}
    if (!name || !same(name, TARGET_CLASS)) return;
    if (!supported(n, b)) {
        report("[tourbox-modifier-fix] unsupported class; left unchanged\r\n");
        return;
    }
    unsigned char *copy = 0;
    if ((*env)->Allocate(env, n, &copy) != JVMTI_ERROR_NONE || !copy) return;
    for (jint i = 0; i < n; ++i) copy[i] = b[i];
    /* sendShortcut @454: previous same-mask branch was a no-op comparison.
     * Replace with sendModifiers(mask, true, platformFlag). Same six bytes,
     * same empty entry/exit stack, unchanged branch targets and StackMapTable.
     * Modifier changes, natural keys, releases, timer and locks are retained.
     */
    static const unsigned char replacement[] = {0x1b,0x04,0x1d,0xb8,0x02,0x66};
    for (unsigned int i = 0; i < sizeof(replacement); ++i)
        copy[PATCH_OFFSET+i] = replacement[i];
    /* sendShortcut @212: button path used goto 779 (unlock), bypassing
     * invalidateReleaseCache() @776. Entry invalidation @79 is outside the
     * class monitor, so a preceding key-up can overwrite it before this
     * button reasserts Alt. Use the existing @776 cleanup while still locked.
     * No new branch target, instruction, API call, or lock is added.
     */
    copy[BUTTON_EXIT_OFFSET+2] = 0x34; /* goto 776 instead of 779 */
    /* @776 now merges button and rotary paths: discard rotary-only locals
     * 10..15 at this common cleanup. Move the original @779 full frame to
     * @776 (delta 27), then use a same_frame at @779 (delta 2). Same total
     * size, same two frame locations, unchanged stack and remaining frames.
     */
    for (unsigned int i=0; i<sizeof(button_frames_patched); ++i)
        copy[BUTTON_FRAMES_OFFSET+i]=button_frames_patched[i];
    *new_n = n;
    *new_b = copy;
    if (!__atomic_exchange_n(&reported, 1u, __ATOMIC_RELAXED))
        report("[tourbox-modifier-fix] repeated modifiers and button release cache v3\r\n");
}
JNIEXPORT jint JNICALL Agent_OnLoad(JavaVM *vm, char *options, void *reserved) {
    (void)options; (void)reserved;
    jvmtiEnv *env = 0;
    if ((*vm)->GetEnv(vm, (void **)&env, JVMTI_VERSION_1_2) != JNI_OK || !env) return JNI_ERR;
    jvmtiCapabilities caps = {0};
    caps.can_generate_all_class_hook_events = 1;
    caps.can_retransform_classes = 1;
    jvmtiEventCallbacks callbacks = {0};
    callbacks.ClassFileLoadHook = on_class;
    if ((*env)->AddCapabilities(env, &caps) != JVMTI_ERROR_NONE ||
        (*env)->SetEventCallbacks(env, &callbacks, sizeof(callbacks)) != JVMTI_ERROR_NONE ||
        (*env)->SetEventNotificationMode(env, JVMTI_ENABLE, JVMTI_EVENT_CLASS_FILE_LOAD_HOOK, 0) != JVMTI_ERROR_NONE)
        return JNI_ERR;
    report("[tourbox-modifier-fix] agent ready v3\r\n");
    return JNI_OK;
}
