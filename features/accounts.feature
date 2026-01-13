Feature: Account management
  As a logged-in user
  I want to update my account settings
  So that the app reflects my preferences

  Scenario: Update display mode via web UI
    Given the API server is reachable
    And I use a unique email
    When I register and login using the web UI
    And I visit the account page
    And I set display mode to "dark" and items per page to "20"
    Then I should be redirected to "/account"
    And the account page should contain "Account updated"