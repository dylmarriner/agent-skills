# Worked example: GCP role-request remediation (2026-08)

Project: **ai-system-495310** ("AI-System", projectNumber 461493450955, no parent org/folder — standalone project)
Owner: dkmarriner@gmail.com (gcloud default account on lin)

## The request
Email from GCP: inhumanekiller22@gmail.com requested a role on ai-system-495310.
Requestor message: Claude Code `/login` succeeded, then "can you index the code of this project..."
then `API Error: 403 [{error:{code:403,message:This API method requires billing to be enabled. Please
enable billing on project #ai-system-495310 ...`

## Diagnosis sequence (all confirmed commands)
1. `gcloud auth list` → dkmarriner@gmail.com active; two project SAs (dkmarriner-534, vertex-express)
2. `gcloud projects describe ai-system-495310` → lifecycleState: ACTIVE (project itself was fine)
3. `gcloud billing projects describe ai-system-495310` → billingEnabled: **false**, but billingAccountName WAS set: billingAccounts/01E2B2-7B63DD-24DDC6
4. `gcloud billing accounts describe 01E2B2-7B63DD-24DDC6` → **open: false** ← root cause. Account "My Billing Account" (NZD) was CLOSED.
5. `gcloud billing accounts list` → only ONE account exists, and it's closed. No other account to link.
6. `gcloud projects get-iam-policy ... --format=json > /tmp/iam.json` → requestor had ZERO roles.

## Attempted automated billing fixes (both FAIL, as expected)
- `gcloud billing accounts create` → "Invalid choice: 'create'" (subcommand does not exist)
- REST `POST https://cloudbilling.googleapis.com/v1/billingAccounts` with `{"displayName": "..."}` and with `{"parent": "projects/..."}` → both `400 INVALID_ARGUMENT`. Standalone (non-reseller) account creation is Console-only.

## Remediation that worked
- IAM: `gcloud projects add-iam-policy-binding ai-system-495310 --member="user:inhumanekiller22@gmail.com" --role="roles/editor" --condition=None` → succeeded.
- Verified: re-dump policy to /tmp/iam2.json, grep → `user:inhumanekiller22@gmail.com => roles/editor` ✓
- Billing: handed owner the Console steps (console.cloud.google.com/billing → Add billing account → card → link project). Closed accounts can't be reopened; a new account must be created and linked (`gcloud billing projects link` once it exists).

## Notes
- roles/editor was the default grant (full project work incl. Cloud Build / GCS / AI Platform). Owner would additionally cover IAM + createBillingAssignment.
- The email's troubleshooter token checks resourcemanager.projects.createBillingAssignment + resourcemanager.projects.get — i.e. requestor lacked billing-assignment ability. Granting editor + enabling billing covers it.
- rtk wrapper on lin corrupts `gcloud ... --format=json | python3` pipelines — always dump to a file first, parse the file.
