*** Variables ***
${BASE_URL}           http://localhost:5000
${LOGIN_URL}          ${BASE_URL}/login
${BROWSER}            Chrome
${VALID_USERNAME}     %{TEST_USERNAME=admin}
${VALID_PASSWORD}     %{TEST_PASSWORD=admin12345}
${INVALID_PASSWORD}   wrong-password-123

${USERNAME_INPUT}     id:username
${PASSWORD_INPUT}     id:password
${SIGNIN_BUTTON}      css:button[type="submit"]
${ERROR_MESSAGE}      id:error-message

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
