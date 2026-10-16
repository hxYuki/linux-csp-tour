import java.nio.file.Files;
import java.nio.file.Path;

public final class VerifyPatched extends ClassLoader {
    private Class<?> check(byte[] bytes) {
        return defineClass("o0o002C239B88.O0o002C235C7A$1", bytes, 0, bytes.length);
    }

    public static void main(String[] args) throws Exception {
        Class<?> checked = new VerifyPatched().check(Files.readAllBytes(Path.of(args[0])));
        // Reflection forces method verification, without instantiating or running it.
        if (checked.getDeclaredMethods().length != 3) throw new AssertionError(checked);
        System.out.println("Patched HKL class verified without initialization or execution.");
    }
}
