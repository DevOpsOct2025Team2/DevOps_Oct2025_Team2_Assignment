*** Variables ***
${BASE_URL}           http://localhost:5000
${LOGIN_URL}          ${BASE_URL}/login
${BROWSER}            Chrome
${VALID_USERNAME}     %{TEST_USERNAME=admin}
${VALID_PASSWORD}     %{TEST_PASSWORD=admin12345}
${INVALID_PASSWORD}   wrong-password-123
${ADMIN_USERNAME}     %{TEST_ADMIN_USERNAME=admin}
${ADMIN_PASSWORD}     %{TEST_ADMIN_PASSWORD=admin12345}

${USERNAME_INPUT}     id:username
${PASSWORD_INPUT}     id:password
${SIGNIN_BUTTON}      css:button[type="submit"]
${ERROR_MESSAGE}      id:error-message
${LOGOUT_BUTTON}      css:.logout-btn
${SEARCH_USERNAME_INPUT}         id:searchUsername
${APPLY_FILTERS_BUTTON}          xpath://button[normalize-space()='Apply Filters']
${OPEN_CREATE_USER_BUTTON}       xpath://button[contains(normalize-space(), 'Create User')]
${CREATE_USER_MODAL}             id:create-user-modal
${NEW_USERNAME_INPUT}            id:new-username
${NEW_PASSWORD_INPUT}            id:new-password
${NEW_ROLE_SELECT}               id:new-role
${CREATE_USER_SUBMIT_BUTTON}     xpath://form[@id='create-user-form']//button[@type='submit']
${MESSAGE_BOX}                   id:message

*** Keywords ***
Open Login Page
    Open Browser    ${LOGIN_URL}    ${BROWSER}
    Maximize Browser Window
    Wait Until Element Is Visible    ${USERNAME_INPUT}    10s

Close Browser Session
    Close Browser

Login With Credentials
    [Arguments]    ${username}    ${password}
    Input Text    ${USERNAME_INPUT}    ${username}
    Input Password    ${PASSWORD_INPUT}    ${password}
    Click Button    ${SIGNIN_BUTTON}

Login Should Succeed
    Wait Until Keyword Succeeds    10x    1s    URL Should Match Login Success Pattern

URL Should Match Login Success Pattern
    ${url}=    Get Location
    Should Match Regexp    ${url}    .*/(admin|dashboard)$
    Log    Login redirected to ${url}

Login Should Fail With Error
    Wait Until Element Is Visible    ${ERROR_MESSAGE}    10s
    ${error_text}=    Get Text    ${ERROR_MESSAGE}
    Should Not Be Empty    ${error_text}
    Log    Login error shown: ${error_text}

Logout Current User
    Wait Until Element Is Visible    ${LOGOUT_BUTTON}    10s
    Click Element    ${LOGOUT_BUTTON}
    Handle Alert    ACCEPT

Logout Should Redirect To Login
    Wait Until Keyword Succeeds    10x    1s    URL Should Be Login Page
    Wait Until Element Is Visible    ${USERNAME_INPUT}    10s

URL Should Be Login Page
    ${url}=    Get Location
    Should Match Regexp    ${url}    .*/login$
    Log    Logout redirected to ${url}

Login As Admin User
    Login With Credentials    ${ADMIN_USERNAME}    ${ADMIN_PASSWORD}
    Wait Until Keyword Succeeds    10x    1s    URL Should Be Admin Page

URL Should Be Admin Page
    ${url}=    Get Location
    Should Match Regexp    ${url}    .*/admin$
    Log    Admin login redirected to ${url}

Generate Unique Username
    ${epoch}=    Evaluate    int(__import__('time').time())
    ${username}=    Set Variable    rf_user_${epoch}
    RETURN    ${username}

Create User In Admin Dashboard
    [Arguments]    ${username}    ${password}    ${role}=regular
    Wait Until Element Is Visible    ${OPEN_CREATE_USER_BUTTON}    10s
    Click Element    ${OPEN_CREATE_USER_BUTTON}
    Wait Until Element Is Visible    ${CREATE_USER_MODAL}    10s
    Input Text    ${NEW_USERNAME_INPUT}    ${username}
    Input Password    ${NEW_PASSWORD_INPUT}    ${password}
    Select From List By Value    ${NEW_ROLE_SELECT}    ${role}
    Click Button    ${CREATE_USER_SUBMIT_BUTTON}
    Wait Until Keyword Succeeds    10x    1s    Message Should Contain    User created successfully

Message Should Contain
    [Arguments]    ${expected_text}
    ${message}=    Get Text    ${MESSAGE_BOX}
    Should Contain    ${message}    ${expected_text}

Filter Users By Username
    [Arguments]    ${username}
    Wait Until Element Is Visible    ${SEARCH_USERNAME_INPUT}    10s
    Clear Element Text    ${SEARCH_USERNAME_INPUT}
    Input Text    ${SEARCH_USERNAME_INPUT}    ${username}
    Click Button    ${APPLY_FILTERS_BUTTON}

User Should Appear In Admin List
    [Arguments]    ${username}
    Filter Users By Username    ${username}
    Wait Until Keyword Succeeds    10x    1s    Page Should Contain Element    xpath://tbody[@id='usersTableBody']//td[normalize-space()='${username}']
