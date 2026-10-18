# Pre-Hackathon Boundary

> Historical plan, superseded on the v2 branch by the user's September 8, 2026 request to begin implementation now. See `BUILD_LOG.md`. The research-only claim below applies to original commit `16c469ae78f22f06df757595b8b36edd9359086e`, not this branch. Do not reuse the old submission template without updating its claims.

**Status:** research and planning only  
**Prepared:** September 2026  
**Target event:** LA Hacks AI Hackathon, October 17–18, 2026

## Purpose

LA Hacks permits open-source pre-existing work, but teams extending prior work must disclose which features were created during the event, and judging focuses on new functionality. This repository therefore contains no runnable CallGate product implementation before the event.

## Allowed before the event

- Problem research and an anonymized motivation statement
- Threat model, abuse cases, ethical principles, and safety requirements
- Architecture diagrams and non-executable interface specifications
- Evaluation plan, demo storyboard, backlog, and issue descriptions
- Vendor comparisons and public reference material
- A public, timestamped repository showing the boundary

## Reserved for the event

- Audio ingestion and real-time streaming
- Speech-to-text and deepfake-signal integration
- Parser service and model prompts
- Policy engine and state machine implementation
- Out-of-band verification service
- Capability-token and receipt implementation
- Frontend/dashboard, accessibility UI, and phone interface
- Tests, deployment, integrations, and the working demo

## Freeze procedure

Before the event:

1. Make this repository public under the MIT License.
2. Create a signed or annotated tag named `pre-hackathon-research-v1`.
3. Export the issue list and take a screenshot of the repository timestamp.
4. Do not add runnable product code before the official start.

At the event:

1. Record the official start time in `BUILD_LOG.md`.
2. Create branch `hackathon/la-hacks-2026` from the research tag.
3. Use small commits tied to backlog issue IDs.
4. Record every dependency, model, sponsor service, and team contribution.
5. In the submission, list the pre-existing documents and separately list all event-built functionality.

## Submission disclosure template

> Before LA Hacks, CallGate consisted only of public research, architecture, safety requirements, interface specifications, and a test plan. During the event, our team implemented the complete runnable system: [list exact components]. Judges can verify the boundary at tag `pre-hackathon-research-v1` and inspect all subsequent commits on `hackathon/la-hacks-2026`.

This document is an engineering disclosure, not legal advice. The team should re-check the official rules immediately before the event in case they change.

