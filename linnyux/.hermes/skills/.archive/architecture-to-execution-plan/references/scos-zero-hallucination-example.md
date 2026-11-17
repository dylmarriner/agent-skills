# SCOS Plan — Zero-Hallucination Reference Example

This reference documents the SCOS v2 implementation plan (`/home/lin/Documents/SCOS/EXECUTION-PLAN.md`) as an example of what a zero-hallucination plan looks like for a multi-crate distributed systems project.

## Key Metrics

- **18 design docs** analyzed (1 index + 17 volumes)
- **12 phases**, first runnable MVP at Phase 5
- **106 KB**, 1,600+ lines of specification
- **67 files** in strict creation order
- **11 Rust crates** + CLI binary + protobuf + CI

## What Makes It Zero-Hallucination

### 1. Every Struct Field Specified

Instead of saying "define the cognitive transaction struct," every field with its type is written verbatim:

```
pub struct CognitiveTransaction {
    pub transaction_id: Uuid,
    pub origin_node_id: NodeId,
    pub objective: String,
    pub constraints: Vec<Constraint>,
    pub required_capabilities: Vec<Capability>,
    pub memory_snapshot_id: Option<String>,
    pub execution_graph_id: String,
    pub token_budget: u64,
    pub deadline_ms: u64,
    pub created_at_ms: u64,
}
```

### 2. Every Function Signature Exact

```
pub fn validate_dag(dag: &ExecutionDag) -> scos_common::Result<()>
pub fn topological_sort(dag: &ExecutionDag) -> Vec<&DagNode>
pub fn encode_message(msg: &NetworkMessage) -> scos_common::Result<Vec<u8>>
```

### 3. Every Dependency Version-Pinned

All in workspace.dependencies — no version guessing:

```toml
[workspace.dependencies]
serde = { version = "1", features = ["derive"] }
uuid = { version = "1", features = ["v4", "serde"] }
libp2p = { version = "0.54", features = ["full", "quic"] }
ed25519-dalek = { version = "2", features = ["serde"] }
prost = "0.13"
wasmtime = "25"
```

### 4. Algorithm Code Inline Instead of "Implement X"

**Bad:** "Implement DAG validation using cycle detection"

**Good:** Written verbatim:

```rust
// Cycle detection: Kahn's algorithm
let mut in_degree: HashMap<&str, usize> = HashMap::new();
let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();
for node in &dag.nodes {
    in_degree.entry(node.id.as_str()).or_insert(0);
    adj.entry(node.id.as_str()).or_default();
}
for edge in &dag.edges {
    *in_degree.entry(edge.to_node_id.as_str()).or_insert(0) += 1;
    adj.entry(edge.from_node_id.as_str())
        .or_default()
        .push(edge.to_node_id.as_str());
}
// ... full algorithm continues
```

Similarly for LinUCB contextual bandit (Gaussian elimination for matrix inversion) and CRDT merge (LWW by updated_at_ms).

### 5. Error Enum with Every Variant

```rust
#[derive(Error, Debug)]
pub enum Error {
    #[error("Node not found: {0}")]
    NodeNotFound(String),
    #[error("Task {0} failed after {1} retries")]
    TaskFailed(String, u8),
    #[error("Network error: {0}")]
    Network(String),
    // ... 12 more variants
}
```

### 6. Module Exports Explicit

```
pub mod error;
pub mod types;
pub mod tracing_module;
pub mod proto {
    include!(concat!(env!("OUT_DIR"), "/scos.rs"));
}
pub use types::*;
pub use error::*;
```

### 7. Proto Contract Complete

Full protobuf file with all 17 messages, exact field numbers:

```protobuf
message CognitiveTransaction {
  string transaction_id = 1;
  string origin_node_id = 2;
  ...
}
```

### 8. Error Handling Contract

```
Every `pub fn` that can fail MUST return `scos_common::Result<T>`, 
not `anyhow::Result<T>`, not unwrap/expect, not panic.
The only exceptions: main() returns anyhow, pure data transforms, tests.
```

### 9. Serialization Contract

```
All wire-format messages (NetworkMessage + variants) use `serde_json`.
Protobuf is generated from `proto/scos.proto` for forward compatibility.
Primary message exchange format for MVP is JSON over GossipSub.
```

### 10. Integration Test Script

Actual runnable shell script with exact ports, commands, and expected output:

```bash
cargo run -- start --config /tmp/scos-test-alice/config.toml &
sleep 2
cargo run -- task submit "hello swarm" --budget 1000
# Expected: [OK] root — completed, [OK] worker-1 — completed
```

### 11. Hard Constraint Checklist

15-item checklist placed at the end of the plan:

```
- [ ] No central broker dependency
- [ ] No mocked swarm behavior in production
- [ ] No LLM where deterministic code suffices
- [ ] No plugin without sandbox
- [ ] No memory write without provenance
- [ ] No task execution without trace ID
...
```

### 12. File Creation Order

67-file strict numbered sequence:

```
Phase 0:
  1. Cargo.toml (workspace)
  2. rust-toolchain.toml
  3. .gitignore
  ...
Phase 1:
  7.  crates/scos-common/Cargo.toml
  8.  crates/scos-common/build.rs
  9.  crates/scos-common/src/error.rs
  ...
```

## Lesson for Future Sessions

A zero-hallucination plan is one where the implementing agent never needs to:

1. Guess a field name or type — every struct specifies them
2. Guess a return type — every function specifies it
3. Guess a dependency version — pinned in workspace
4. Design an algorithm — written inline
5. Design an error path — every variant enumerated
6. Decide module structure — lib.rs re-exports shown
7. Decide serialization format — explicitly stated
8. Decide where to put files — numbered creation order
9. Decide test expectations — assertions written
10. Decide config schema — default content shown verbatim
