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
import hashlib
import hmac
import os

from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer
from starlette.datastructures import ImmutableMultiDict, Secret
from starlette.requests import Request as StarletteRequest
from wtforms import ValidationError


async def get_formdata(request: StarletteRequest):
    """Return formdata from request. Handles multi-dict and json content types.

    Args:
      request (:class:`starlette.requests.Request`): The request instance.

    Returns:
      formdata (ImmutableMultiDict): The form/json data from the request.

    """
    if request.headers.get('content-type') == 'application/json':
        formdata = ImmutableMultiDict(await request.json())
    else:
        formdata = await request.form()

    return formdata


def generate_csrf(request: StarletteRequest,
                  secret_key: str,
                  field_name: str):
    """Generate a new token, store it in the session and return a time-signed
    token. If a token is already present in the session, it will be used to
    generate a new time signed token. The time-signed token is cached per
    request so multiple calls to this function will return the same time-signed
    token.

    Args:
      request (:class:`starlette.requests.Request`): The request instance.
      secret_key (str): The signing key.
      field_name (str): Where the token is stored in the session.

    Returns:
      str: The time-signed token

    """
    if not hasattr(request.state, field_name):
        # handle Secret instances
        if isinstance(secret_key, Secret):
            secret_key = str(secret_key)
        
        s = URLSafeTimedSerializer(secret_key, salt='wtf-csrf-token')

        session = request.session

        # get/set token in session
        if field_name not in session:
            session[field_name] = hashlib.sha1(os.urandom(64)).hexdigest()

        try:
            token = s.dumps(session[field_name])
        except TypeError:
            session[field_name] = hashlib.sha1(os.urandom(64)).hexdigest()
            token = s.dumps(session[field_name])

        setattr(request.state, field_name, token)

    return getattr(request.state, field_name)


def validate_csrf(request: StarletteRequest,
                  data: str,
                  secret_key: str,
                  field_name: str,
                  time_limit: int=None):
    """Check if the given data is a valid CSRF token. This compares the given
    signed token to the one stored in the session.

    Args:
      request (:class:`starlette.requests.Request`): The request instance.
      data (str): The time-signed CSRF token to be checked.
      secret_key (str): The signing key Used to sign the token.
      field_name (str): Where token is stored in session.
      time_limit (int): Number of seconds that the token is valid. Defaults to
          None.

    Returns:
      None: Completes successfully otherwise raises an error.

    Raises:
      ValidationError: If token failes validation. Contains the reason that
          validation failed.

    """
    if not data:
        raise ValidationError('The CSRF token is missing.')

    if field_name not in request.session:
        raise ValidationError('The CSRF session token is missing.')

    # handle Secret instances
    if isinstance(secret_key, Secret):
        secret_key = str(secret_key)
    
    s = URLSafeTimedSerializer(secret_key, salt='wtf-csrf-token')
    
    try:
        token = s.loads(data, max_age=time_limit)
    except SignatureExpired:
        raise ValidationError('The CSRF token has expired.')
    except BadData:
        raise ValidationError('The CSRF token is invalid.')

    # do safe string comparison
    if not hmac.compare_digest(request.session[field_name], token):
        raise ValidationError('The CSRF tokens do not match.')
