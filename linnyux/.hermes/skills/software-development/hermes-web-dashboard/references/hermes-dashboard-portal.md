# Hermes dashboard / portal setup notes

Session-derived notes for starting and registering the Hermes web dashboard.

## What worked
- `hermes dashboard --no-open` starts the Hermes web UI server in the background.
- Default local URL observed: `http://127.0.0.1:9119/`.
- Browser verification should confirm the page title is `Hermes Agent - Dashboard` and the nav loads.
- `hermes config set dashboard.oauth.client_id agent:cmrgedtjy0018hs0akxnarwp3` successfully wrote the config entry to `~/.hermes/config.yaml`.

## Distinctions to remember
- Hermes dashboard is not Obelisk.
- `hermes dashboard` = browser UI.
- `hermes serve` = same backend, headless.
- `hermes setup --portal` is Nous Portal onboarding for the model/tool gateway, not dashboard registration.

## OAuth registration flow
- The dashboard OAuth client registration path lives in `hermes dashboard register`.
- That command is the right way to mint a self-hosted dashboard client ID for a public or remotely reachable dashboard.
- `--redirect-uri` should be the full HTTPS callback URL only for public deployment.
- For localhost-only usage, omit the redirect URI.

## Verification pattern
1. Start the dashboard.
2. Wait for a ready line in the server output.
3. Load the URL in a browser.
4. Confirm it returns the Hermes dashboard, not a different app.
5. If the page responds 500, inspect logs before assuming success.

## Useful commands observed
- `hermes dashboard --no-open`
- `hermes config set dashboard.oauth.client_id agent:cmrgedtjy0018hs0akxnarwp3`
- `hermes dashboard register --name <name> --redirect-uri https://host/auth/callback`
