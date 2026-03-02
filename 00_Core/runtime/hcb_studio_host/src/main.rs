use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

use chrono::Local;
use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[derive(Parser, Debug)]
#[command(name = "hcb_studio_host")]
#[command(about = "Native HCB Studio kernel host (Windows .exe)")]
struct Cli {
    #[arg(
        long,
        default_value = "F:\\HCB_STUDIO",
        help = "HCB Studio root path"
    )]
    root: String,
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    Status,
    Event {
        #[command(subcommand)]
        command: EventCommand,
    },
    Concept {
        #[command(subcommand)]
        command: ConceptCommand,
    },
    Plan {
        #[arg(long)]
        goal: String,
    },
}

#[derive(Subcommand, Debug)]
enum EventCommand {
    Emit {
        #[arg(long = "event-type")]
        event_type: String,
        #[arg(long, default_value = "")]
        note: String,
    },
    Tail {
        #[arg(long, default_value_t = 20)]
        limit: usize,
    },
}

#[derive(Subcommand, Debug)]
enum ConceptCommand {
    Add {
        #[arg(long)]
        name: String,
        #[arg(long)]
        hypothesis: String,
        #[arg(long, default_value = "draft")]
        status: String,
        #[arg(long, default_value = "")]
        evidence: String,
    },
    List,
}

#[derive(Serialize, Deserialize, Debug)]
struct EventRecord {
    event_id: String,
    timestamp: String,
    event_type: String,
    payload: Value,
}

#[derive(Serialize, Deserialize, Debug)]
struct ConceptRegistry {
    version: String,
    concepts: Vec<Concept>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Concept {
    name: String,
    hypothesis: String,
    status: String,
    evidence: String,
    created_at: String,
    updated_at: String,
}

fn now_iso() -> String {
    Local::now().format("%Y-%m-%dT%H:%M:%S").to_string()
}

fn event_log_path(root: &Path) -> PathBuf {
    root.join("00_Core").join("logs").join("event_bus.jsonl")
}

fn concept_registry_path(root: &Path) -> PathBuf {
    root.join("00_Core")
        .join("contracts")
        .join("concept_registry.json")
}

fn append_event(root: &Path, event_type: &str, payload: Value) -> Result<EventRecord, String> {
    let path = event_log_path(root);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let record = EventRecord {
        event_id: format!(
            "evt_{}",
            Local::now().timestamp_nanos_opt().unwrap_or_default()
        ),
        timestamp: now_iso(),
        event_type: event_type.to_string(),
        payload,
    };
    let line = serde_json::to_string(&record).map_err(|e| e.to_string())?;
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| e.to_string())?;
    writeln!(file, "{line}").map_err(|e| e.to_string())?;
    Ok(record)
}

fn read_event_tail(root: &Path, limit: usize) -> Result<Vec<EventRecord>, String> {
    let path = event_log_path(root);
    if !path.exists() {
        return Ok(vec![]);
    }
    let file = fs::File::open(path).map_err(|e| e.to_string())?;
    let reader = BufReader::new(file);
    let lines: Vec<String> = reader.lines().map_while(Result::ok).collect();
    let mut out = Vec::new();
    for line in lines.iter().rev().take(limit) {
        if let Ok(event) = serde_json::from_str::<EventRecord>(line) {
            out.push(event);
        }
    }
    Ok(out)
}

fn load_registry(root: &Path) -> Result<ConceptRegistry, String> {
    let path = concept_registry_path(root);
    if !path.exists() {
        return Ok(ConceptRegistry {
            version: "1.0".to_string(),
            concepts: vec![],
        });
    }
    let raw = fs::read_to_string(path).map_err(|e| e.to_string())?;
    serde_json::from_str(&raw).map_err(|e| e.to_string())
}

fn save_registry(root: &Path, reg: &ConceptRegistry) -> Result<(), String> {
    let path = concept_registry_path(root);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let raw = serde_json::to_string_pretty(reg).map_err(|e| e.to_string())?;
    fs::write(path, raw).map_err(|e| e.to_string())
}

