import static org.junit.Assert.assertEquals;
import static org.junit.Assertion.SOME_VAR;
import static org.mockito.Mockito.when;
import static java.lang.Boolean.TRUE;
import org.junit.Assert;
import org.junit.Assert;


// <FCTX>
// // Focal Class
// public class Taxes {
//     // Focal Method
//     public String calculateAndFormatIva(double value, Country country) {
//         double iva = calculateIva(value);
//         if (country != null) {
//             CountrySettings countrySettings = appSettings.getCountrySettings(country);
//             return countrySettings.applyCurrencyFormat(iva);
//         }
//         return applyDefaultFormat(iva);
//     }
//     // Public Constructors
//     public Taxes();
//     public Taxes(AppSettings);
//     // Public Method Signatures invocated from Focal Method
//     public double calculateIva(double);
//     // Private Fields and Method Signatures invocated from Focal Method
//     private AppSettings appSettings;
//     private String applyDefaultFormat(double);
// }
// </FCTX>
// <ECTX>
// // External Class 1
// public class AppSettings {
//     // Public Constructors from External Class
//     public AppSettings();
//     // Method Signatures invocated from Focal Method
//     public CountrySettings getCountrySettings(Country);
// }
// // External Class 2
// public class CountrySettings {
//     public CountrySettings(Country);
//     public String applyCurrencyFormat(double);
// }
// </ECTX>



// // Focal Class
// public class Taxes {
//     // Focal Method
//     public String calculateAndFormatIva(double value, Country country) {
//         double iva = calculateIva(value);
//         if (country != null) {
//             CountrySettings countrySettings = appSettings.getCountrySettings(country);
//             return countrySettings.applyCurrencyFormat(iva);
//         }
//         return applyDefaultFormat(iva);
//     }
//     // Constructors
//     public Taxes();
//     public Taxes(AppSettings);
//     // Public Method Signatures
//     public double calculateIva(double);
//     public double calculateIncomeTax(double);
//     public String calculateAndFormatIncomeTax(double, Country);
//     public double calculateDividendTax(double);
//     public String calculateAndFormatDividendTax(double, Country);
//     public double calculateWealthTax(double);
//     public String calculateAndFormatWealthTax(double, Country);
// }



@AllConstructors
public class MyClass<T> extends Parent implements IAction, Clonable {

    public static final String STATIC_VAR = "Some static value";

    private ConstructorConstructor obj = new Object();

    @Mock
    private ObjectConstructor other;

    private Long    [] values;

