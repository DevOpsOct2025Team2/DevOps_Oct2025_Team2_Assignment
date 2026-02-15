*** Settings ***
Documentation    Logout feature smoke test for the web UI.
Library          SeleniumLibrary
Resource         resources/login_keywords.resource
Test Setup       Open Login Page
Test Teardown    Close Browser Session

*** Test Cases ***
Logged In User Can Logout
    [Documentation]    Logs in with valid credentials, logs out, and returns to login page.
    Login With Credentials    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Login Should Succeed
    Logout Current User
    Logout Should Redirect To Login