fn upsert_concept(
    root: &Path,
    name: &str,
    hypothesis: &str,
    status: &str,
    evidence: &str,
) -> Result<Concept, String> {
    let mut reg = load_registry(root)?;
    let now = now_iso();

    if let Some(existing) = reg.concepts.iter_mut().find(|c| c.name == name) {
        existing.hypothesis = hypothesis.to_string();
        existing.status = status.to_string();
        existing.evidence = evidence.to_string();
        existing.updated_at = now.clone();
        let concept = existing.clone();
        save_registry(root, &reg)?;
        return Ok(concept);
    }

    let concept = Concept {
        name: name.to_string(),
        hypothesis: hypothesis.to_string(),
        status: status.to_string(),
        evidence: evidence.to_string(),
        created_at: now.clone(),
        updated_at: now,
    };
    reg.concepts.push(concept.clone());
    save_registry(root, &reg)?;
    Ok(concept)
}

fn build_plan(goal: &str) -> Value {
    let text = goal.to_lowercase();
    let mut steps: Vec<Value> = vec![];

    if text.contains("status") || text.contains("saude") || text.contains("diagnostico") {
        steps.push(json!({"step":"Diagnosticar estado do sistema","command_args":["status"]}));
    }
    if text.contains("checkpoint") || text.contains("guardanapo") || text.contains("contexto") {
        steps.push(json!({"step":"Ler contexto de checkpoints","command_args":["napkin"]}));
    }
    if text.contains("ia") || text.contains("gemini") || text.contains("motor") {
        steps.push(json!({"step":"Verificar motor de IA","command_args":["ai","status"]}));
    }

    if steps.is_empty() {
        steps.push(json!({"step":"Diagnosticar estado base","command_args":["status"]}));
        steps.push(json!({"step":"Verificar motor de IA","command_args":["ai","status"]}));
    }

    json!({
        "goal": goal,
        "created_at": now_iso(),
        "steps": steps
    })
}

fn print_status(root: &Path) {
    let temp = root.join("04_TEMP");
    let storage = root.join("02_STORAGE");
    let ai_cfg = root.join("00_Core").join("config").join("ai_engine.json");

    println!("--- HCB STUDIO HOST STATUS ---");
    println!("Timestamp: {}", now_iso());
    println!("Root: {}", root.display());
    println!("Temp exists: {}", temp.exists());
    println!("Storage exists: {}", storage.exists());
    println!("AI config exists: {}", ai_cfg.exists());
    println!("Event log: {}", event_log_path(root).display());
}

fn run(cli: Cli) -> Result<(), String> {
    let root = PathBuf::from(cli.root);
    match cli.command {
        Commands::Status => {
            print_status(&root);
        }
        Commands::Event { command } => match command {
            EventCommand::Emit { event_type, note } => {
                let event = append_event(&root, &event_type, json!({"note": note}))?;
                println!("{}", serde_json::to_string_pretty(&event).map_err(|e| e.to_string())?);
            }
            EventCommand::Tail { limit } => {
                let rows = read_event_tail(&root, limit)?;
                if rows.is_empty() {
                    println!("(none)");
                } else {
                    for row in rows {
                        println!("{} | {} | {}", row.timestamp, row.event_type, row.event_id);
                    }
                }
            }
        },
        Commands::Concept { command } => match command {
            ConceptCommand::Add {
                name,
                hypothesis,
                status,
                evidence,
            } => {
                let concept = upsert_concept(&root, &name, &hypothesis, &status, &evidence)?;
                let _ = append_event(
                    &root,
                    "concept_upserted",
                    json!({"name": concept.name, "status": concept.status}),
                )?;
                println!("{}", serde_json::to_string_pretty(&concept).map_err(|e| e.to_string())?);
            }
            ConceptCommand::List => {
                let reg = load_registry(&root)?;
                if reg.concepts.is_empty() {
                    println!("(none)");
                } else {
                    for c in reg.concepts {
                        println!("{} | {} | {}", c.name, c.status, c.updated_at);
                    }
                }
            }
        },
        Commands::Plan { goal } => {
            let plan = build_plan(&goal);
            let _ = append_event(
                &root,
                "plan_created_native",
                json!({"goal": goal, "steps": plan["steps"].as_array().map_or(0, |x| x.len())}),
            )?;
            println!(
                "{}",
                serde_json::to_string_pretty(&plan).map_err(|e| e.to_string())?
            );
        }
    }
    Ok(())
}

fn main() {
    let cli = Cli::parse();
    if let Err(e) = run(cli) {
        eprintln!("ERROR: {e}");
        std::process::exit(1);
    }
}