    private MyClass otherClass;

    
    @Test
    public <T> void testSerialization(@Size Map.Entry<String, @Nullable String> entry, MyClass myClass, Map<String, Object> map, Integer someInteger, @NotNull int value[], Type... type) {
        assertThat(FieldNamingPolicy.separateCamelCase(pair[0], '_')).isEqualTo(pair[1]);


        OtraClase otherClass = new Object();
        other.changeValue = 1;

        ClaseArray<MyClass>[] arr = new ClaseArray[1];
        arr[0].callFromArray();

        obj.methodCalledWithoutThis();
        
        
        Objeto object = Mockito.mock(Objeto.class);
        //when(other.someAction()).thenReturn(1);
        //addType(Roshambo);
        //new GraphAdapterBuilder().addType(Roshambo.class);
        //Assert.assertEquals("1", "2");
        assertEquals("1", "2");
        Roshambo rock = new Roshambo("ROCK ");
        Roshambo scissors = new Roshambo("SCISSORS ");
        Integer valInt = 3;
        rock.beats = Integer.MAX_VALUE;
        rock.beats = valInt.next();
        rock.beats = valInt.some;
        rock.beats = SOME_VAR.value;
        rock.beats = this.other.mockValue;

        new MyClass().other.methodNext();

        new MyClass().someMethodCaller01().someInvocated02(new Roshambo());
        //new MyClass().someMethodCaller01(valInt, value, "").someInvocated02(new Roshambo());
        //new MyClass().someMethodCaller01(valInt, value, "").someInvocated03(new Type());
        //new MyClass().someMethodCaller01(valInt, value, "").somethingType();

        list.stream().forEach(System.out::println);
        list.stream().forEach(Integer::longValue);
        list.stream().forEach(someInteger::valueOf);
        list.stream().forEach(MyClass::new);
        list.stream().forEach(MyClass[]::new);
        someMethodLambda(MyClass::methodReference01);
        list.stream().forEach(otherClass::methodReference02);
        list.stream().forEach(this.otherClass::methodReference06);
        list.stream().forEach(ObjectConstructor::new);
        list.stream().forEach(ObjectConstructor[]::new);
        list.stream().forEach(ConstructorConstructor::methodReference03);
        list.stream().forEach(other::methodReference04);
        list.stream().forEach(this.other::methodReference05);

        try (Writer w = new Writer(); 
                InnerResource inner = new InnerResource()) {
        	w.open();
            inner.close();
        } catch (Exception | RuntimeException e) {
        }

        for (Type2 t : list) {
            t.callIntoForEach();
        }

        MyClass.some04();
        rock.beats = MyClass.FIELD_04;

        new MyClass().some03();
        new MyClass().field03;
        new MyOtherClass().llamadaToOtherMethod();
        rock.beats = new MyOtherClass().llamadaToOtherFiel;

        new String().trim();

        new SomeClass().concat(new ElJavatar[0]);
        new SomeClass().concat(new ElJavatar());


        rock.beats = value[0].trim();
        rock.beats = value[0].MY_STRING;
        rock.beats = type[0].somethingType();
        rock.beats = type[0].somethingType(rock.beats);
        rock.beats = type[0].MY_TYPE;

        rock.beats = myClass.valueInClass;
        rock.beats = myClass.obj;
        rock.beats = myClass.methodInClass(rock.beats);
        rock.beats = myClass.methodInClass(valInt);
        rock.beats = myClass.methodInClass(rock);
        
        rock.beats = this.otherClass.otherValueInClass;
        rock.beats = this.otherClass.otherMethodInvocation();

        rock.beats = this.obj.methodAccessedByThis();

        rock.beats = value.length;
        rock.beats = Long.MIN_VALUE;

        super.parent.val1 = 1;
        this.parent.val2 = 1;

        //rock.beats = value.LITERAL;
        this.obj.beats = someMethod1(Assert.OTHER_VAR);
        this.obj.beats2 = this.someMethod2(Assert.OTHER_VAR);
        rock.peeks.parser = some.val;
        this.obj = super.someMethod3(scissors.some);
        //GsonBuilder gsonBuilder = new GsonBuilder();
        //gsonBuilder.getValue();
        //new GraphAdapterBuilder().addType(Roshambo.class).registerOn(gsonBuilder);
    }
    

    public Type someMethodCaller01(int val, Integer[] val2, String val3) {

    }

    public MyClass someMethodCaller01(int val, Integer[] val2, Map<?, ?> map) {

    }

    //public MyClass some01(int val, Integer[] val2, Long val3) {

    //}

    //public MyClass some01(String val, String val2, String val3) {

    //}

    //public Integer some02() {
        
    //}
/*
    public void set01(ObjectConstructor other) { // Esta fallando
        this.other = other;
    }

    public ObjectConstructor set02(ObjectConstructor other) {
        this.other = other;
        return other;
    }

    public void set03(ObjectConstructor oth) {
        ObjectConstructor other = oth;
    }

    public void set04(ObjectConstructor oth) {
        ObjectConstructor other = oth;
        this.other = oth;
    }

    public ObjectConstructor get05(String val) {
        return val;
    }
*/
    class Objeto {
        private String val1;
        
        public Objeto() {
            this.val1 = "Hola Mundo";
        }
    }

}

/*
class MyObject {
    private String val1;
    
    public MyObject() {
        val1();
        //String val1 = "Hola Mundo";
    }

    public String val1() {
        return "";
    }
}
*/