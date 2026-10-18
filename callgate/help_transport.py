"""Minimal public help surface. No payment service is mounted or proxied."""
import asyncio
from contextlib import asynccontextmanager
import hmac
import sqlite3
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .help_requests import HelpStore, HelpPrincipal, HelpNotFound

ASSETS=Path(__file__).with_name('demo')


class HelpAction(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    action_id: str=Field(min_length=1,max_length=128,pattern=r'^[A-Za-z0-9_.:-]+$')


class HelpResponse(HelpAction):
    response: Literal['accept','unable']


def create_help_app(store:HelpStore, credentials:dict[str,HelpPrincipal]):
    if (not credentials or any(not isinstance(token,str) or len(token)<32 or not token.isascii()
        or any(c.isspace() for c in token) for token in credentials)
        or any(p.role not in {'owner','contact','dashboard'} or not p.actor_id or not p.device_ids for p in credentials.values())):
        raise ValueError('distinct scoped help credentials required')
    credentials=dict(credentials)

    @asynccontextmanager
    async def lifespan(app):
        async def ingest():
            while True:
                try:
                    await asyncio.to_thread(store.sync)
                    app.state.inbox_available=True
                except Exception:
                    # No exception payloads, source records or credentials in logs.
                    app.state.inbox_available=False
                await asyncio.sleep(1)
        task=asyncio.create_task(ingest())
        try:
            yield
        finally:
            task.cancel()
            await asyncio.gather(task,return_exceptions=True)

    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    app.state.inbox_available=True

    def principal(request:Request):
        supplied=request.headers.get('authorization','').encode()
        for token, identity in credentials.items():
            if hmac.compare_digest(supplied,('Bearer '+token).encode()):
                return identity
        raise HTTPException(401,'A valid help role access code is required.',headers={'WWW-Authenticate':'Bearer'})

    @app.exception_handler(RequestValidationError)
    async def invalid(request,exc):
        return JSONResponse({'detail':'Invalid help action format.'},status_code=422)

    @app.middleware('http')
    async def boundary(request,call_next):
        origin=request.headers.get('origin')
        if origin and (urlsplit(origin).netloc!=request.headers.get('host') or urlsplit(origin).scheme not in {'http','https'}):
            return JSONResponse({'detail':'Cross-origin access is not allowed.'},status_code=403)
        if request.method=='POST':
            chunks=[];size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>2048:
                    return JSONResponse({'detail':'Help action body too large.'},status_code=413)
                chunks.append(chunk)
            request._body=b''.join(chunks)
        response=await call_next(request)
        response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer',
            'X-Content-Type-Options':'nosniff',
            'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"})
        return response

    @app.exception_handler(HelpNotFound)
    async def not_found(request,error):
        return JSONResponse({'detail':'Help request not found.'},status_code=404)

    @app.exception_handler(sqlite3.Error)
    async def storage_unavailable(request,error):
        return JSONResponse({'detail':'Help storage is temporarily unavailable. No action is confirmed.'},status_code=503)

    @app.exception_handler(PermissionError)
    async def forbidden(request,error):
        return JSONResponse({'detail':'This role cannot perform that action.'},status_code=403)

    @app.get('/')
    def dashboard():
        return FileResponse(ASSETS/'help-dashboard.html')

    @app.get('/contact')
    def contact_page():
        return FileResponse(ASSETS/'help-contact.html')

    @app.get('/help.js')
    def javascript():
        return FileResponse(ASSETS/'help.js',media_type='text/javascript')

    @app.get('/help.css')
    def help_stylesheet():
        return FileResponse(ASSETS/'help.css',media_type='text/css')

    @app.get('/review-ui.css')
    def stylesheet():
        return FileResponse(ASSETS/'review-ui.css',media_type='text/css')

    @app.get('/api/help-requests')
    def requests(p=Depends(principal)):
        return {'role':p.role,'actor_id':p.actor_id,'requests':store.list(p),
                'inbox_last_read_at':store.last_sync,'notification_delivery_confirmed':False}

    @app.get('/api/help-requests/{event_id}')
    def status(event_id:str,p=Depends(principal)):
        return store.get(event_id,p)

    @app.post('/api/help-requests/{event_id}/responses')
    def respond(event_id:str,body:HelpResponse,p=Depends(principal)):
        code,result=store.act(event_id,body.action_id,p,body.response)
        return JSONResponse(result,status_code=code)

    @app.post('/api/help-requests/{event_id}/cancel')
    def cancel(event_id:str,body:HelpAction,p=Depends(principal)):
        code,result=store.act(event_id,body.action_id,p,'cancel')
        return JSONResponse(result,status_code=code)

    return app
