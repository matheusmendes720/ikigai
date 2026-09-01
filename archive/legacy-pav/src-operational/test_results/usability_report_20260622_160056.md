# PAV Operational — Manual Test Report

**Generated:** 2026-06-22T16:00:58.033731+00:00  
**Root:** `C:\Users\mathe\code_space\life-oss\life\life-ops\operational`  
**State:** `C:\Users\mathe\.time-tasker`

## Summary

- **Total tests:** 29
- **Passed:** 0  
- **Failed:** 29  
- **Pass rate:** 0%

## Results by Category

| Category | Total | Passed | Failed | Rate |
|----------|-------|--------|--------|------|
| block | 3 | 0 | 3 | 0% |
| demo | 2 | 0 | 2 | 0% |
| doctor | 2 | 0 | 2 | 0% |
| habit | 3 | 0 | 3 | 0% |
| home | 1 | 0 | 1 | 0% |
| journal | 2 | 0 | 2 | 0% |
| lunch | 2 | 0 | 2 | 0% |
| metric | 3 | 0 | 3 | 0% |
| policy | 2 | 0 | 2 | 0% |
| reflect | 3 | 0 | 3 | 0% |
| report | 2 | 0 | 2 | 0% |
| routine | 3 | 0 | 3 | 0% |
| state | 1 | 0 | 1 | 0% |

## Failed Tests

| # | Command | Exit | Notes |
|---|---------|------|-------|
| routine_01 | `pav routine create Test Routine CLI MANHA CORE` | 1 | exit=1 |
| routine_02 | `pav routine list --json` | 1 | exit=1 |
| routine_03 | `pav routine list --period MANHA --json` | 1 | exit=1 |
| block_01 | `pav block create TARDE --label Deep work block CLI` | 1 | exit=1 |
| block_02 | `pav block list --json` | 1 | exit=1 |
| block_03 | `pav block list --period TARDE --json` | 1 | exit=1 |
| journal_01 | `pav journal create --text Test journal entry via CLI script` | 1 | exit=1 |
| journal_02 | `pav journal list --json` | 1 | exit=1 |
| habit_01 | `pav habit create Test Habit CLI physiological --resistance 3 --w` | 1 | exit=1 |
| habit_02 | `pav habit list --json` | 1 | exit=1 |
| habit_03 | `pav habit list --category physiological --json` | 1 | exit=1 |
| metric_sleep_01 | `pav metric sleep --quality 8 --bed-hour 22 --bed-minute 30 --wak` | 1 | exit=1 |
| metric_sleep_02 | `pav metric list --json` | 1 | exit=1 |
| metric_energy_01 | `pav metric energy --energia 7 --foco 8` | 1 | exit=1 |
| policy_01 | `pav policy setpoints --json` | 1 | exit=1 |
| policy_02 | `pav policy decisions --json` | 1 | exit=1 |
| demo_01 | `pav demo show --json` | 1 | exit=1 |
| demo_02 | `pav demo show` | 1 | exit=1 |
| state_01 | `pav state show --json` | 1 | exit=1 |
| reflect_entrada_01 | `pav reflect entrada --date 2026-06-22 --json` | 1 | exit=1 |
| reflect_saida_01 | `pav reflect saida --date 2026-06-22 --json` | 1 | exit=1 |
| reflect_list_01 | `pav reflect list --json` | 1 | exit=1 |
| report_01 | `pav report daily --json` | 1 | exit=1 |
| report_02 | `pav report weekly --json` | 1 | exit=1 |
| lunch_01 | `pav lunch create --eat 45 --rest 20 --notas Test lunch via CLI s` | 1 | exit=1 |
| lunch_02 | `pav lunch list --json` | 1 | exit=1 |
| doctor_01 | `pav doctor doctor --json` | 1 | exit=1 |
| doctor_02 | `pav doctor doctor` | 1 | exit=1 |
| home_01 | `pav home` | 1 | exit=1 |

## State Files After Tests

- **habits**: 0 record(s)
- **journals**: 0 record(s)
- **routines**: 0 record(s)
- **sleep_records**: 0 record(s)
- **time_blocks**: 0 record(s)

## All Test Results

| # | Cat | Command | Exit | Pass? | Expected | Actual |
|---|-----|---------|------|--------|---------|--------|
| routine_01 | routine | `pav routine create Test Routine CLI MAN` | 1 | FAIL | id |  |
| routine_02 | routine | `pav routine list --json` | 1 | FAIL | id |  |
| routine_03 | routine | `pav routine list --period MANHA --json` | 1 | FAIL | MANHA |  |
| block_01 | block | `pav block create TARDE --label Deep wor` | 1 | FAIL | id |  |
| block_02 | block | `pav block list --json` | 1 | FAIL | id |  |
| block_03 | block | `pav block list --period TARDE --json` | 1 | FAIL | TARDE |  |
| journal_01 | journal | `pav journal create --text Test journal ` | 1 | FAIL | id |  |
| journal_02 | journal | `pav journal list --json` | 1 | FAIL | id |  |
| habit_01 | habit | `pav habit create Test Habit CLI physiol` | 1 | FAIL | id |  |
| habit_02 | habit | `pav habit list --json` | 1 | FAIL | id |  |
| habit_03 | habit | `pav habit list --category physiological` | 1 | FAIL | physiological |  |
| metric_sleep_01 | metric | `pav metric sleep --quality 8 --bed-hour` | 1 | FAIL | id |  |
| metric_sleep_02 | metric | `pav metric list --json` | 1 | FAIL | id |  |
| metric_energy_01 | metric | `pav metric energy --energia 7 --foco 8` | 1 | FAIL | id |  |
| policy_01 | policy | `pav policy setpoints --json` | 1 | FAIL | id |  |
| policy_02 | policy | `pav policy decisions --json` | 1 | FAIL | id |  |
| demo_01 | demo | `pav demo show --json` | 1 | FAIL | routines |  |
| demo_02 | demo | `pav demo show` | 1 | FAIL | Rotinas |  |
| state_01 | state | `pav state show --json` | 1 | FAIL | id |  |
| reflect_entrada_01 | reflect | `pav reflect entrada --date 2026-06-22 -` | 1 | FAIL | id |  |
| reflect_saida_01 | reflect | `pav reflect saida --date 2026-06-22 --j` | 1 | FAIL | id |  |
| reflect_list_01 | reflect | `pav reflect list --json` | 1 | FAIL | id |  |
| report_01 | report | `pav report daily --json` | 1 | FAIL | sono_resumo |  |
| report_02 | report | `pav report weekly --json` | 1 | FAIL | dias |  |
| lunch_01 | lunch | `pav lunch create --eat 45 --rest 20 --n` | 1 | FAIL | id |  |
| lunch_02 | lunch | `pav lunch list --json` | 1 | FAIL | id |  |
| doctor_01 | doctor | `pav doctor doctor --json` | 1 | FAIL | schema_ok |  |
| doctor_02 | doctor | `pav doctor doctor` | 1 | FAIL | schema_ok |  |
| home_01 | home | `pav home` | 1 | FAIL | PAV-OS |  |
