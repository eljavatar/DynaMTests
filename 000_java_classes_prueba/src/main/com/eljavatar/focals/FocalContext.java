package com.eljavatar.focals;

import com.eljavatar.externals.ExternalContext01;
import com.eljavatar.externals.ExternalContext02;
import com.eljavatar.externals.StaticExternal01;
import java.util.List;
import java.util.Map;

import static com.eljavatar.externals.ExternalContext03.getSomeStrFrom03;
import static com.eljavatar.externals.ExternalContext04.getSomeStrFrom04;
import static com.eljavatar.externals.StaticExternal01.STATIC_INT_VAL;
import static java.util.Objects.nonNull;

public class FocalContext extends Parent implements IAction, Clonable {

    private ExternalContext01 ext01;
    // Da prioridad a la clase del package porque no se está importando
    private SamePackageExternal01 fromSamePackExt01 = new SamePackageExternal01();

    public FocalContext() {
        this.ext01 = new ExternalContext01();
    }

    public FocalContext(ExternalContext01 ext01) {
        this.ext01 = ext01;
    }

    public String doSomething(@Size Map.Entry<String, @Nullable String> entry, List<ExternalContext01> listExt, ExternalContext01 ext_01, Map.Entry<String, ExternalContext01> entry01, Object[] arrays) {
        List<String> listStr = listExt.stream()
                .map(ExternalContext01::methodReference)
                .toList();

        entry01.key();
        entry01.value();

        Map.Entry<String, SamePackageExternal01> entry02;
        entry02.key();
        entry02.value();

        final String valStr01 = ext01.methodReference(STATIC_INT_VAL);
        int someInt = STATIC_INT_VAL.intValue();
        int someInt02 = StaticExternal01.STATIC_INT_VAL_02.intValue();
        callSomeMethod(someInt);

        boolean valBool01 = StaticExternal01.methodStatic("some value");

        ext_01.getSomeIntValue(valBool01, nonNull(listExt));
        ext01.getSomeIntValue(nonNull(listStr), "another");
        this.ext01.getSomeIntValue(listStr.get(0), nonNull(ext01));
        this.ext01.getSomeIntValue("", 1L);

        this.runSomeVoid(valStr01);
        runSomeVoid(1L);
        runSomeVoid(true);
        runSomeVoid(nonNull(listStr));

        someMethodFromParent("");

        // Como se está importando la clase, se da preferencia al import que a la clase del mismo paquete
        ExternalContext02 ext02 = new ExternalContext02();
        System.println.out(ext02.getSomeStrFrom02());
        System.println.out(ExternalContext02.getSomeStrFrom02());

        // Como se está importando el método estático, se extraen las 2 (la del import y la del mismo paquete)
        ExternalContext03 ext03 = new ExternalContext03();
        System.println.out(ext03.getSomeStrFrom03());
        System.println.out(getSomeStrFrom03());

        // Como se está importando el método estático, se extraen las 2 (la del import y la del mismo file)
        ExternalContext04 ext04 = new ExternalContext04();
        System.println.out(ext04.getSomeStrFrom04());
        System.println.out(getSomeStrFrom04());

        fromSamePackExt01.getSomeStrFromSamePackExt01();

        return "value";
    }

    public void callSomeMethod(int val) {

    }

    public void runSomeVoid(String val) {

    }

    public void runSomeVoid(Long val) {

    }

    private void runSomeVoid(Boolean val) {

    }

    private void runSomeVoid(Integer val) {

    }
    
}


class ExternalContext04 {

    public static <T> StringBuilder getSomeStrFrom04() {
        return "same file";
    }

    public static String getSomeStrFrom05() {
        return "same file";
    }

}

class ExternalContext04Test {

    public static <T> StringBuilder getSomeStrFrom04() {
        return "same file";
    }

    public void testAlgo() {
        ExternalContext04 ext = new ExternalContext04();
        ext.getSomeStrFrom05();
        // ext.getSomeStrFrom04();
    }

}
