Feature: PAV CLI Command Execution

  Scenario: habit list returns valid JSON
    Given the PAV CLI is available
    When I run `pav habit list --json`
    Then I receive valid JSON with entity fields
    And the exit code is 0

  Scenario: routine list returns entities for each period
    Given the PAV CLI is available
    When I run `pav routine list --json`
    Then I receive a list of routine entities
    And each entity has id, name, period, routine_type

  Scenario: report daily uses synthetic dataset context
    Given the system has 180 days of synthetic data loaded
    When I run `pav report daily --json`
    Then I receive a daily report with sleep, habit, energy fields
    And the report date matches today's date

