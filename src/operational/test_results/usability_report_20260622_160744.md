# PAV Operational — Manual Test Report

**Generated:** 2026-06-22T16:08:03.347532+00:00  
**Root:** `C:\Users\mathe\code_space\life-oss\life\life-ops\operational`  
**State:** `C:\Users\mathe\.time-tasker`

## Summary

- **Total tests:** 29
- **Passed:** 18  
- **Failed:** 11  
- **Pass rate:** 62%

## Results by Category

| Category | Total | Passed | Failed | Rate |
|----------|-------|--------|--------|------|
| block | 3 | 3 | 0 | 100% |
| demo | 2 | 0 | 2 | 0% |
| doctor | 2 | 0 | 2 | 0% |
| habit | 3 | 3 | 0 | 100% |
| home | 1 | 0 | 1 | 0% |
| journal | 2 | 1 | 1 | 50% |
| lunch | 2 | 1 | 1 | 50% |
| metric | 3 | 3 | 0 | 100% |
| policy | 2 | 2 | 0 | 100% |
| reflect | 3 | 3 | 0 | 100% |
| report | 2 | 0 | 2 | 0% |
| routine | 3 | 2 | 1 | 67% |
| state | 1 | 0 | 1 | 0% |

## Failed Tests

| # | Command | Exit | Notes |
|---|---------|------|-------|
| routine_01 | `pav routine create Test Routine CLI MANHA CORE` | 0 | 'id' not found in output |
| journal_01 | `pav journal create --text Test journal entry via CLI script` | 0 | 'id' not found in output |
| demo_01 | `pav demo show --json` | 0 | 'routines' not found in output |
| demo_02 | `pav demo show` | 0 | 'Rotinas' not found in output |
| state_01 | `pav state show --json` | 0 | 'id' not found in output |
| report_01 | `pav report daily --json` | 0 | 'sono_resumo' not found in output |
| report_02 | `pav report weekly --json` | 0 | 'dias' not found in output |
| lunch_01 | `pav lunch create --eat 45 --rest 20 --notas Test lunch via CLI s` | 0 | 'id' not found in output |
| doctor_01 | `pav doctor doctor --json` | 1 | exit=1 |
| doctor_02 | `pav doctor doctor` | 1 | exit=1 |
| home_01 | `pav home` | 1 | exit=1 |

## State Files After Tests

- **ajustes_finos**: 1 record(s)
- **daily_reflections**: 1 record(s)
- **day_contexts**: 1 record(s)
- **habits**: 1 record(s)
- **journals**: 1 record(s)
- **lunch_records**: 1 record(s)
- **policy_decisions**: 1 record(s)
- **policy_setpoints**: 1 record(s)
- **pomodoros**: 1 record(s)
- **routine_logs**: 1 record(s)
- **routines**: 1 record(s)
- **sleep_records**: 1 record(s)
- **time_blocks**: 1 record(s)
- **transicoes**: 1 record(s)

## All Test Results

| # | Cat | Command | Exit | Pass? | Expected | Actual |
|---|-----|---------|------|--------|---------|--------|
| routine_01 | routine | `pav routine create Test Routine CLI MAN` | 0 | FAIL | id | Criando rotina |
| routine_02 | routine | `pav routine list --json` | 0 | PASS | id | id,name,period,routine_ty |
| routine_03 | routine | `pav routine list --period MANHA --json` | 0 | PASS | MANHA | id,name,period,routine_ty |
| block_01 | block | `pav block create TARDE --label Deep wor` | 0 | PASS | id | Criando time block |
| block_02 | block | `pav block list --json` | 0 | PASS | id | id,label,start,end,period |
| block_03 | block | `pav block list --period TARDE --json` | 0 | PASS | TARDE | id,label,start,end,period |
| journal_01 | journal | `pav journal create --text Test journal ` | 0 | FAIL | id | Criando entrada de diário |
| journal_02 | journal | `pav journal list --json` | 0 | PASS | id | id,date,entry_text,period |
| habit_01 | habit | `pav habit create Test Habit CLI physiol` | 0 | PASS | id | Criando hábito |
| habit_02 | habit | `pav habit list --json` | 0 | PASS | id | id,name,category,resistan |
| habit_03 | habit | `pav habit list --category physiological` | 0 | PASS | physiological | id,name,category,resistan |
| metric_sleep_01 | metric | `pav metric sleep --quality 8 --bed-hour` | 0 | PASS | id | Registrando sono |
| metric_sleep_02 | metric | `pav metric list --json` | 0 | PASS | id | id,date,bedtime,wake_time |
| metric_energy_01 | metric | `pav metric energy --energia 7 --foco 8` | 0 | PASS | id | Check-in de energia/foco |
| policy_01 | policy | `pav policy setpoints --json` | 0 | PASS | id | id,state,hardwork_budget_ |
| policy_02 | policy | `pav policy decisions --json` | 0 | PASS | id | id,date,state,severity,ra |
| demo_01 | demo | `pav demo show --json` | 0 | FAIL | routines | entities |
| demo_02 | demo | `pav demo show` | 0 | FAIL | Rotinas | | Entity | Count | |:---- |
| state_01 | state | `pav state show --json` | 0 | FAIL | id | date,period_now,sleep,blo |
| reflect_entrada_01 | reflect | `pav reflect entrada --date 2026-06-22 -` | 0 | PASS | id | 🌅 OKRs de Entrada — 2026- |
| reflect_saida_01 | reflect | `pav reflect saida --date 2026-06-22 --j` | 0 | PASS | id | 🌙 OKRs de Saída — 2026-06 |
| reflect_list_01 | reflect | `pav reflect list --json` | 0 | PASS | id | id,date,parar_de_fazer,re |
| report_01 | report | `pav report daily --json` | 0 | FAIL | sono_resumo | date,tipo_dia,wake_hour,s |
| report_02 | report | `pav report weekly --json` | 0 | FAIL | dias | start,end,n_days,n_pomodo |
| lunch_01 | lunch | `pav lunch create --eat 45 --rest 20 --n` | 0 | FAIL | id | ╭──────────────────────── |
| lunch_02 | lunch | `pav lunch list --json` | 0 | PASS | id | id,date,eat_min,rest_min, |
| doctor_01 | doctor | `pav doctor doctor --json` | 1 | FAIL | schema_ok |  |
| doctor_02 | doctor | `pav doctor doctor` | 1 | FAIL | schema_ok |  |
| home_01 | home | `pav home` | 1 | FAIL | PAV-OS | ╔════════════════════════ |
