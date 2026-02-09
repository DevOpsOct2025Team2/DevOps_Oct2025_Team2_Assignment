Feature: Admin Dashboard API
  As an admin user
  I want to manage user accounts
  So that I can create and delete users

  Scenario: Admin can list all users
    Given an authenticated user with role "admin"
    And the user service returns a user list
    When I request the admin user list
    Then the response status should be 200
    And the response should include users

  Scenario: Admin can create a user
    Given an authenticated user with role "admin"
    And a new user payload with username "newuser" and password "Pass1234"
    And the database accepts the new user
    When I submit an admin create user request
    Then the response status should be 201

  Scenario: Admin can delete a user
    Given an authenticated user with role "admin"
    And a target user id "user-2"
    And the user exists in the system
    When I submit an admin delete user request
    Then the response status should be 200

  Scenario: Regular user is forbidden from admin actions
    Given an authenticated user with role "regular"
    When I request the admin user list
    Then the response status should be 403
