"""Starlette helpers for WTForms

Contains code with and without modification from Flask-WTF:

Copyright (c) 2010 by Dan Jacob.
Copyright (c) 2013 by Hsiaoming Yang.

Some rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above
  copyright notice, this list of conditions and the following
  disclaimer in the documentation and/or other materials provided
  with the distribution.

* The names of the contributors may not be used to endorse or
  promote products derived from this software without specific
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from typing import List, Optional, ByteString
import functools
from urllib.parse import urlparse

from starlette.applications import Starlette as StarletteApplication
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from wtforms import ValidationError
from wtforms.csrf.core import CSRF

from starlette_wtf.form import SUBMIT_METHODS, get_formdata
from starlette_wtf.util import generate_csrf, validate_csrf


__all__ = ['CSRFProtectMiddleware', 'csrf_protect', 'csrf_token', 'CSRFError']


class _StarletteFormCSRF(CSRF):
    def setup_form(self, form):
        self.form_meta = form.meta
        return super(_StarletteFormCSRF, self).setup_form(form)

    
    def generate_csrf_token(self, csrf_token_field):
        meta = self.form_meta
        return generate_csrf(
            request=meta.csrf_context,
            secret_key=meta.csrf_secret,
            field_name=meta.csrf_field_name)

    
    def validate_csrf_token(self, form, field):
        meta = self.form_meta

        if hasattr(meta.csrf_context.state, 'csrf_valid'):
            # already validated by CSRFProtectMiddleware
            return

        validate_csrf(
            request=meta.csrf_context,
            data=field.data,
            secret_key=meta.csrf_secret,
            field_name=meta.csrf_field_name,
            time_limit=meta.csrf_time_limit)


DEFAULT_ENABLED = True
DEFAULT_CSRF_SECRET = None
DEFAULT_CSRF_FIELD_NAME = 'csrf_token'
DEFAULT_CSRF_TIME_LIMIT = 3600
DEFAULT_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']
DEFAULT_CSRF_SSL_STRICT = True


class CSRFProtectMiddleware(BaseHTTPMiddleware):
    def __init__(self,
                 app: StarletteApplication,
                 enabled: bool=DEFAULT_ENABLED,
                 csrf_secret: Optional[ByteString]=DEFAULT_CSRF_SECRET,
                 csrf_field_name: str=DEFAULT_CSRF_FIELD_NAME,
                 csrf_time_limit: int=DEFAULT_CSRF_TIME_LIMIT,
                 csrf_headers: List[str]=DEFAULT_CSRF_HEADERS,
                 csrf_ssl_strict: bool=DEFAULT_CSRF_SSL_STRICT):
        """ASGI Middleware needed by Starlette-WTF to enable CSRF protection.
        
        Args:
          app (:class:`starlette.applications.Starlette`): The application
              instance.
          enabled (bool, optional): Defaults to True.
          csrf_secret (str): CSRF secret key
          csrf_field_name (str): The CSRF token field name. Defaults to
              "csrf_token".
          csrf_time_limit (int): The CSRF token time limit in seconds. Defaults
              to 3600.
          csrf_headers (list of str): CSRF HTTP header field names. Defaults to
              ["X-CSRFToken", "X-CSRF-Token"]
          csrf_ssl_strict (bool): If enabled, ensures same origin policy on
              https requests. Defaults to true.

        """
        if enabled and not csrf_secret:
            raise RuntimeError('`csrf_secret` is required')

        self.csrf_config = {
            'enabled': enabled,
            'csrf_secret': csrf_secret,
            'csrf_class': _StarletteFormCSRF,
            'csrf_field_name': csrf_field_name,
            'csrf_time_limit': csrf_time_limit,
            'csrf_headers': csrf_headers,
            'csrf_ssl_strict': csrf_ssl_strict
        }
        
        super().__init__(app)

        
    async def dispatch(self, request, call_next):
        """Add CSRF config to request state
        """
        request.state.csrf_config = self.csrf_config
        return await call_next(request)


class CSRFError(HTTPException):
    """HTTPException class for CSRF validation errors. Returns 403 Forbidden.
    """
    def __init__(self, detail=None):
        super().__init__(status_code=403, detail=detail)


def csrf_protect(func):
    """Returns decorator that performs CSRF validation before calling 
    endpoint function
    """
    @functools.wraps(func)
    async def endpoint_wrapper(request, *args, **kwargs):
        if not request.method in SUBMIT_METHODS:
            return await func(request, *args, **kwargs)
        
        # get token
        signed_token = await get_csrf_token(request)

        config = request.state.csrf_config
        
        # validate token
        try:
            validate_csrf(request,
                          signed_token,
                          secret_key=config['csrf_secret'],
                          field_name=config['csrf_field_name'],
                          time_limit=config['csrf_time_limit'])
        except ValidationError as e:
            raise CSRFError(e.args[0])

        # strict ssl check
        if request.url.scheme == 'https' and config['csrf_ssl_strict']:
            referrer = request.headers.get('REFERER')

            if not referrer:
                raise CSRFError('The referrer header is missing.')

            if not same_origin(urlparse(referrer), request.url):
                raise CSRFError('The referrer does not match the host.')
        
        # mark request as valid
        request.state.csrf_valid = True

        # pass on request
        return await func(request, *args, **kwargs)

    return endpoint_wrapper


def csrf_token(request):
    """Return CSRF token

    Args:
      request (:class:`starlette.requests.Request`): The request instance.

    Returns:
      str: The signed token

    """
    csrf_config = request.state.csrf_config
    
    return generate_csrf(request,
                         secret_key=csrf_config['csrf_secret'],
                         field_name=csrf_config['csrf_field_name'])


async def get_csrf_token(request):
    csrf_config = request.state.csrf_config
    
    formdata = await get_formdata(request)
    
    field_name = csrf_config['csrf_field_name']
    base_token = formdata.get(field_name)

    if base_token:
        return base_token
    
    # find the token in the headers
    for header_name in csrf_config['csrf_headers']:
        csrf_token = request.headers.get(header_name)
        if csrf_token:
            return csrf_token
        
    return None


def same_origin(url1, url2):
    return (
        url1.scheme == url2.scheme
        and url1.hostname == url2.hostname
        and url1.port == url2.port
    )
