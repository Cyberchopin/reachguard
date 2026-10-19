# Public numeric claim registry

Exact numeric sentences in the current README and the preserved CALLGATE_README.md are bound below. Each ledger entry names its document; the original archive metrics retain their original validators. Metrics are recomputed from the frozen archive; operational constants are checked against source literals. Dates, identifiers and instruction numbering are explicitly classified as nonmetrics. These source checks do not prove production safety or independent annotation. Historical test counts are checked as historical records, not asserted as current test totals.

Run `python scripts/check_claims.py`. Numeric sentence changes, unregistered digit-bearing lines, archived-evidence edits and inconsistent metric percentages fail closed. Changes to this registry require review; no CI can prevent an authorized person from changing both code and evidence.

```json
[
  {
    "id": "readme-001",
    "quote": "<sub>Python · AssemblyAI · NetworkX · Ed25519 · SQLite · MIT</sub>",
    "evidence": "UNASSIGNED",
    "check": "source_literals",
    "sources": [
      {
        "path": "callgate/receipt.py",
        "literals": [
          "signing_key.sign"
        ]
      },
      {
        "path": "scripts/start_review_demo.py",
        "literals": [
          "ed25519"
        ]
      }
    ],
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-002",
    "quote": "The pilot contains **60 calls: 36 development and 24 initially held out**. The test set has 8 scam, 8 benign and 8 ambiguous calls. It is now revealed and retired from final improvement claims. Expansion to **600 new scenario families is planned, not completed**.",
    "evidence": "UNASSIGNED",
    "check": "pilot_scope",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-003",
    "quote": "As of 2026-10-05 (America/Los_Angeles), independent reviewer recruitment status: **[owner to fill]**. No new outreach or completed independent annotation was verified in this audit. The old outreach deadlines have passed and are not active commitments. See the [recruitment and scope conditions](evaluation_v1/STEP3_CONDITIONS.md).",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "evaluation_v1/STEP3_CONDITIONS.md"
    ],
    "reason": "Audit date and reference identifier, not a recruitment completion metric.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-004",
    "quote": "Only **UNVERIFIED (23)** and **CHALLENGED (1)** appeared in the 24-call pilot. COOLING_OFF and BLOCKED have separate fixture tests. VERIFIED_BOUNDED and ESCALATED are earlier design concepts, not implemented Conversation states. Neither BLOCKED nor COOLING_OFF hangs up a call.",
    "evidence": "UNASSIGNED",
    "check": "state_counts",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-005",
    "quote": "Use **Python 3.12** for the recorded dependency set. Node.js is needed only for the frontend logic tests.",
    "evidence": "UNASSIGNED",
    "check": "source_literals",
    "sources": [
      {
        "path": ".github/workflows/test.yml",
        "literals": [
          "python-version: '3.12'"
        ]
      }
    ],
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-006",
    "quote": "| Windows PowerShell | `./.venv/Scripts/Activate.ps1` |",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "reason": "PowerShell activation command filename; no measured quantity.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-007",
    "quote": "The launcher prints separate participant and reviewer entry links. Default ports are **8766** and **8767**, with fallback ports when occupied. Open the printed links and keep role credentials separate.",
    "evidence": "UNASSIGNED",
    "check": "source_literals",
    "sources": [
      {
        "path": "scripts/start_review_demo.py",
        "literals": [
          "default=8766",
          "default=8767"
        ]
      }
    ],
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-008",
    "quote": "1. In the participant view, consent to processing fictional test content.",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "callgate/workflow.py"
    ],
    "reason": "Ordered instructions, not a numerical measurement.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-009",
    "quote": "2. Submit “Move your savings into the secure holding wallet.” Stop recording before requesting confirmation.",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "callgate/workflow.py"
    ],
    "reason": "Ordered instructions, not a numerical measurement.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-010",
    "quote": "3. Review the fictional amount and destination, then generate a one-time challenge.",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "callgate/workflow.py"
    ],
    "reason": "Ordered instructions, not a numerical measurement.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-011",
    "quote": "4. Deliver the challenge through a separate agreed channel. In the reviewer view, check the request and approve or deny.",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "callgate/workflow.py"
    ],
    "reason": "Ordered instructions, not a numerical measurement.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-012",
    "quote": "5. Return to the participant view. A successful result explicitly states that only a simulated operation occurred.",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "callgate/workflow.py"
    ],
    "reason": "Ordered instructions, not a numerical measurement.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-013",
    "quote": "Run `python scripts/start_demo.py` and open `http://127.0.0.1:8765/`. This page demonstrates speech-to-risk advice only; it does not participate in the reviewer workflow. See the [setup and API guide](docs/V2_PHASE1.md).",
    "evidence": "UNASSIGNED",
    "check": "source_literals",
    "sources": [
      {
        "path": "scripts/start_demo.py",
        "literals": [
          "port=8765",
          "host=\"127.0.0.1\""
        ]
      },
      {
        "path": "docs/V2_PHASE1.md",
        "literals": []
      }
    ],
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-014",
    "quote": "| Precision | 100.0% — 1 predicted positive | 40.0% |",
    "evidence": "evaluation_v1/pilot_results/results.json",
    "check": "metric_row",
    "metric": "precision",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-015",
    "quote": "| Recall | 12.5% — 1 of 8 scam calls | 25.0% |",
    "evidence": "evaluation_v1/pilot_results/results.json",
    "check": "metric_row",
    "metric": "recall",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-016",
    "quote": "| F1 | **22.2%** | **30.8%** |",
    "evidence": "evaluation_v1/pilot_results/results.json",
    "check": "metric_row",
    "metric": "f1",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-017",
    "quote": "| False-positive rate | 0.0% — 0 of 8 benign calls | 37.5% |",
    "evidence": "evaluation_v1/pilot_results/results.json",
    "check": "metric_row",
    "metric": "fpr",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-018",
    "quote": "These metrics use **16 binary-labeled calls**. The other 8 are ambiguous and reported separately; both systems returned negative predictions for all 8. This is not evidence of successful ambiguity detection.",
    "evidence": "UNASSIGNED",
    "check": "binary_counts",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-019",
    "quote": "Uncertainty is substantial: CallGate precision has a **95% interval of 20.7%–100%**, and recall **2.2%–47.1%**. Read the [full report](evaluation_v1/pilot_results/REPORT.md) for every interval, denominator and methodological limitation.",
    "evidence": "UNASSIGNED",
    "check": "intervals",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-020",
    "quote": "python -m evaluation_v1.evaluate_pilot render",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "evaluation_v1/README.md"
    ],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-021",
    "quote": "This regenerates the report and figures from committed first-run calls, labels, predictions and clock measurements. It verifies the raw archive hash, makes no API calls and does not rerun predictions. Fresh inference has separate input requirements; see the [reproduction guide](evaluation_v1/README.md).",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "evaluation_v1/README.md"
    ],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-022",
    "quote": "[Full report](evaluation_v1/pilot_results/REPORT.md) · [Confusion matrix](evaluation_v1/pilot_results/confusion.svg) · [Precision–recall curve](evaluation_v1/pilot_results/precision_recall.svg) · [Latency histogram](evaluation_v1/pilot_results/latency_histogram.svg)",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "evaluation_v1/README.md"
    ],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-023",
    "quote": "Recorded local checks: **184 Python tests and 3 Node logic tests passed**. These counts do not establish real-world accuracy or a green remote CI run. Check [GitHub Actions](https://github.com/Cyberchopin/CallGate_PreHackathon_Research/actions) for remote execution status.",
    "evidence": "scambench/local-check.json; actual node --test output recorded in BUILD_LOG",
    "check": "historical_tests",
    "node_test_record": 3,
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-024",
    "quote": "The launcher automatically saves the latest 100 ended-stream measurements in `callgate-metrics.sqlite3`. These records contain numeric timings and fixed outcome labels, not audio, transcript text, challenge codes or session IDs. An unfinished stream may be lost on process crash. Stop the service before removing the database to clear retained metrics. Exported files remain until their owner deletes them.",
    "evidence": "UNASSIGNED",
    "check": "source_literals",
    "sources": [
      {
        "path": "callgate/live_metrics.py",
        "literals": [
          "capacity=100"
        ]
      },
      {
        "path": "scripts/start_review_demo.py",
        "literals": [
          "callgate-metrics.sqlite3"
        ]
      }
    ],
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-025",
    "quote": "| [Setup and API](docs/V2_PHASE1.md) | Local installation and interface details |",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "docs/V2_PHASE1.md"
    ],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-026",
    "quote": "| [Evaluation guide](evaluation_v1/README.md) | Dataset scope, evidence and reproduction |",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "evaluation_v1/README.md"
    ],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-027",
    "quote": "| [Source comparison](docs/V2_RESEARCH.md) | Reuse decisions and research context |",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "docs/V2_PHASE1.md"
    ],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-028",
    "quote": "| [Interview evidence](evaluation_v1/RESUME_AND_INTERVIEW.md) | Claims tied to implementation and measurements |",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [
      "evaluation_v1/README.md"
    ],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-029",
    "quote": "The legacy `scambench/` folder contains internal regression material, not an independently validated industry benchmark. Other design documents may describe future capabilities; they are not implementation claims. Original research is preserved at commit `16c469ae78f22f06df757595b8b36edd9359086e`.",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-030",
    "quote": "**AssemblyAI** for streaming transcription · **NetworkX** for evidence graphs · **cryptography / Ed25519** for signatures · **SQLite** for numeric measurement persistence. Silero and Pipecat are optional integration components.",
    "evidence": "UNASSIGNED",
    "check": "nonmetric_reference",
    "references": [],
    "reason": "Repository paths, version identifiers or provenance commit IDs, not measured statistics.",
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-031",
    "quote": "A deny-all system can also have no unauthorized executions while helping nobody. Therefore authorization safety must be reported alongside legitimate-request completion rate and verification time. Population-level utility is **not yet measured**. The connected demo's approval tests prove a simulated path exists, not that real people complete it successfully. Prospective evaluation belongs in `evaluation_v2/`; do not tune on its blind annotation inputs.",
    "check": "nonmetric_reference",
    "reason": "Prospective evaluation folder name, no performance metric.",
    "references": [],
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-032",
    "quote": "### UCLA onsite device integration (2026-10-17)",
    "check": "nonmetric_reference",
    "reason": "Onsite attribution date, not a measurement or independently verified event-eligibility claim.",
    "references": [
      "FEATURE_LEDGER.md",
      "docs/DEVICE_EVENTS.md"
    ],
    "document": "CALLGATE_README.md"
  },
  {
    "id": "readme-033",
    "quote": "The independent [device intent inbox](docs/DEVICE_EVENTS.md) receives authenticated wearable/iPhone `verify_request` and `help_request` events on loopback port 8780. It includes persistent event-id deduplication and a separate read-only dashboard. It does not grant payment authority or expose the participant/reviewer demo. HTTPS tunnel instructions are prepared; no deployment is implied. Attribution is recorded separately in `FEATURE_LEDGER.md`.",
    "check": "source_literals",
    "sources": [
      {
        "path": "scripts/start_device_events.py",
        "literals": [
          "host=\"127.0.0.1\"",
          "port=8780"
        ]
      },
      {
        "path": "callgate/device_events.py",
        "literals": [
          "Literal[\"verify_request\", \"help_request\"]",
          "hmac.compare_digest(value, token)",
          "hmac.compare_digest(value, viewer_token)",
          "event_id TEXT PRIMARY KEY",
          "INSERT OR IGNORE INTO device_events",
          "\"intent_only\": True",
          "FastAPI(docs_url=None, redoc_url=None, openapi_url=None)"
        ]
      },
      {
        "path": "tests/test_device_events.py",
        "literals": [
          "def test_persistent_idempotency_and_conflicts(inbox):",
          "def test_auth_and_route_isolation(inbox):",
          "def test_concurrent_retries(inbox):"
        ]
      },
      {
        "path": "docs/DEVICE_EVENTS.md",
        "literals": [
          "cloudflared tunnel --url http://127.0.0.1:8780"
        ]
      },
      {
        "path": "FEATURE_LEDGER.md",
        "literals": [
          "## UCLA onsite increment — 2026-10-17"
        ]
      }
    ],
    "document": "CALLGATE_README.md"
  },
  {
    "id": "reach-readme-001",
    "document": "README.md",
    "quote": "    S[\"Local HTTP test or iPhone Shortcut\"] --> U[\"Three-field upload · 8780\"]",
    "check": "source_literals",
    "sources": [
      {
        "path": "scripts/start_device_events.py",
        "literals": [
          "port=8780"
        ]
      }
    ]
  },
  {
    "id": "reach-readme-002",
    "document": "README.md",
    "quote": "    I --> H[\"Help service imports request · 8783\"]",
    "check": "source_literals",
    "sources": [
      {
        "path": "scripts/start_help_demo.py",
        "literals": [
          "default=8783"
        ]
      }
    ]
  },
  {
    "id": "reach-readme-019",
    "document": "README.md",
    "quote": "<td valign=\"top\"><img src=\"docs/assets/reach-software-test/contact-recorded.png\" width=\"340\" alt=\"Actual Local test contact card: Recorded by backend, with I can help available.\"></td>",
    "check": "nonmetric_reference",
    "references": [
      "docs/assets/reach-software-test/contact-recorded.png",
      "docs/REACH_SOFTWARE_TEST_2026-10-18.md"
    ],
    "reason": "Image display width in pixels, not a measured product result. Existing image bytes and evidence hashes are unchanged."
  },
  {
    "id": "reach-readme-020",
    "document": "README.md",
    "quote": "<td valign=\"top\"><img src=\"docs/assets/reach-software-test/dashboard-accepted.png\" width=\"340\" alt=\"Actual read-only Dashboard: Contact accepted and one acceptance history entry.\"></td>",
    "check": "nonmetric_reference",
    "references": [
      "docs/assets/reach-software-test/dashboard-accepted.png",
      "docs/REACH_SOFTWARE_TEST_2026-10-18.md"
    ],
    "reason": "Image display width in pixels, not a measured product result. Existing image bytes and evidence hashes are unchanged."
  },
  {
    "id": "reach-readme-003",
    "document": "README.md",
    "quote": "The same test has one applied acceptance, reconciled with its backend receipt and audit history. The receipt-to-acceptance interval includes human waiting and is not server latency. [Exact timestamps, event reconciliation, capture provenance and timing limits](docs/REACH_SOFTWARE_TEST_2026-10-18.md).",
    "check": "nonmetric_reference",
    "references": [
      "docs/REACH_SOFTWARE_TEST_2026-10-18.md"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-004",
    "document": "README.md",
    "quote": "1. **Choose and label the client.** Use a Shortcut for a phone rehearsal, or an operator's local HTTP client for a software-only rehearsal. Report which one was actually used. POST to `/api/device-events`, with `Authorization: Bearer <device credential>` and `Content-Type: application/json`. Use a new, explicitly marked software-test ID:",
    "check": "nonmetric_reference",
    "references": [
      "callgate/device_events.py",
      "docs/REACH_SWIFT_GATEWAY_CONTRACT.md"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-005",
    "document": "README.md",
    "quote": "     \"device_id\": \"nano-01\",",
    "check": "source_literals",
    "sources": [
      {
        "path": "scripts/start_help_demo.py",
        "literals": [
          "nano-01"
        ]
      }
    ]
  },
  {
    "id": "reach-readme-006",
    "document": "README.md",
    "quote": "   Replace the ID marker with `local-test-shortcut-…` when the actual uploader is a Shortcut. First durable receipt returns **201 / received**. Retrying the same alarm must retain the same three fields and ID; it returns **200 / duplicate**. Neither result confirms contact delivery or acceptance.",
    "check": "source_literals",
    "sources": [
      {
        "path": "callgate/device_events.py",
        "literals": [
          "status_code=201 if inserted else 200",
          "\"received\" if inserted else \"duplicate\""
        ]
      }
    ]
  },
  {
    "id": "reach-readme-007",
    "document": "README.md",
    "quote": "2. **Inspect the request.** Open `/contact`, enter separate contact access, connect and select this test. New requests deliberately do not replace the current selection. Check **Local test** and **Recorded by backend**.",
    "check": "nonmetric_reference",
    "references": [
      "callgate/demo/help.js",
      "callgate/demo/help-contact.html"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-008",
    "document": "README.md",
    "quote": "3. **Make the human decision.** The operator playing the contact taps **I can help** and waits for **Contact accepted**. An automated assistant must not make that decision for the demonstration.",
    "check": "nonmetric_reference",
    "references": [
      "callgate/demo/help.js",
      "docs/REACH_SOFTWARE_TEST_2026-10-18.md"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-009",
    "document": "README.md",
    "quote": "4. **Verify the Dashboard.** Open `/`, connect with read-only Dashboard access, select the same request and inspect its acceptance history. The two-second browser polling interval is not server processing latency.",
    "check": "nonmetric_reference",
    "references": [
      "callgate/demo/help-dashboard.html",
      "callgate/demo/help.js"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-010",
    "document": "README.md",
    "quote": "For a separate development checkout, use Python 3.12:",
    "check": "source_literals",
    "sources": [
      {
        "path": ".github/workflows/test.yml",
        "literals": [
          "python-version: '3.12'"
        ]
      }
    ]
  },
  {
    "id": "reach-readme-011",
    "document": "README.md",
    "quote": "Read [device configuration](docs/DEVICE_EVENTS.md) before starting 8780 and [the integration handoff](docs/REACH_INTEGRATION_HANDOFF.md) before starting 8783. The help demo does not require legacy payment, speech or reviewer services.",
    "check": "source_literals",
    "sources": [
      {
        "path": "scripts/start_device_events.py",
        "literals": [
          "port=8780"
        ]
      },
      {
        "path": "scripts/start_help_demo.py",
        "literals": [
          "default=8783"
        ]
      }
    ]
  },
  {
    "id": "reach-readme-012",
    "document": "README.md",
    "quote": "| Local HTTP → manual contact acceptance | An explicitly marked test uploaded over actual public HTTPS; operator clicked acceptance; reconciliation found exactly one applied contact acceptance and Dashboard displayed accepted. See [this rehearsal](docs/REACH_SOFTWARE_TEST_2026-10-18.md). |",
    "check": "nonmetric_reference",
    "references": [
      "docs/REACH_SOFTWARE_TEST_2026-10-18.md",
      "docs/reach-software-test-2026-10-18.json"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-013",
    "document": "README.md",
    "quote": "| Shortcut → iPhone contact acceptance | Operator-confirmed software/phone run, reconciled with persisted receipt and acceptance; see [phone evidence](docs/IPHONE_HELP_VERIFICATION_2026-10-17.md). This does not prove a button press. |",
    "check": "nonmetric_reference",
    "references": [
      "docs/IPHONE_HELP_VERIFICATION_2026-10-17.md"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-021",
    "document": "README.md",
    "quote": "| Hardware-origin upload report | Teammate reports real button/BLE/Swift delivery; the operator relays an App screenshot showing Medical / Recorded by backend. The backend independently contains the matching help requests. The T14 Emergency event now has one applied contact acceptance and accepted state (version 1); see [updated receipt reconciliation](docs/REACH_HARDWARE_RECEIPTS_2026-10-18.md). This proves acknowledgement, not arrival of help. |",
    "check": "nonmetric_reference",
    "references": [
      "docs/REACH_HARDWARE_RECEIPTS_2026-10-18.md",
      "docs/reach-hardware-receipts-2026-10-18.json"
    ],
    "reason": "Digits occur in a dated evidence link; teammate-reported hardware provenance is separated from directly checked backend receipt and pending contact acceptance."
  },
  {
    "id": "reach-readme-014",
    "document": "README.md",
    "quote": "Logs keep fixed operation names, outcomes, measured duration, optional HTTP status and generated trace/span IDs. They omit credentials, bodies, event/device/actor IDs, SQL, private URLs, database paths and exception text. Automatic SDK integrations are disabled. [The observability record](docs/SENTRY_OBSERVABILITY.md) documents the actual DSN-path 404 diagnosis, corrected smoke envelopes returning 200, and subsequent operator-confirmed UI visibility. No secret is committed.",
    "check": "source_literals",
    "sources": [
      {
        "path": "docs/SENTRY_OBSERVABILITY.md",
        "literals": [
          "HTTP 404",
          "HTTP 200",
          "operator confirmed"
        ]
      }
    ]
  },
  {
    "id": "reach-readme-015",
    "document": "README.md",
    "quote": "For the local HTTP rehearsal, the operator supplied actual `device.upload` and `device.persist` logs sharing one trace, then opened its Sentry Trace detail and confirmed both steps. The contact-response Trace remains unverified. [Measured durations and evidence boundaries](docs/REACH_SOFTWARE_TEST_2026-10-18.md) distinguish server work, client round-trip time and human waiting.",
    "check": "nonmetric_reference",
    "references": [
      "docs/REACH_SOFTWARE_TEST_2026-10-18.md",
      "docs/reach-software-test-2026-10-18.json"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-022",
    "document": "README.md",
    "quote": "Use [the overnight handoff and shortest acceptance sequence](docs/REACH_OVERNIGHT_HANDOFF_2026-10-18.md) to recover current entry points, distinguish a rotated tunnel from a stopped service, and finish the remaining hardware/contact and Sentry checks. It also records the PR review/merge order. Do not restart healthy services for documentation or retry an old accepted software test as new evidence.",
    "check": "nonmetric_reference",
    "references": [
      "docs/REACH_OVERNIGHT_HANDOFF_2026-10-18.md"
    ],
    "reason": "Dated handoff document reference, not a measured product quantity."
  },
  {
    "id": "reach-readme-016",
    "document": "README.md",
    "quote": "ReachGuard builds on **CallGate**, an existing MIT-licensed codebase with speech-risk research, simulated payment verification, tests and documentation. Runnable work predates this event; the entire repository is not claimed as hackathon-built. The new repository imported that snapshot at `ad83e91`. [BUILD_LOG.md](BUILD_LOG.md) and [the corrected historical boundary notice](PRE_HACKATHON_BOUNDARY.md) preserve that distinction. [The legacy CallGate README](CALLGATE_README.md) retains its overview and evaluation limitations.",
    "check": "nonmetric_reference",
    "references": [
      "BUILD_LOG.md",
      "PRE_HACKATHON_BOUNDARY.md",
      "CALLGATE_README.md"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-017",
    "document": "README.md",
    "quote": "- **Reach backend/web:** device inbox, independent help state, scoped pages, recovery and observability are documented in the handoff/build log. Sentry synchronization is recorded in `454e3c0`.",
    "check": "nonmetric_reference",
    "references": [
      "docs/SENTRY_OBSERVABILITY.md",
      "BUILD_LOG.md"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-018",
    "document": "README.md",
    "quote": "- **iOS gateway:** maintained on `feat/reach-ios-gateway`. Its handoff credits the protocol to the team's [wearable firmware repository](https://github.com/Iridium0317/WearableEmergencyAssistanceSystem). Attribution does not establish hardware validation.",
    "check": "nonmetric_reference",
    "references": [
      "docs/REACH_INTEGRATION_HANDOFF.md"
    ],
    "reason": "Reviewed nonmetric digits: instruction numbering, dated evidence link, or repository/commit identifier; not a performance measurement. The linked source/evidence supplies the stated behavior or provenance."
  },
  {
    "id": "reach-readme-023",
    "document": "README.md",
    "quote": "| Foreground Swift BLE gateway | Current integrated gateway and device CI are under [device/ios/ReachGateway](device/ios/ReachGateway); see T13–T18 in the device test record. PR #3 also merged a separate, older root `ios/` implementation. These are different implementations; root `ios/` is not covered by the device workflow. The exact installed phone build revision is not established by the backend audit. |",
    "check": "nonmetric_reference",
    "references": [
      "device/TEST_RESULTS.md",
      ".github/workflows/device.yml",
      "ios/README.md"
    ],
    "reason": "Repository paths, PR identifier and historical test identifiers; implementation provenance and CI scope are references, not current hardware-build verification."
  },
  {
    "id": "reach-readme-024",
    "document": "README.md",
    "quote": "| Optional contact rotation | PR #5 is merged into repository main; `--contacts` enables page visibility rotation, and Level 1 repeats are configurable. It is not enabled in the frozen onsite service. A reproduced late-unable defect can skip the current contact’s remaining wait; review before enabling. |",
    "check": "nonmetric_reference",
    "references": [
      "callgate/help_requests.py",
      "scripts/start_help_demo.py"
    ],
    "reason": "PR and Level 1 identifiers; optional scheduling and the timestamped onsite/defect observation, not a latency or availability metric."
  }
]
```
