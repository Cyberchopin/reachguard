# Final-product rehearsal and recovery runbook

Run locally. Do not expose loopback services to the public network. Construction date is recorded honestly; event eligibility is separate from product readiness.

## Setup and validation

```bash
python -m pip install -r requirements-lock.txt -r requirements-verification.txt -r requirements-safety.txt
python -m pytest -q -p no:cacheprovider
node --test tests/review_ui.test.cjs
python scripts/check_claims.py
python evaluation_v2/verify_inputs.py
python -m scripts.proof_demo
python -m scripts.start_review_demo
```

Open the exact printed URLs. Do not manually reuse an old role token. Text fallback needs no API key. Do not broadcast or record the launcher's secret role URLs.

## Failure decisions

| Failure | Next operation | Disclosure |
|---|---|---|
| No saved identity selected | Click **读取已登记联系人**, select the synthetic startup identity, and retry before expiry; run `python -m scripts.start_review_demo --contact-identity fictional-parent` for a fresh fictional configuration | Trusted-startup routing, not independent human enrollment |
| Wrong reviewer sees no request | Read the selected claimed identity; use its labeled startup URL. For separate roles run `python -m scripts.start_review_demo --contact-identity saved-family --contact-identity saved-bank` | No fallback to a different contact; never share all reviewer entries with the participant |
| Contact denies or request times out | Stop the attempted action and verify through a known saved channel; for a separate fictional rehearsal click **结束本场并开始新的独立测试** and obtain fresh consent | Changing identity or amount cannot authorize the denied session |
| Internet unavailable | Stop microphone; select text language and paste fictional script; click text input | Text-to-policy demo, not live audio |
| AssemblyAI fails or key absent | Stop microphone; use text fallback; do not repeatedly retry provider | External transcription unavailable |
| Mandarin ASR fails | Preserve the observed failure; replay the exact intended script through Chinese text selection in a fresh session | Bilingual text rules tested; Mandarin streaming unvalidated |
| Reviewer page cannot connect | Stop launcher; rerun `python -m scripts.start_review_demo`; use newly printed URLs | Old approvals and keys are invalidated by restart |
| Phone cannot open localhost | Use separate browser role tabs on the trusted host | Enrolled two-device delivery is not implemented; do not bind services publicly as a workaround |
| Protected-action response is not forbidden | Stop demo; run `python -m pytest tests/test_review_transport.py -q -p no:cacheprovider` | Demo-blocking regression; never pretend refusal occurred |
| Need offline counterfactual proof | Run `python -m scripts.proof_demo`; display empty-detector refusal and valid signed simulation | Integration rehearsal, not real-person utility evaluation |
| Receipt validation fails | Check public key against trusted source and expected session; run `python -m scripts.verify_receipt RECEIPT.json --public-key EXPECTED_HEX --session EXPECTED_SESSION` | Receipt integrity unconfirmed |
| Claims checker fails | Read claim ID and compare archive; do not edit measurements to pass | Public metric remains unresolved |
| Corpus hash changes | Stop input use; run `git diff -- evaluation_v2`; explain and version an intentional change | No silent re-freeze or label edits |

## Audio contingency inventory

No prerecorded WAVs are shipped with this increment. Planned inputs: fictional bilingual family emergency; benign family conversation; government impersonation; credential request. These need consented synthesis/recording and provenance before audio claims. Text fallback is available now.

Local transcription feasibility: CPU inference may work for short clips but model downloads, codec conversion, Mandarin accuracy, memory and real-time factor are not yet measured. GPU availability is unknown. Do not install a large inference stack during a failing live demo or claim it is already a fallback. This is an assessment only.

## Freeze and rehearsal

Final preparation window: no new features; only repair a test-proven demo blocker. Record changes in BUILD_LOG and rerun the affected tests and full suite. Rehearse refusal, valid simulated completion, reviewer denial, stale request, reset and withdrawal. Capture an offline screen recording locally only after the live path succeeds; there is no supplied prerecorded demo yet.

## Build stages

| Stage | Exit condition |
|---|---|
| Baseline | Source commit and tests recorded |
| Vertical slice | Live/text evidence reaches participant and current reviewer simulation |
| Safety policy | Bilingual fixtures and monotonicity properties pass |
| Identity work | Claimed identity maps to enrolled contact; same-origin self-approval tested; currently incomplete |
| Evaluation | Independent labels returned before new-corpus system inference; safety and utility reported together |
| Presentation | Recorded live proof and honest failure disclosures; no future storyboard masquerading as shipped work |

Do not assign an invented hacking duration to an event whose official schedule still needs confirmation.
