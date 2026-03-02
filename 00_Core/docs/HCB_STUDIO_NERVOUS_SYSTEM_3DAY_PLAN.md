# HCB Studio Nervous System - 3 Day Build Plan

## Objective
Build a robust, modular nervous system for HCB Studio with clear separation of responsibilities:
- Rust for orchestration/runtime reliability
- C++ for high-performance kernels
- Java for enterprise-style integration/services
- Python for AI tooling and rapid adapters

This is not a quick script project. It is a staged systems build.

## Core Principles
- Zero-loss posture: every critical action is logged, replayable, and recoverable.
- Deterministic flow: command in, plan generated, action executed, evidence stored.
- Progressive hardening: prototype in Python, stabilize in Rust/Java, optimize hotspots in C++.
- Rest-safe continuity: each work block ends with a machine-readable checkpoint.

## Target Architecture
1. Sensory Layer
- File/events ingestion from `04_TEMP`, external folders, and command channels.
- Normalization into events with strict schema.

2. Memory Layer
- Capsule persistence (JSON) + indexed archive.
- Context retrieval by module, intent, and time window.

3. Cognition Layer
- Planner/Executor that maps intents to workflows.
- Policy engine for "allowed actions", guardrails, and rollback strategy.

4. Motor Layer
- Tool Runner to execute controlled actions (`triage`, `train`, `napkin`, `evolve`, future connectors).
- Native execution path for heavy tasks via C++.

5. Governance Layer
- Audit log per operation.
- Risk gates before destructive actions.
- Snapshot/restore points via Git and runtime reports.

## Language Responsibilities
1. Rust
- Runtime coordinator (state machine + job queue + retries + timeouts).
- Event bus process with durable local store.
- Health monitor and watchdog process.

2. C++
- Native computational kernels (already started in `00_Core/engines/cpp_native`).
- Memory bridge performance-critical operations.
- Bounded FFI API consumed by Rust/Python.

3. Java
- Integration service boundary for enterprise modules:
- authentication, workflow routing, connectors, reporting endpoints.
- Strong typed API contracts for long-term maintainability.

4. Python
- AI-facing adapters, model routines, and operational scripts.
- Rapid experimentation before migration to hard-runtime modules.

## 3-Day Execution Plan
## Day 1 - Backbone and Contracts
1. Define event schema and command schema (`intent`, `action`, `result`, `evidence`).
2. Add Rust service skeleton: `runtime_coordinator` with local queue.
3. Wire Python `hcb_control.py` as a managed worker (not standalone logic center).
4. Create operation audit envelope for every command.
5. Deliverable: one end-to-end flow from intent to audited result.

## Day 2 - Memory + Planner Hardening
1. Promote `arm-memory` into indexed memory service contract.
2. Build planner pipeline:
- intent -> plan steps -> execute -> validate -> checkpoint.
3. Add rollback policy:
- if any critical step fails, system records failure and reverts safe state.
4. Deliverable: repeatable plan execution with deterministic logs.

## Day 3 - Native and Integration Expansion
1. Connect Rust coordinator to C++ kernels through stable FFI boundary.
2. Add Java integration service skeleton (API and connector stubs).
3. Add health dashboard metrics (jobs, failures, retries, latency).
4. Deliverable: multi-language nervous system baseline running with telemetry.

## Immediate Next Build Tasks
1. Create `00_Core/runtime/rust_coordinator/` workspace.
2. Create `00_Core/contracts/` with JSON schemas for command/result/checkpoint.
3. Add `planner` command in `hcb_control.py` that emits schema-compliant plan record.
4. Add `checkpoint end-of-block` command to persist continuity capsule at each stop.

## Definition of Done (for this phase)
- One intent can be executed via coordinator, not ad-hoc scripts.
- Every step produces machine-readable evidence.
- A failed run can be diagnosed from logs without re-running.
- Work can pause/resume with no context loss.
