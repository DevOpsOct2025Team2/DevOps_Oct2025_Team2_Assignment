*** Settings ***
Documentation    Admin create user smoke test for the web UI.
Library          SeleniumLibrary
Resource         resources/login_keywords.resource
Test Setup       Open Login Page
Test Teardown    Close Browser Session

*** Test Cases ***
Admin Can Create A Regular User
    [Documentation]    Logs in as admin, creates a user in the admin dashboard, and verifies it appears in user list.
    Login As Admin User
    ${new_username}=    Generate Unique Username
    ${new_password}=    Set Variable    Robot12345
    Create User In Admin Dashboard    ${new_username}    ${new_password}    regular
    User Should Appear In Admin List    ${new_username}
