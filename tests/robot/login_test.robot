*** Settings ***
Documentation    Login feature smoke tests for the web UI.
Library          SeleniumLibrary
Resource         resources/login_keywords.resource
Test Setup       Open Login Page
Test Teardown    Close Browser Session

*** Test Cases ***
Valid User Can Login
    [Documentation]    Uses TEST_USERNAME and TEST_PASSWORD from environment.
    Login With Credentials    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Login Should Succeed

Invalid Password Shows Error Message
    Login With Credentials    ${VALID_USERNAME}    ${INVALID_PASSWORD}
    Login Should Fail With Error
