import java.nio.file.*;
import java.lang.reflect.*;
import java.awt.image.BufferedImage;
public final class VerifyCapture extends ClassLoader {
 public static void main(String[] a) throws Exception {
  Class<?> gdi=Class.forName("com.sun.jna.platform.win32.GDI32");
  for(Method m:gdi.getMethods()) if(m.getName().equals("BitBlt"))System.out.println(m.toGenericString());
  byte[] bytes=Files.readAllBytes(Path.of(a[0]));Class<?> cls=new VerifyCapture().defineClass("o0o002C239B89.O0o002C231F41",bytes,0,bytes.length);
  System.out.println("Verified methods="+cls.getDeclaredMethods().length);
  Class<?> guide=Class.forName("com.tourbox.model.jna.GuideUser32");Object user=guide.getField("INSTANCE").get(null);guide.getMethod("SetThreadDpiAwarenessContext",long.class).invoke(user,-4L);
  Class<?> ptr=Class.forName("com.sun.jna.Pointer"), hwnd=Class.forName("com.sun.jna.platform.win32.WinDef$HWND");Object handle=hwnd.getConstructor(ptr).newInstance(ptr.getConstructor(long.class).newInstance(Long.parseLong(a[1],16)));
  BufferedImage image=(BufferedImage)cls.getMethod("o0o002C231EAB",hwnd).invoke(null,handle);
  javax.imageio.ImageIO.write(image,"png",Path.of(a[2]).toFile());
  Class<?> qr=Class.forName("o0o002C239B89.O0o002C232A26");Object result=qr.getMethod("o0o002C232A25",BufferedImage.class).invoke(null,image);
  System.out.println("Capture="+image.getWidth()+"x"+image.getHeight()+" QR decoded="+(result!=null));
 }
}
