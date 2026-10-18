"""Two loopback applications with separate capabilities; no human identity proof.

The broker owns the issuer and policy. Only the reviewer process holds the
reviewer signing key. Both processes and their host remain trusted.
"""
import asyncio
import hashlib
import hmac
import json
import math
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import Field
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from .confirmation import ConfirmationRequest, ReviewerDecision, decision_bytes
from .assemblyai import stream_pcm
from .live_metrics import LiveMetrics
from .workflow import ChallengeRateLimited
from .models import StrictModel, Transcript
from .sentry_observability import configure_sentry, log_security, trace_step

ASSETS = Path(__file__).parent / 'demo'


class Operation(StrictModel):
    destination: str = Field(min_length=1, max_length=80)
    amount_cents: int = Field(gt=0, le=100_000_000)


class ContactOperation(Operation):
    claimed_identity: str | None = Field(default=None, min_length=1, max_length=80,
        pattern=r'^[a-zA-Z0-9_-]+$')


class Approval(StrictModel):
    request_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    approved: bool
    challenge_response: str | None = Field(default=None, pattern=r'^\d{6}$')


class SubmittedDecision(StrictModel):
    decision: ReviewerDecision
    challenge_response: str | None = Field(default=None, pattern=r'^\d{6}$')


class ProcessingConsent(StrictModel):
    granted: bool


