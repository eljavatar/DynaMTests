package com.eljavatar.externals;

public class ExternalContext01 {

    public ExternalContext01() {
        
    }

    public String methodReference() {
        return "";
    }

    public String methodReference(Integer val) {
        return "" + val;
    }

    public String methodReference(Boolean val) {
        return "" + val;
    }

    private String methodReference(Long val) {
        return "" + val;
    }

    public Integer getSomeIntValue(boolean val1, boolean val2) {
        return 1;
    }

    public Integer getSomeIntValue(boolean val1, String val2) {
        return 2;
    }

    public Integer getSomeIntValue(String val1, boolean val2) {
        return 3;
    }

    private Integer getSomeIntValue(String val1, String val2) {
        return 4;
    }
    
}