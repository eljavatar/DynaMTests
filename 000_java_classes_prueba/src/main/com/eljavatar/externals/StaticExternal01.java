package com.eljavatar.externals;

public class StaticExternal01 {

    public static final Integer STATIC_INT_VAL = 10;
    public static final Integer STATIC_INT_VAL_02 = 20;

    private StaticExternal01() {}

    public static boolean methodStatic(String val01) {
        return val01 == null;
    }

}