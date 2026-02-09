Feature: Data Isolation
  As a regular user
  I should only access my own files
  So that other users' data is protected

  Scenario: User cannot delete another user's file
    Given an authenticated user with role "regular" and id "user-1"
    And the file service denies access to file "file-2"
    When I delete my file "file-2"
    Then the response status should be 403

  Scenario: User sees only their own files
    Given an authenticated user with role "regular" and id "user-1"
    And the file service returns only files for user "user-1"
    When I request my file list
    Then the response status should be 200
    And the response should include files

  Scenario: User can delete their own file
    Given an authenticated user with role "regular" and id "user-1"
    And the file service allows deleting file "file-1"
    When I delete my file "file-1"
    Then the response status should be 200

  Scenario: Unauthenticated user cannot list files
    Given an unauthenticated user
    When I request my file list
    Then the response status should be 401

  Scenario: Unauthenticated user cannot delete a file
    Given an unauthenticated user
    When I delete my file "file-1"
    Then the response status should be 401
