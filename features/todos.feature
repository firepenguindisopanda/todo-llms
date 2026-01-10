Feature: Todo Management
  As a logged-in user
  I want to create, read, update, and delete todos
  So that I can manage my tasks effectively

  Background:
    Given the API server is reachable
    And I have a registered user and access token

  Scenario: Create a new todo
    When I create a todo with title "Buy groceries" and description "Milk, eggs, bread"
    Then the todo should be created successfully
    And the response should include the todo title "Buy groceries"

  Scenario: List all todos
    Given I have created a todo with title "First task"
    And I have created a todo with title "Second task"
    When I list all my todos
    Then I should see 2 todos in the list

  Scenario: Get a specific todo
    Given I have created a todo with title "Specific task"
    When I get the todo by ID
    Then the response should include the todo title "Specific task"

  Scenario: Update a todo
    Given I have created a todo with title "Original title"
    When I update the todo title to "Updated title"
    Then the todo should be updated successfully
    And the response should include the todo title "Updated title"

  Scenario: Mark todo as completed
    Given I have created a todo with title "Task to complete"
    When I mark the todo as completed
    Then the todo should show completed status

  Scenario: Delete a todo
    Given I have created a todo with title "Task to delete"
    When I delete the todo
    Then the todo should be deleted successfully
    And the todo should no longer exist

  Scenario: Create a todo via dashboard (web UI)
    Given I use a unique email
    When I visit the registration page
    And I fill in the registration form with the unique email and password "todopw123"
    And I submit the registration form
    Then I should be redirected to "/auth/login"
    And the response should contain "Registration successful"
    When I visit the login page
    And I fill in the login form with the registered credentials
    And I submit the login form
    Then I should be redirected to "/dashboard"
    When I visit the dashboard page
    And I create a todo via the dashboard with title "Buy milk" and description "2L"
    Then I should be redirected to "/dashboard"
    And the response should contain "Todo created successfully"
    And the response should contain "Buy milk"
