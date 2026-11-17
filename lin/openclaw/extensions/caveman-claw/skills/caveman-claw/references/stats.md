# Savings Stats

## Usage

```
/cc stats
```

## What to do

Call the `caveman_claw_stats` tool. Output the result verbatim.

The tool reads OpenClaw's session and model data to resolve the current model's per-token price. No user configuration required.

## Example output

```
Caveman Claw savings:

Session:  -12,400 tokens  (~$0.04 saved)
Today:    -89,200 tokens  (~$0.27 saved)
All time: -1.2M tokens    (~$3.60 saved)

Model: google/gemini-2.5-flash · $0.08/1M tokens
Note: tracks input compression only. Output savings not measured.
```
