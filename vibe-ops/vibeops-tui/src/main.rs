use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout},
    widgets::{Block, Borders, Paragraph, Gauge},
    Terminal, Frame,
};
mod persistence;

use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use std::{error::Error, io, time::{Duration, Instant}};
use persistence::{get_latest_state, DbState};

struct App {
    state: Option<DbState>,
}

impl App {
    fn new() -> App {
        App {
            state: None,
        }
    }

    fn update(&mut self) {
        // Path adjusted to the project root relative to where TUI is usually run
        if let Ok(state) = get_latest_state("../vibe_ops.db") {
            self.state = Some(state);
        }
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    // Terminal setup
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let tick_rate = Duration::from_millis(1000);
    let mut app = App::new();
    app.update(); // Initial update
    let mut last_tick = Instant::now();

    loop {
        terminal.draw(|f| ui(f, &app))?;

        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));
            
        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if let KeyCode::Char('q') = key.code {
                    break;
                }
                if let KeyCode::Char('r') = key.code {
                    app.update();
                }
            }
        }
        if last_tick.elapsed() >= tick_rate {
            app.update();
            last_tick = Instant::now();
        }
    }

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    Ok(())
}

fn ui(f: &mut Frame, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints(
            [
                Constraint::Length(3),
                Constraint::Min(0),
                Constraint::Length(3),
            ]
            .as_ref(),
        )
        .split(f.size());

    // Title
    let title = Paragraph::new(" VibeOps Cybernetic Dashboard (Rust TUI) ")
        .block(Block::default().borders(Borders::ALL))
        .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(title, chunks[0]);

    if let Some(state) = &app.state {
        // Main Content
        let inner_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(50), Constraint::Percentage(50)].as_ref())
            .split(chunks[1]);

        // Policy Status
        let status_color = match state.policy.as_str() {
            "PUSH" => ratatui::style::Color::Red,
            "MAINTAIN" => ratatui::style::Color::Green,
            _ => ratatui::style::Color::Yellow,
        };
        
        let status_text = format!(
            "Current Policy: {}\nQHE (Quantum Human Efficiency): {:.2}\nHardwork Budget: {}h/day\nToday's Study: {:.2}h",
            state.policy, state.qhe, state.hardwork_budget, state.study_hours_today
        );
        let status = Paragraph::new(status_text)
            .style(ratatui::style::Style::default().fg(status_color))
            .block(Block::default().title(" System State ").borders(Borders::ALL));
        f.render_widget(status, inner_chunks[0]);

        // Ikigai Score
        let gauge = Gauge::default()
            .block(Block::default().title(" Ikigai Alignment (Metrics Avg) ").borders(Borders::ALL))
            .gauge_style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan))
            .percent((state.ikigai_global * 100.0) as u16)
            .label(format!("{:.1}%", state.ikigai_global * 100.0));
        f.render_widget(gauge, inner_chunks[1]);
    } else {
        let loading = Paragraph::new("Loading data from vibe_ops.db...")
            .block(Block::default().borders(Borders::ALL));
        f.render_widget(loading, chunks[1]);
    }

    // Footer
    let footer = Paragraph::new(" [Q] Exit | [R] Manual Refresh | Sync: 1s ")
        .block(Block::default().borders(Borders::ALL));
    f.render_widget(footer, chunks[2]);
}
