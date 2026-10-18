"""Real-browser UI acceptance using explicit synthetic fixtures only.

Serves the actual running HTML/CSS/JS, intercepts EVERY /api/ request, and never
loads real credentials or writes events to the live service. Playwright is an
optional local test dependency, not a runtime dependency.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect


def fixture(state='waiting'):
    stamp=time.time()
    iso=lambda seconds: datetime.fromtimestamp(stamp+seconds,timezone.utc).isoformat()
    request=dict(request_id='synthetic-preview-request',session_id='synthetic-preview-session',
                 reviewer='local-reviewer',claimed_identity='saved-family',expires_at=int(stamp)+110)
    operation=dict(destination='campus-repair-demo',amount_cents=8000,currency='USD',claimed_identity='saved-family')
    binding=dict(session_id=request['session_id'],device_id='nano-01',destination=operation['destination'],amount_cents=8000,claimed_identity='saved-family')
    event=dict(event_id='ui-preview-local-test-001',device_id='nano-01',event_type='verify_request',received_at=iso(-30))
    timeline=[dict(stage='event_received',at=iso(-30)),dict(stage='verification_request_created',at=iso(-20),request_id=request['request_id'])]
    row=dict(event=event,status='request_created',request=request,binding=binding,timeline=timeline,out_of_band_challenge='123456')
    context=dict(session_id=request['session_id'],risk_state='CHALLENGED',processing_allowed=True,processing_consent='GRANTED',pending=True,authorization_denied=False,outcome=None)
    if state in {'success','denied'}:
        result=dict(status='simulated_action_completed' if state=='success' else 'reviewer_denied',real_action_executed=False)
        timeline.extend([dict(stage='contact_responded',at=iso(-8),approved=state=='success'),dict(stage='simulated_operation_result',at=iso(-8),result=result)])
        row.update(status='completed',outcome=result);row.pop('out_of_band_challenge');context.update(pending=False,outcome=result)
    if state=='expired':
        request['expires_at']=int(stamp)-1;row['status']='no_longer_pending';context.update(pending=False,authorization_denied=True)
    if state=='ready':
        row=dict(event=event,status='intent_received',reason=None,timeline=[timeline[0]]);context['pending']=False
    evidence=dict(contributions=[dict(kind='money'),dict(kind='urgency')],graph=dict(nodes=[dict(type='segment')]))
    return dict(fusion=dict(context=context,contacts=['saved-family'],binding=binding,events=[row]),evidence=evidence,pending=dict(request=request,operation=operation))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8781')
    parser.add_argument('--reviewer-url',default='http://127.0.0.1:8782')
    parser.add_argument('--output-dir',type=Path,default=Path('.test-tmp/reachguard-ui'))
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    checks=[];screenshots=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport=dict(width=1440,height=1150),reduced_motion='reduce')
        page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
        controller=fixture();calls=[];mode={'fail':False,'review_status':200}
        def intercept(route):
            path=urlsplit(route.request.url).path;method=route.request.method
            calls.append((path,method))
            if mode['fail']:route.abort();return
            if path=='/api/fusion':body=controller['fusion']
            elif path=='/api/evidence':body=controller['evidence']
            elif path=='/api/status':body=controller['fusion']['context']
            elif path=='/api/contacts':body={'identities':['saved-family']}
            elif path=='/api/processing-consent':
                controller['fusion']['context']['processing_allowed']=route.request.post_data_json['granted'];body={}
            elif path=='/api/transcript':body={'state':'CHALLENGED','score':30}
            elif path=='/api/pending':
                route.fulfill(status=mode['review_status'],body=json.dumps(controller.get('pending')),content_type='application/json');return
            elif path=='/api/decide':
                submitted=route.request.post_data_json
                assert submitted['request_id']=='synthetic-preview-request'
                assert submitted['challenge_response']==('123456' if submitted['approved'] else None)
                body=dict(status='simulated_action_completed' if submitted['approved'] else 'reviewer_denied',real_action_executed=False)
            elif path=='/api/fusion/process':
                assert route.request.post_data_json=={'event_id':'ui-preview-local-test-001'}
                body={'status':'request_created'}
            else:body={}
            route.fulfill(status=200,json=body)
        page.route('**/api/**',intercept)
        def banner():
            page.locator('.eyebrow').first.evaluate("el => el.textContent = 'UI PREVIEW · SYNTHETIC LOCAL TEST'")
        def shot(name):
            banner();path=args.output_dir/(name+'.png');page.screenshot(path=str(path),full_page=True);screenshots.append(str(path))
        def connect_operator(state):
            controller.clear();controller.update(fixture(state));mode.update(fail=False,review_status=200)
            page.goto(args.base_url+'/fusion');page.locator('#token').fill('ui-preview-operator');page.locator('#connect').click()
            expect(page.locator('#connection')).to_have_text('Workspace synced')
        def no_overflow():
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
        connect_operator('waiting')
        expect(page.locator('#challenge-panel')).to_be_visible();expect(page.locator('#challenge-code')).to_have_text('123456')
        assert not any(path=='/api/fusion/process' for path,_ in calls)
        shot('operator-waiting-desktop');no_overflow();checks.append('waiting state / no automatic verification')
        selection=page.locator('#event-select').input_value()
        newcomer=deepcopy(controller['fusion']['events'][0]);newcomer['event']['event_id']='ui-preview-new-arrival';newcomer['status']='intent_received'
        controller['fusion']['events'].insert(0,newcomer);page.wait_for_timeout(2200)
        assert page.locator('#event-select').input_value()==selection
        page.locator('#event-select').focus();assert page.locator('#event-select').evaluate("el => getComputedStyle(el).outlineStyle !== 'none'")
        checks.append('new arrival keeps selection / keyboard focus visible')
        mode['fail']=True;page.wait_for_timeout(2300);expect(page.locator('#challenge-panel')).to_be_hidden();expect(page.locator('#request-verification')).to_be_disabled();checks.append('network failure hides challenge and disables action')
        for state,heading in [('success','Simulated action completed'),('denied','Contact denied this request'),('expired','Verification expired')]:
            connect_operator(state);expect(page.locator('#verification-status')).to_have_text(heading);expect(page.locator('#challenge-panel')).to_be_hidden()
            shot('operator-'+state+'-desktop');no_overflow()
        connect_operator('ready');expect(page.locator('#request-verification')).to_be_enabled();page.locator('#request-verification').click()
        assert sum(path=='/api/fusion/process' for path,_ in calls)==1;checks.append('verification requires an explicit click with event ID only')
        connect_operator('waiting');page.set_viewport_size(dict(width=390,height=844));shot('operator-waiting-mobile');no_overflow()
        checks.append('operator mobile layout / no horizontal overflow')
        # Force browser-clock expiry while the fixture still claims backend pending.
        controller['fusion']['events'][0]['request']['expires_at']=int(time.time())+2
        page.wait_for_timeout(4500);expect(page.locator('#challenge-panel')).to_be_hidden();checks.append('countdown hides expired code without waiting for a response')
        def reviewer(state='waiting',status=200):
            controller.clear();controller.update(fixture(state));mode.update(fail=False,review_status=status)
            page.goto(args.reviewer_url+'/#token=ui-preview-reviewer');page.locator('#refresh').click()
        reviewer();expect(page.locator('#approve')).to_be_enabled();expect(page.locator('#review-amount')).to_have_text('$80.00')
        shot('reviewer-waiting-mobile');no_overflow()
        for button in ['#approve','#deny','#refresh']:
            box=page.locator(button).bounding_box();assert box['height']>=44
        page.locator('#challenge-response').fill('123456');page.locator('#approve').click();expect(page.locator('#review-heading')).to_have_text('Simulated action completed');expect(page.locator('#approve')).to_be_disabled();assert page.locator('#challenge-response').input_value()==''
        shot('reviewer-success-mobile');checks.append('reviewer approval preserves request ID and challenge protocol')
        reviewer();page.locator('#deny').click();expect(page.locator('#review-heading')).to_have_text('Contact denied this request');shot('reviewer-denied-mobile');checks.append('denial requires no approval challenge')
        reviewer('expired');expect(page.locator('#review-heading')).to_have_text('Verification expired');expect(page.locator('#approve')).to_be_disabled();shot('reviewer-expired-mobile')
        reviewer(status=401);expect(page.locator('#review-heading')).to_have_text('Contact access required');checks.append('invalid access is separate from an empty request')
        mode.update(fail=False,review_status=200);controller['pending']=None;page.locator('#refresh').click();expect(page.locator('#review-heading')).to_have_text('No request waiting')
        mode['fail']=True;page.locator('#refresh').click();expect(page.locator('#review-heading')).to_have_text('Connection unavailable');checks.append('empty / network error / expiry have distinct states')
        mode.update(fail=False,review_status=200);controller.clear();controller.update(fixture('ready'))
        controller['fusion']['context']['processing_allowed']=False
        page.set_viewport_size(dict(width=1440,height=1000));page.goto(args.base_url+'/#token=ui-preview-participant')
        expect(page.locator('#start-audio')).to_be_disabled();expect(page.locator('#ingest')).to_be_disabled()
        page.locator('#consent').click();expect(page.locator('#ingest')).to_be_enabled();page.locator('#ingest').click()
        expect(page.locator('#risk')).to_contain_text('Verify before acting')
        expect(page.locator('#request')).to_be_disabled();page.locator('#load-contacts').click();expect(page.locator('#request')).to_be_enabled()
        shot('participant-text-desktop');no_overflow();checks.append('English request view keeps consent and contact prerequisites')
        assert not errors, errors
        browser.close()
    report={'source':'synthetic local UI fixtures; all /api calls intercepted; no live credentials or event writes',
            'checks':checks,'screenshots':screenshots,'browser_errors':errors,'passed':True}
    (args.output_dir/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'passed':True,'checks':len(checks),'screenshots':len(screenshots),'report':str(args.output_dir/'report.json')}))


if __name__=='__main__':main()
