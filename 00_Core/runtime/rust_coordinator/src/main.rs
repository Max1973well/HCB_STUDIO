use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;
use thiserror::Error;
use tokio::time::{sleep, Duration};

#[derive(Debug, Error)]
enum CoordinatorError {
    #[error("usage: rust_coordinator process --command-file <path> [--result-file <path>] | demo")]
    Usage,
    #[error("missing value for argument: {0}")]
    MissingArg(&'static str),
    #[error("unsupported mode: {0}")]
    UnsupportedMode(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}

#[derive(Debug, Deserialize)]
struct CommandEnvelope {
    command_id: String,
    intent: String,
    action: String,
    #[serde(default)]
    payload: Value,
    metadata: CommandMetadata,
}

#[derive(Debug, Deserialize)]
struct CommandMetadata {
    timestamp: String,
    source: String,
}

#[derive(Debug, Serialize)]
struct ResultEnvelope {
    command_id: String,
    status: String,
    evidence: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    error_details: Option<String>,
    metadata: ResultMetadata,
}

#[derive(Debug, Serialize)]
struct ResultMetadata {
    timestamp: String,
    duration_ms: u128,
}

fn parse_args() -> Result<(String, Option<PathBuf>, Option<PathBuf>), CoordinatorError> {
    let mut args = env::args().skip(1);
    let mode = args.next().ok_or(CoordinatorError::Usage)?;
    let mut command_file = None;
    let mut result_file = None;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--command-file" => {
                let value = args.next().ok_or(CoordinatorError::MissingArg("--command-file"))?;
                command_file = Some(PathBuf::from(value));
            }
            "--result-file" => {
                let value = args.next().ok_or(CoordinatorError::MissingArg("--result-file"))?;
                result_file = Some(PathBuf::from(value));
            }
            other => return Err(CoordinatorError::UnsupportedMode(other.to_string())),
        }
    }

    Ok((mode, command_file, result_file))
}

fn load_command(path: &Path) -> Result<CommandEnvelope, CoordinatorError> {
    let raw = fs::read_to_string(path)?;
    Ok(serde_json::from_str(&raw)?)
}

fn write_result(path: &Path, result: &ResultEnvelope) -> Result<(), CoordinatorError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let raw = serde_json::to_string_pretty(result)?;
    fs::write(path, raw)?;
    Ok(())
}

async fn execute_command(command: &CommandEnvelope) -> ResultEnvelope {
    let started = Instant::now();
    let outcome = match command.action.as_str() {
        "execute_plan" => {
            let steps = command
                .payload
                .get("steps")
                .and_then(|value| value.as_array())
                .map(|items| items.len())
                .unwrap_or(0);
            sleep(Duration::from_millis(60)).await;
            (
                "success".to_string(),
                json!({
                    "action": command.action,
                    "intent": command.intent,
                    "received_from": command.metadata.source,
                    "command_timestamp": command.metadata.timestamp,
                    "steps_received": steps,
                    "execution_mode": "coordinator_simulated"
                }),
                None,
            )
        }
        "status_snapshot" => {
            sleep(Duration::from_millis(20)).await;
            (
                "success".to_string(),
                json!({
                    "action": command.action,
                    "intent": command.intent,
                    "received_from": command.metadata.source,
                    "coordinator_state": "healthy"
                }),
                None,
            )
        }
        other => {
            sleep(Duration::from_millis(10)).await;
            (
                "partial".to_string(),
                json!({
                    "action": other,
                    "intent": command.intent,
                    "received_from": command.metadata.source,
                    "execution_mode": "stub_unhandled"
                }),
                Some(format!("action not implemented yet: {other}")),
            )
        }
    };

    ResultEnvelope {
        command_id: command.command_id.clone(),
        status: outcome.0,
        evidence: outcome.1,
        error_details: outcome.2,
        metadata: ResultMetadata {
            timestamp: Utc::now().to_rfc3339(),
            duration_ms: started.elapsed().as_millis(),
        },
    }
}

async fn run_demo() {
    let demo = CommandEnvelope {
        command_id: "demo-command".to_string(),
        intent: "boot nervous system".to_string(),
        action: "status_snapshot".to_string(),
        payload: json!({}),
        metadata: CommandMetadata {
            timestamp: Utc::now().to_rfc3339(),
            source: "rust_demo".to_string(),
        },
    };

    let result = execute_command(&demo).await;
    println!("{}", serde_json::to_string_pretty(&result).unwrap_or_else(|_| "{}".to_string()));
}

#[tokio::main]
async fn main() -> Result<(), CoordinatorError> {
    let (mode, command_file, result_file) = parse_args()?;

    match mode.as_str() {
        "demo" => {
            run_demo().await;
            Ok(())
        }
        "process" => {
            let command_path = command_file.ok_or(CoordinatorError::MissingArg("--command-file"))?;
            let command = load_command(&command_path)?;
            let result = execute_command(&command).await;

            if let Some(path) = result_file {
                write_result(&path, &result)?;
                println!("result_written={}", path.display());
            } else {
                println!("{}", serde_json::to_string_pretty(&result)?);
            }
            Ok(())
        }
        other => Err(CoordinatorError::UnsupportedMode(other.to_string())),
    }
}
