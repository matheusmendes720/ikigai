use rusqlite::{Connection, Result};
use chrono::Utc;

pub struct DbState {
    pub policy: String,
    pub qhe: f64,
    pub ikigai_global: f64,
    pub hardwork_budget: f64,
    pub study_hours_today: f64,
}

pub fn get_latest_state(db_path: &str) -> Result<DbState> {
    let conn = Connection::open(db_path)?;

    // 1. Get latest policy decision
    let mut stmt = conn.prepare(
        "SELECT policy, qhe, hardwork_budget_hours FROM policy_decisions ORDER BY date DESC LIMIT 1"
    )?;
    
    let (policy, qhe, hardwork_budget) = stmt.query_row([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, f64>(1)?,
            row.get::<_, f64>(2)?,
        ))
    }).unwrap_or_else(|_| ("MAINTAIN".to_string(), 0.5, 2.5));

    // 2. Get study hours for today
    let today = Utc::now().date_naive().to_string();
    let mut stmt_study = conn.prepare(
        "SELECT SUM(duration_minutes) / 60.0 FROM study_sessions WHERE date = ?"
    )?;
    let study_hours: f64 = stmt_study.query_row([today], |row| {
        let val: Option<f64> = row.get(0)?;
        Ok(val.unwrap_or(0.0))
    })?;

    // 3. Compute a simple Ikigai Global for display
    // In a real scenario, we'd query the metrics table
    let mut stmt_metrics = conn.prepare(
        "SELECT AVG(qhe) FROM policy_decisions WHERE date >= date('now', '-7 days')"
    )?;
    let ikigai_global: f64 = stmt_metrics.query_row([], |row| {
        let val: Option<f64> = row.get(0)?;
        Ok(val.unwrap_or(0.5))
    })?;

    Ok(DbState {
        policy,
        qhe,
        ikigai_global,
        hardwork_budget,
        study_hours_today: study_hours,
    })
}
