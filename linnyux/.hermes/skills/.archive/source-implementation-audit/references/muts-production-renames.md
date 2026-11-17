# MUTS: Common Prototype-to-Production Renames

When auditing MUTS original sources against the `app/` workspace,
these production-safe renames are the most common mismatches:

## Core Security

| Prototype Name | Production Name | Location |
|---|---|---|
| `MazdaSecurity` (muts1) | `MazdaSecurity` | `app/muts/security/security_engine.py` |
| `MazdaBackdoor` (muts12) | `C2Interface` | `app/muts/network/c2_backdoor.py` (file stays, class renamed) |
| `MazdaECUExploit` (muts13) | `MazdaECUAccess` | `app/muts/ecu/ecu_exploits.py` |
| `DiagnosticExploits` (muts13) | (embedded in `MazdaECUAccess`) | `app/muts/ecu/ecu_exploits.py` |
| `CANInjection` (muts13) | `CANSessionControl` | `app/muts/ecu/ecu_exploits.py` |
| `SecurityAccessLevel` (mds1) | `SecurityAccessLevel` | `app/mds/protocols/diagnostic_protocols.py` |

## SRS / Safety

| Prototype Name | Production Name | Location |
|---|---|---|
| `SRSAirbag` (muts2) | `SRSAirbag` | `app/muts/safety/srs_airbag.py` |
| `SRSAirbagExploiter` (muts4) | (merged into `SRSAirbag`) | `app/muts/safety/srs_airbag.py` |

## EEPROM / Memory

| Prototype Name | Production Name | Location |
|---|---|---|
| `EEPROMExploiter` (muts3) | `EEPROMExploiter` | `app/muts/eeprom/eeprom_exploiter.py` |
| `ComponentWearReset` (muts3) | `WearResetManager` | `app/muts/eeprom/wear_reset_manager.py` (planned) |
| `DPFEGR` (muts1) | `DPF_EGR_Manager` | `app/muts/security/security_engine.py` |

## Racing / Performance

| Prototype Name | Production Name | Location |
|---|---|---|
| `RacingFeatureController` (muts8) | `RacingFeatureController` | `app/muts/racing/racing_exploits.py` |
| `DiagnosticExploiter` (muts8) | `DiagnosticAccessManager` | `app/muts/diagnostics/advanced_diagnostics.py` (planned) |
| `SpecialFeatures` (muts2) | `RaceFeaturesManager` | `app/muts/racing/race_features_manager.py` (planned) |
| `AntiLagSystem` (add14) | `AntiLagSystem` | `app/services/performance_features.py` |
| `TwoStepRevLimiter` (add14) | (merged into AntiLagSystem) | `app/services/performance_features.py` |
| `LaunchControlSystem` (add14) | (merged into AntiLagSystem) | `app/services/performance_features.py` |

## Dark Web / Knowledge

| Prototype Name | Production Name | Location |
|---|---|---|
| `DarkWebIntelligence` (add2) | `KnowledgeSourceRegistry` | `app/muts/data/knowledge_source_registry.py` (planned) |
| `BlackMarketTuning` (add2) | (merged into KnowledgeSourceRegistry) | (planned) |
| `CriminalEnterpriseTools` (add2) | (not implemented — excluded from prod) | N/A |
| `AdvancedExploitation` (add2) | (not implemented — excluded from prod) | N/A |
| `IllegalMarketAnalysis` (add2) | (not implemented — excluded from prod) | N/A |

## Race Engineering / Dealership Secrets

| Prototype Name | Production Name | Location |
|---|---|---|
| `MazdaRaceEngineering` (muts14) | `RaceEngineeringData` | `app/muts/data/race_engineering_data.py` (planned) |
| `MazdaDealershipSecrets` (muts14) | `DealershipProcedures` | `app/muts/data/dealership_procedures.py` (planned) |
| `AdvancedTuningSecrets` (muts14) | `TuningKnowledgeBase` | `app/muts/data/tuning_knowledge_base.py` (planned) |
| `MazdaSpeed3RaceTuning` (muts14) | `RaceTuneGenerator` | `app/muts/tuning/race_tune_generator.py` (planned) |

## ADD Modules

| Prototype Name | Production Name | Location |
|---|---|---|
| `ADD24ECUExploit` (add24) | `EngineComponentDatabase` | `app/muts/data/engine_component_database.py` (planned) |

## General Pattern

```
*Exploit        → *Access | *Manager | *Handler
*Backdoor       → *Interface | *Gateway | *Bridge
*DarkWeb        → *KnowledgeBase | *SourceRegistry
*Illegal*       → (excluded from production)
*Hijack*        → *Override* | *Custom* | *Advanced*
Criminal*       → (excluded from production)
```

Any class matching a pattern in the "excluded" row should be flagged as
intentionally not ported, not as an accidental omission.
