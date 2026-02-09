Feature: User Dashboard API
  As a regular user
  I want to manage my files
  So that I can upload, view, and delete my own files

  Scenario: Regular user can list their files
    Given an authenticated user with role "regular" and id "user-1"
    And the file service returns a file list
    When I request my file list
    Then the response status should be 200
    And the response should include files

  Scenario: Regular user can upload a file
    Given an authenticated user with role "regular" and id "user-1"
    And the file service accepts uploads
    When I upload a file named "test.txt"
    Then the response status should be 201

  Scenario: Regular user can delete their file
    Given an authenticated user with role "regular" and id "user-1"
    And the file service allows deleting file "file-1"
    When I delete my file "file-1"
    Then the response status should be 200

  Scenario: Admin is forbidden from user file list
    Given an authenticated user with role "admin" and id "admin-1"
    When I request my file list
    Then the response status should be 403

  Scenario: Unauthenticated user cannot list files
    Given an unauthenticated user
    When I request my file list
    Then the response status should be 401

  Scenario: Unauthenticated user cannot upload a file
    Given an unauthenticated user
    When I upload a file named "test.txt"
    Then the response status should be 401
