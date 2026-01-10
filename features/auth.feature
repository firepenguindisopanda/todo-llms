Feature: User registration and login
  Verify basic authentication flows work via the API and web UI.

  Background:
    Given the API server is reachable

  # === API Authentication ===

  Scenario: Register new user and login via API
    Given I use a unique email
    When I POST /api/v1/auth/register with valid payload
    Then I receive 201 Created and the user's email is returned
    And I can login with the same credentials

  # === Web UI Authentication ===

  Scenario: Successful user registration via web UI
    Given I use a unique email
    When I visit the registration page
    And I fill in the registration form with the unique email and password "secret123"
    And I submit the registration form
    Then I should be redirected to "/auth/login"
    And the response should contain "Registration successful"

  Scenario: Registration with mismatched passwords via web UI
    Given I use a unique email
    When I visit the registration page
    And I fill in the registration form with the unique email and mismatched passwords
    And I submit the registration form
    Then the response should contain "Passwords do not match"

  Scenario: Successful login via web UI
    Given I use a unique email
    And I register the user via API
    When I visit the login page
    And I fill in the login form with the registered credentials
    And I submit the login form
    Then I should be redirected to "/dashboard"

  Scenario: Login with invalid credentials via web UI
    When I visit the login page
    And I fill in the login form with email "nonexistent@example.com" and password "wrong"
    And I submit the login form
    Then the response should contain "Invalid credentials"

  Scenario: Registration with duplicate email via web UI
    Given I use a unique email
    And I register the user via API
    When I visit the registration page
    And I fill in the registration form with the unique email and password "secret123"
    And I submit the registration form
    Then the response should contain "Email already registered"
