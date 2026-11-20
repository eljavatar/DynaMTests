package com.eljavatar.focals;

import org.junit.Test;

import static org.junit.Assert.assertEquals;

/**
 * Minimal fixture test class required by tests/TEST_PLAN.md section C.3.
 *
 * It contains exactly seven JUnit test methods, each one exercising a
 * specific path of match_test_cases() (name matching, Test suffix,
 * single invocation, overload insensitivity, ambiguity, zero invocations
 * and dependency belonging to another class).
 */
public class FocalContextTest {

    @Test
    public void testDoSomething() {
        assertEquals("value", new FocalContext().doSomething(null, null, null, null, null));
    }

    @Test
    public void DoSomethingTest() {
        assertEquals("value", new FocalContext().doSomething(null, null, null, null, null));
    }

    @Test
    public void verifyBehaviour() {
        new FocalContext().runSomeVoid("x");
    }

    @Test
    public void runSomeVoidTest() {
        new FocalContext().runSomeVoid(1L);
    }

    @Test
    public void verifyAmbiguous() {
        new FocalContext().runSomeVoid("x");
        new FocalContext().callSomeMethod(1);
    }

    @Test
    public void verifyNoInvocation() {
        assertEquals(1, 1);
    }

    @Test
    public void verifyOtherClass() {
        new SamePackageExternal01().getSomeStrFromSamePackExt01();
    }
}
