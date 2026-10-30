from pathlib import Path
import argparse,tempfile,subprocess,shutil
p=argparse.ArgumentParser();p.add_argument('fixture_dir',type=Path);p.add_argument('patched_class',type=Path);args=p.parse_args()
fixture=args.fixture_dir.resolve()
with tempfile.TemporaryDirectory(prefix='tourbox-picker-regression-') as folder:
 root=Path(folder);src=root/'src';out=root/'classes';src.mkdir();out.mkdir()
 files={
 'org/apache/log4j/Logger.java':'package org.apache.log4j; public class Logger {public void info(Object o){} public void debug(Object o){}}',
 'org/apache/log4j/LogManager.java':'package org.apache.log4j; public class LogManager {public static Logger getLogger(Class<?> c){return new Logger();}}',
 'org/eclipse/swt/widgets/Display.java':'''package org.eclipse.swt.widgets; public class Display {public static java.util.List<Runnable> queue=new java.util.ArrayList<>(); public void timerExec(int ms,Runnable r){queue.add(r);} public void asyncExec(Runnable r){queue.add(r);} }''',
 'o0o002C239BAC/O0o002C2322B5.java':'package o0o002C239BAC; public class O0o002C2322B5 {public org.eclipse.swt.widgets.Display o0o002C231A89(){return new org.eclipse.swt.widgets.Display();}}',
 'o0o002C239BAC/O0o002C233594.java':'package o0o002C239BAC; public class O0o002C233594 {public static O0o002C2322B5 o0o002C23281E=new O0o002C2322B5();}',
 'o0o002C239BAC/O0o002C234CF1.java':'package o0o002C239BAC; public class O0o002C234CF1 {public static boolean o0o002C234C64=false;}',
 'o0o002C239B6C/O0o002C23589B.java':'''package o0o002C239B6C; public class O0o002C23589B {public static boolean open,resident;static O0o002C23589B instance=new O0o002C23589B();public static O0o002C23589B o0o002C235678(){return instance;}public boolean o0o002C2335C2(){return open;}public boolean o0o002C2336E5(){return resident;}}''',
 'o0o002C239B89/O0o002C2342A9.java':'package o0o002C239B89; public class O0o002C2342A9 {public static boolean open;public boolean o0o002C2335C2(){return open;}}',
 'o0o002C239B71/O0o002C235B41.java':'''package o0o002C239B71; public class O0o002C235B41 {public static boolean resident;static O0o002C235B41 instance=new O0o002C235B41();public static o0o002C239B89.O0o002C2342A9 o0o002C232E92(){return new o0o002C239B89.O0o002C2342A9();}public static O0o002C235B41 o0o002C235B35(){return instance;}public boolean o0o002C2336E5(){return resident;}}''',
 'o0o002C239B89/O0o002C23296F.java':'package o0o002C239B89; public class O0o002C23296F {public static int altDowns;public static void o0o002C2322B1(){altDowns++;}}',
 'PickerRegression.java':'''import java.lang.reflect.*;import java.util.*;
import o0o002C239BAC.O0o002C23488D;import o0o002C239B89.O0o002C2342A9;import o0o002C239B89.O0o002C23296F;import o0o002C239B71.O0o002C235B41;import o0o002C239B6C.O0o002C23589B;import org.eclipse.swt.widgets.Display;
public class PickerRegression {
 static void reset(){Display.queue.clear();O0o002C2342A9.open=false;O0o002C235B41.resident=false;O0o002C23589B.open=false;O0o002C23589B.resident=false;O0o002C23296F.altDowns=0;}
 static void schedule(){O0o002C23488D.o0o002C2345F2(36,true,false);}
 static void fire() throws Exception {
  Field f=O0o002C23488D.class.getDeclaredField("o0o002C2344F8");f.setAccessible(true);Object timer=f.get(null);
  Field due=timer.getClass().getDeclaredField("o0o002C2344F6");due.setAccessible(true);due.setLong(timer,0);
  List<Runnable> jobs=new ArrayList<>(Display.queue);Display.queue.clear();for(Runnable r:jobs)r.run();
 }
 static void expect(int count,String scenario){if(O0o002C23296F.altDowns!=count)throw new AssertionError(scenario+" unexpected Alt downs="+O0o002C23296F.altDowns);}
 public static void main(String[] a)throws Exception {
  boolean baseline=a[0].equals("baseline");reset();O0o002C2342A9.open=true;schedule();schedule();O0o002C2342A9.open=false;fire();
  expect(baseline?2:0,"R1 repeated then A released");System.out.println(baseline?"PICKER_BASELINE_REPRODUCED: 2 ghost Alt downs after close":"PICKER_CLOSED: no ghost Alt down");
  if(baseline)return;
  for(int count:new int[]{1,2,3,10,32,100}){reset();O0o002C2342A9.open=true;for(int i=0;i<count;i++)schedule();O0o002C2342A9.open=false;fire();expect(0,"rapid count="+count);}
  reset();O0o002C2342A9.open=true;schedule();fire();expect(1,"CSP remains held: restore retained");
  reset();O0o002C23589B.open=true;schedule();fire();expect(1,"LR remains held: restore retained");
  reset();O0o002C2342A9.open=true;schedule();O0o002C235B41.resident=true;fire();expect(0,"CSP switched to resident");
  reset();O0o002C23589B.open=true;schedule();O0o002C23589B.open=false;fire();expect(0,"LR picker closed");
  System.out.println("PICKER_REGRESSION_PASS: closed/resident suppressed; active CSP/LR restoration retained");
 }
}'''
 }
 for n,s in files.items():q=src/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(s)
 subprocess.run(['javac','-cp',str(fixture),'-d',str(out),*[str(src/n) for n in files]],check=True)
 target=out/'o0o002C239BAC/O0o002C23488D.class'
 for name in ['O0o002C23488D.class','O0o002C23488D$O0o002C2344F9.class']:shutil.copyfile(fixture/'o0o002C239BAC'/name,out/'o0o002C239BAC'/name)
 cp=str(out)+':'+str(fixture)
 subprocess.run(['java','-Xverify:all','-cp',cp,'PickerRegression','baseline'],check=True)
 shutil.copyfile(args.patched_class,target)
 subprocess.run(['java','-Xverify:all','-cp',cp,'PickerRegression','patched'],check=True)
