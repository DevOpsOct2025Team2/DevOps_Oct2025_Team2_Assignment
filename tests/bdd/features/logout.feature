Feature: Logout
  As an authenticated user
  I want to log out securely
  So that I am returned to the login page

  Scenario: Authenticated user can log out
    Given an authenticated user with role "regular"
    When I submit a logout request
    Then the response status should be 200
    And the response redirect_to should be "/login"
    And the auth cookie should be cleared

  Scenario: Admin user can log out
    Given an authenticated user with role "admin"
    When I submit a logout request
    Then the response status should be 200
    And the response redirect_to should be "/login"
    And the auth cookie should be cleared

  Scenario: Unauthenticated user cannot log out
    Given no authentication
    When I submit a logout request
    Then the response status should be 401
    And the response error should be "unauthorized"

  Scenario: Invalid token is rejected
    Given an invalid auth token
    When I submit a logout request
    Then the response status should be 401
    And the response error should be "unauthorized"

  Scenario: Expired token is rejected
    Given an expired auth token
    When I submit a logout request
    Then the response status should be 401
    And the response error should be "unauthorized"
