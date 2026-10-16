#include <assert.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include "compat.c"

HANDLE GetStdHandle(DWORD kind) { (void)kind; return (HANDLE)2; }
BOOL WriteFile(HANDLE handle, const void *data, DWORD count, DWORD *done, void *overlapped) {
    (void)handle; (void)overlapped;
    long n = write(2, data, count);
    *done = n < 0 ? 0 : (DWORD)n;
    return n >= 0;
}
static jvmtiError allocate(jvmtiEnv *env, jlong count, unsigned char **out) {
    (void)env;
    *out = malloc((unsigned long)count);
    return *out ? JVMTI_ERROR_NONE : JVMTI_ERROR_OUT_OF_MEMORY;
}

int main(int argc, char **argv) {
    assert(argc == 3);
    unsigned char input[EXPECTED_LENGTH + 1];
    int fd = open(argv[1], O_RDONLY);
    assert(fd >= 0);
    long length = read(fd, input, sizeof(input));
    close(fd);
    assert(length == EXPECTED_LENGTH);

    unsigned int code = 0;
    assert(check_original(input, EXPECTED_LENGTH, &code));
    assert(code == 4626); // fixture assertion only; production parser finds this.
    for (unsigned int n = 0; n < code + EXPECTED_CODE_LENGTH; ++n)
        assert(!find_run_code(input, n, &code));

    struct jvmtiInterface_1_ functions = {0};
    functions.Allocate = allocate;
    jvmtiEnv env = &functions;
    jint new_length = 0;
    unsigned char *output = 0;
    on_class(&env, 0, 0, 0, TARGET_CLASS, 0, EXPECTED_LENGTH, input, &new_length, &output);
    assert(output && new_length == EXPECTED_LENGTH);
    assert(output[code + 455] == 0xa7 && output[code + 456] == 0 && output[code + 457] == 3);
    assert(output[code + 524] == 0x57 && output[code + 525] == 0 && output[code + 526] == 0);
    unsigned int changes = 0;
    for (unsigned int i = 0; i < EXPECTED_LENGTH; ++i) {
        if (input[i] == output[i]) continue;
        assert(i == code + 457 || i == code + 524 || i == code + 525 || i == code + 526);
        ++changes;
    }
    assert(changes == 4);
    fd = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0600);
    assert(fd >= 0 && write(fd, output, EXPECTED_LENGTH) == EXPECTED_LENGTH);
    close(fd);
    free(output);

    output = 0; new_length = 0;
    on_class(&env, 0, 0, 0, "other/Class", 0, EXPECTED_LENGTH, input, &new_length, &output);
    assert(!output && !new_length);
    on_class(&env, 0, 0, 0, TARGET_CLASS, 0, EXPECTED_LENGTH - 1, input, &new_length, &output);
    assert(!output && !new_length);
    input[0] ^= 1;
    on_class(&env, 0, 0, 0, TARGET_CLASS, 0, EXPECTED_LENGTH, input, &new_length, &output);
    assert(!output && !new_length);
    return 0;
}
