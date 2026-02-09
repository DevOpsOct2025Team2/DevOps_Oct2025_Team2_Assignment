Feature: Login
  As a user
  I want to log in with my credentials
  So that I am redirected to the correct dashboard for my role

  Scenario: Admin login redirects to admin dashboard
    Given a login username "admin" and password "Admin123"
    And the auth service recognizes this user as role "admin"
    When I submit a login request
    Then the response status should be 200
    And the response role should be "admin"
    And the response redirect_to should be "/admin"
    And the auth cookie should be set with security attributes

  Scenario: Regular login redirects to user dashboard
    Given a login username "user1" and password "User1234"
    And the auth service recognizes this user as role "regular"
    When I submit a login request
    Then the response status should be 200
    And the response role should be "regular"
    And the response redirect_to should be "/dashboard"
    And the auth cookie should be set with security attributes

  Scenario: Invalid credentials are rejected
    Given a login username "user1" and password "Wrong1234"
    And the auth service rejects the credentials
    When I submit a login request
    Then the response status should be 401
    And the response error should be "invalid_credentials"

  Scenario: Missing username or password is rejected
    Given a login username "" and password ""
    When I submit a login request
    Then the response status should be 400
    And the response error should be "invalid_request"

  Scenario: Missing JSON body is rejected
    Given no login payload
    When I submit a login request without json
    Then the response status should be 400
    And the response error should be "invalid_request"

  Scenario: Authentication service misconfiguration returns server error
    Given a login username "user1" and password "User1234"
    And the auth service is misconfigured
    When I submit a login request
    Then the response status should be 500
    And the response error should be "server_configuration"