def guarded_app(origin, page):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    host = urlsplit(origin).netloc

    @app.middleware('http')
    async def boundary(request: Request, call_next):
        if request.headers.get('host') != host:
            return JSONResponse({'detail': 'invalid host'}, status_code=400)
        supplied = request.headers.get('origin')
        if supplied is not None and supplied != origin:
            return JSONResponse({'detail': 'invalid origin'}, status_code=403)
        # Authenticated Python-to-Python calls omit Origin; browsers cannot set
        # Authorization cross-origin without a preflight, which we do not allow.
        response = await call_next(request)
        response.headers.update({
            'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        })
        return response

    @app.get('/')
    def index():
        return FileResponse(ASSETS / page)

    @app.get('/review-ui.js')
    def javascript():
        return FileResponse(ASSETS / 'review-ui.js', media_type='text/javascript')

    @app.get('/review-ui.css')
    def css():
        return FileResponse(ASSETS / 'review-ui.css', media_type='text/css')

    @app.get('/pcm-worklet.js')
    def pcm_worklet():
        return FileResponse(ASSETS / 'pcm-worklet.js', media_type='text/javascript')

    return app


def bearer(token):
    def require(request: Request):
        header = request.headers.get('authorization', '')
        if not hmac.compare_digest(header.encode(), ('Bearer ' + token).encode()):
            raise HTTPException(401, 'role credential required')
    return require


def configured_asr_rate():
    """Optional user-supplied USD/hour rate; no vendor price is assumed."""
    raw = os.environ.get('CALLGATE_ASR_USD_PER_HOUR')
    if raw is None:
        return None
    try:
        rate = float(raw)
    except ValueError:
        return None
    return rate if math.isfinite(rate) and 0 <= rate <= 10_000 else None


def create_broker_app(workflow, participant_token, reviewer_token, *, origin='http://127.0.0.1:8766',
                      metrics_database=None, reviewer_identity=None, telemetry_transport=None,
                      device_inbox=None, fusion_state=None):
    if not isinstance(participant_token, str) or not participant_token:
        raise ValueError('distinct role credentials required')
    if isinstance(reviewer_token, dict):
        if reviewer_identity is not None:
            raise ValueError('ambiguous reviewer route configuration')
        reviewer_routes = dict(reviewer_token)
    else:
        reviewer_routes = {reviewer_identity: reviewer_token}
    values = list(reviewer_routes.values())
    if (not values or any(not isinstance(t, str) or not t for t in values)
            or len(set(values)) != len(values) or participant_token in values
            or any(k is not None and (not isinstance(k, str) or not k) for k in reviewer_routes)):
        raise ValueError('distinct role credentials required')
    if len(workflow.contact_identities()) > 1 and None in reviewer_routes:
        raise ValueError('explicit reviewer route identity required')
    app = guarded_app(origin, 'participant.html')
    configure_sentry(transport=telemetry_transport)
    live_metrics = LiveMetrics(database=metrics_database)
    receipt_key = Ed25519PrivateKey.generate()
    receipt_public = receipt_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    active_audio = set()

    async def stop_audio():
        tasks = list(active_audio)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    participant = bearer(participant_token)

    def reviewer(request: Request):
        header = request.headers.get('authorization', '').encode()
        found, principal = False, None
        for identity, token in reviewer_routes.items():
            if hmac.compare_digest(header, ('Bearer ' + token).encode()):
                found, principal = True, identity
        if not found:
            raise HTTPException(401, 'invalid role credential')
        return principal

    @app.get('/api/status', dependencies=[Depends(participant)])
    def status():
        return workflow.status()

    @app.get('/api/evidence', dependencies=[Depends(participant)])
    def evidence():
        return workflow.evidence_view()

    @app.get('/api/receipt-key', dependencies=[Depends(participant)])
    def receipt_verification_key():
        return {'algorithm': 'Ed25519', 'public_key_hex': receipt_public,
                'key_scope': 'ephemeral_broker_startup', 'identity_verified': False}

    @app.post('/api/receipt', dependencies=[Depends(participant)])
    def receipt():
        try:
            signed = workflow.decision_receipt(receipt_key)
        except ValueError:
            raise HTTPException(409, 'current consented evidence required') from None
        return {'schema_version': 'callgate-receipt-export-v1',
                'receipt': signed.model_dump(), 'public_key_hex': receipt_public,
                'trust_note': 'Pin the expected key independently; bundled key alone does not establish issuer identity.'}

    @app.get('/api/metrics/summary', dependencies=[Depends(participant)])
    def metrics_summary():
        return live_metrics.summary()

    @app.get('/api/metrics/export', dependencies=[Depends(participant)])
    def metrics_export():
        return JSONResponse(live_metrics.export(), headers={
            'Content-Disposition': 'attachment; filename="callgate-measurements.json"'})

    @app.post('/api/processing-consent', dependencies=[Depends(participant)])
    async def processing_consent(body: ProcessingConsent):
        result = workflow.set_processing_consent(body.granted)
        if not body.granted:
            await stop_audio()
        return result

    @app.post('/api/session/reset', dependencies=[Depends(participant)])
    async def reset_session():
        result = workflow.reset_session()
        await stop_audio()
        return result

    @app.post('/api/transcript', dependencies=[Depends(participant)])
    def ingest(body: Transcript):
        try:
            with trace_step('transcript_to_evidence', **workflow.telemetry_context()):
                result = workflow.ingest(body)
            log_security('policy_decision', policy_state=result['state'],
                         **workflow.telemetry_context())
            return result
        except ValueError:
            log_security('policy_decision_rejected', error_code='TRANSCRIPT_REJECTED',
                         **workflow.telemetry_context())
            raise HTTPException(409, 'transcript rejected') from None

    @app.websocket('/api/audio')
    async def audio(ws: WebSocket):
        if ws.headers.get('host') != urlsplit(origin).netloc or ws.headers.get('origin') != origin:
            await ws.close(code=1008)
            return
        await ws.accept()
        try:
            raw = await asyncio.wait_for(ws.receive_text(), 5)
            supplied = json.loads(raw)
            candidate = supplied.get('token', '') if supplied.get('type') == 'authenticate' else ''
            if not isinstance(candidate, str) or not hmac.compare_digest(candidate, participant_token):
                await ws.close(code=1008)
                return
            if not workflow.status()['processing_allowed']:
                await ws.send_json({'error': 'processing_consent_required'})
                await ws.close(code=1008)
                return
            if not os.environ.get('ASSEMBLYAI_API_KEY'):
                await ws.send_json({'error': 'assemblyai_not_configured'})
                await ws.close(code=1011)
                return
            if any(not task.done() for task in active_audio):
                await ws.send_json({'error': 'audio_already_active'})
                await ws.close(code=1008)
                return
            generation = workflow.processing_generation()
            provider_task = None
            started = time.perf_counter()
            first_audio_at = None
            audio_bytes = 0
            asr_rate = configured_asr_rate()
            first_alert_proxy_ms = None
            risk_engine_samples = []
            provider_timings = {}
            measurement_recorded = False
            ingress_prefix = secrets.token_hex(4)

            async def chunks():
                nonlocal audio_bytes, first_audio_at
                while True:
                    item = await asyncio.wait_for(ws.receive(), 30)
                    if item['type'] == 'websocket.disconnect':
                        raise WebSocketDisconnect()
                    if item.get('bytes') is not None:
                        if workflow.processing_generation() != generation:
                            raise ValueError('stale audio session')
                        pcm = item['bytes']
                        if not 1600 <= len(pcm) <= 32000 or len(pcm) % 2:
                            raise ValueError('invalid PCM frame')
                        if first_audio_at is None:
                            first_audio_at = time.perf_counter()
                        audio_bytes += len(pcm)
                        yield item['bytes']
                    elif item.get('text') == '{"type":"stop"}':
                        return
                    else:
                        raise ValueError('expected PCM bytes or stop')

            async def on_segment(segment):
                nonlocal first_alert_proxy_ms
                # AssemblyAI turn numbering restarts at zero for every socket.
                # Namespace it before adding evidence to the shared workflow.
                segment = segment.model_copy(
                    update={'segment_id': ingress_prefix + '-' + segment.segment_id})
                risk_started = time.perf_counter()
                with trace_step('transcript_to_evidence', **workflow.telemetry_context()):
                    result = workflow.ingest(segment, generation=generation)
                risk_ms = (time.perf_counter() - risk_started) * 1000
                log_security('policy_decision', policy_state=result['state'],
                             **workflow.telemetry_context())
                elapsed_ms = (time.perf_counter() - started) * 1000
                audio_ms = audio_bytes / 32
                proxy = None
                if first_audio_at is not None and 0 < segment.end_ms <= audio_ms:
                    observed = (time.perf_counter() - first_audio_at) * 1000 - segment.end_ms
                    if observed >= 0:
                        proxy = round(observed, 1)
                metrics = {
                    **provider_timings,
                    'audio_received_ms': round(audio_ms, 1),
                    'server_elapsed_ms': round(elapsed_ms, 1),
                    'risk_engine_ms': round(risk_ms, 3),
                    # Provider word timestamps and this server clock are only an
                    # observed demo proxy, not a telephony latency SLA.
                    'end_of_speech_to_alert_proxy_ms': proxy,
                    'asr_rate_usd_per_hour': asr_rate,
                    'estimated_asr_cost_usd': (None if asr_rate is None else
                        round((audio_ms/3_600_000)*asr_rate, 8)),
                    'cost_scope': 'asr_only_configured_rate',
                }
                risk_engine_samples.append(risk_ms)
                if segment.final and result['guardian']['emit'] and first_alert_proxy_ms is None:
                    first_alert_proxy_ms = metrics['end_of_speech_to_alert_proxy_ms']
                await ws.send_json({'transcript': segment.model_dump(), 'risk': result,
                                    'metrics': metrics})

            provider_task = asyncio.create_task(stream_pcm(chunks(), on_segment, timings=provider_timings))
            active_audio.add(provider_task)
            await asyncio.wait_for(provider_task, timeout=90)
            live_metrics.record(completed=True, audio_ms=audio_bytes / 32,
                first_alert_proxy_ms=first_alert_proxy_ms,
                risk_engine_ms=max(risk_engine_samples) if risk_engine_samples else None,
                    **provider_timings)
            measurement_recorded = True
            await ws.send_json({'type': 'completed', 'session_metrics': {
                'audio_received_ms': round(audio_bytes / 32, 1),
                'estimated_asr_cost_usd': (None if asr_rate is None else
                    round((audio_bytes / 32 / 3_600_000) * asr_rate, 8)),
                'cost_scope': 'asr_only_configured_rate',
            }})
            await ws.close()
        except asyncio.CancelledError:
            if 'started' in locals() and not measurement_recorded:
                live_metrics.record(outcome='cancelled', audio_ms=audio_bytes / 32,
                    first_alert_proxy_ms=first_alert_proxy_ms,
                    risk_engine_ms=max(risk_engine_samples) if risk_engine_samples else None,
                    **provider_timings)
            try:
                await ws.send_json({'error': 'processing_stopped'})
                await ws.close(code=1000)
            except (WebSocketDisconnect, RuntimeError):
                pass
        except WebSocketDisconnect:
            if 'started' in locals() and not measurement_recorded:
                live_metrics.record(outcome='disconnected', audio_ms=audio_bytes / 32,
                    first_alert_proxy_ms=first_alert_proxy_ms,
                    risk_engine_ms=max(risk_engine_samples) if risk_engine_samples else None,
                    **provider_timings)
        except Exception:
            if 'started' in locals() and not measurement_recorded:
                live_metrics.record(completed=False, audio_ms=audio_bytes / 32,
                    first_alert_proxy_ms=first_alert_proxy_ms,
                    risk_engine_ms=max(risk_engine_samples) if risk_engine_samples else None,
                    **provider_timings)
            try:
                await ws.send_json({'error': 'audio_stream_failed',
                                    'protected_actions_allowed': False})
                await ws.close(code=1011)
            except (WebSocketDisconnect, RuntimeError):
                pass

        finally:
            if 'provider_task' in locals() and provider_task is not None:
                active_audio.discard(provider_task)
                if not provider_task.done():
                    provider_task.cancel()
                await asyncio.gather(provider_task, return_exceptions=True)

    @app.post('/api/protected-action', dependencies=[Depends(participant)])
    def protected_action(body: Operation):
        # This direct path has no authorization capability. The only execution
        # path remains verified reviewer completion under trusted orchestration.
        log_security('gateway_refused', error_code='POLICY_PROOF_REQUIRED',
                     **workflow.telemetry_context())
        raise HTTPException(403, detail={
            'code': 'POLICY_PROOF_REQUIRED',
            'message': 'Direct speech or participant input cannot authorize an action.',
            'real_action_executed': False,
        })

    @app.post('/api/request', dependencies=[Depends(participant)])
    async def request_confirmation(body: ContactOperation):
        if any(not task.done() for task in active_audio):
            raise HTTPException(409, 'finish audio before requesting confirmation')
        try:
            with trace_step('challenge_request', **workflow.telemetry_context()):
                result = workflow.request_confirmation(**body.model_dump())
            log_security('challenge_created', **workflow.telemetry_context())
            return result
        except ChallengeRateLimited as error:
            log_security('challenge_rate_limited', error_code='RATE_LIMITED',
                         **workflow.telemetry_context())
            raise HTTPException(429, 'challenge issuance rate exceeded',
                                headers={'Retry-After': str(error.retry_after)}) from None
        except ValueError:
            log_security('challenge_refused', error_code='POLICY_PREVENTS_CONFIRMATION',
                         **workflow.telemetry_context())
            raise HTTPException(409, 'policy prevents confirmation') from None

    @app.get('/api/contacts', dependencies=[Depends(participant)])
    def contacts():
        return {'identities': workflow.contact_identities(),
                'enrollment': 'trusted_startup_not_verified_human_identity'}

    @app.get('/api/review/pending')
    def pending(principal=Depends(reviewer)):
        bundle = workflow.pending_confirmation()
        if bundle is not None and principal is not None:
            if bundle['request']['reviewer'] != principal:
                return None
        return bundle

    @app.post('/api/review/decision')
    async def decision(body: SubmittedDecision, principal=Depends(reviewer)):
        if principal is not None and body.decision.request.reviewer != principal:
            log_security('review_decision_refused', error_code='WRONG_REVIEWER',
                         **workflow.telemetry_context())
            raise HTTPException(409, 'request belongs to another saved contact')
        if any(not task.done() for task in active_audio):
            raise HTTPException(409, 'finish audio before deciding')
        try:
            with trace_step('reviewer_decision', **workflow.telemetry_context()):
                result = workflow.complete(body.decision, challenge_response=body.challenge_response)
            if hasattr(app.state, 'device_fusion'):
                app.state.device_fusion.record_completion(body.decision, result)
            log_security('gateway_result', outcome_status=result.get('status'),
                         **workflow.telemetry_context())
            return result
        except ValueError:
            log_security('review_decision_refused', error_code='INVALID_OR_STALE_CONFIRMATION',
                         **workflow.telemetry_context())
            raise HTTPException(409, 'confirmation invalid, stale, expired or already used') from None

    if device_inbox is not None:
        from .device_fusion import attach_device_fusion
        attach_device_fusion(app, workflow, participant_token, device_inbox, fusion_state,
                             audio_active=lambda: any(not task.done() for task in active_audio))

    return app


def create_reviewer_app(signing_key, reviewer_token, fetch_pending, submit_decision, *,
                        origin='http://127.0.0.1:8767', expected_reviewer=None):
    if not reviewer_token:
        raise ValueError('reviewer credential required')
    app = guarded_app(origin, 'reviewer.html')
    reviewer = bearer(reviewer_token)

    def fetch_verified():
        try:
            bundle = fetch_pending()
        except Exception:
            raise HTTPException(503, 'confirmation channel unavailable') from None
        try:
            if bundle is None:
                return None
            request = ConfirmationRequest.model_validate(bundle['request'])
            if expected_reviewer is not None and request.reviewer != expected_reviewer:
                raise ValueError('request addressed to another saved contact')
            operation = dict(bundle['operation'])
            if operation.pop('currency') != 'USD':
                raise ValueError('unsupported currency')
            operation = {**ContactOperation.model_validate(operation).model_dump(exclude_none=True),
                         'currency': 'USD'}
            if operation.get('claimed_identity') != request.claimed_identity:
                raise ValueError('claimed identity commitment mismatch')
            digest = hashlib.sha256(json.dumps(operation, sort_keys=True).encode()).hexdigest()
            if not hmac.compare_digest(digest, request.resource):
                raise ValueError('operation commitment mismatch')
            return {'request': request, 'operation': operation}
        except (ValueError, KeyError, TypeError):
            # No upstream exception, transcript or credential in a client error.
            raise HTTPException(409, 'confirmation content invalid') from None

    @app.get('/api/pending', dependencies=[Depends(reviewer)])
    def pending():
        return fetch_verified()

    @app.post('/api/decide', dependencies=[Depends(reviewer)])
    def decide(body: Approval):
        bundle = fetch_verified()
        if bundle is None or bundle['request'].request_id != body.request_id:
            raise HTTPException(409, 'reviewed request is no longer current')
        request = bundle['request']
        signed = ReviewerDecision(request=request, approved=body.approved,
            signature=signing_key.sign(decision_bytes(request, body.approved)).hex())
        try:
            return submit_decision(SubmittedDecision(
                decision=signed, challenge_response=body.challenge_response))
        except ValueError:
            raise HTTPException(409, 'confirmation invalid, stale, expired or already used') from None
        except Exception:
            # A lost response may follow a completed simulated action. Never
            # retry or claim success; the broker consumes confirmation once.
            raise HTTPException(503, 'decision not confirmed; do not retry automatically') from None

    return app
