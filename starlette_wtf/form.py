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
import asyncio
import inspect

from starlette.datastructures import ImmutableMultiDict
from starlette.requests import Request as StarletteRequest
from wtforms import Form, ValidationError
from wtforms.meta import DefaultMeta

from starlette_wtf.util import get_formdata


__all__ = ['StarletteForm']


SUBMIT_METHODS = set(('POST', 'PUT', 'PATCH', 'DELETE'))
_Auto = object()


class StarletteForm(Form):
    """Starlette-specific subclass of WTForms :class:`~wtforms.form.Form`.

    To populate from submitted formdata use the ```.from_submit()``` class
    method to initialize the instance.
    """

    def __init__(self, request: StarletteRequest, *args, **kwargs):
        """Initialize StarletteForm instance.

        Args:
          request (:class:`starlette.requests.Request`): The request instance.
          *args: Variable length argument list for :class:`starlette.requests
              .Request`
          **kwargs: Arbitrary keyword arguments for :class:`starlette.requests
              .Request`

        """
        # cache request
        self._request = request
        
        # for WTForms CSRF handling
        if hasattr(request.state, 'csrf_config'):
            config = request.state.csrf_config
            kwargs['meta'] = {
                'csrf': config['enabled'],
                'csrf_secret': str(config['csrf_secret']).encode('utf-8'),
                'csrf_class': config['csrf_class'],
                'csrf_context': request,
                'csrf_field_name': config['csrf_field_name'],
                'csrf_time_limit': config['csrf_time_limit']
            }

        super().__init__(*args, **kwargs)

        
    @classmethod
    async def from_formdata(cls, request: StarletteRequest, formdata=_Auto,
                            **kwargs):
        """Method to support initializing class from submitted formdata. If
        request is a POST, PUT, PATCH or DELETE, form will be initialized using
        formdata. Otherwise, it will be initialized using defaults.

        Args:
          request (:class:`starlette.requests.Request`): The request instance.
          formdata (ImmutableMultiDict, optional): If present, this will be
              used to initialize the form fields.

        Returns:
          :class:`starlette_wtf.form.StarletteForm`: A new form instance.

        """
        if formdata is _Auto:
            if request.method in SUBMIT_METHODS:
                # get formdata from request.form() or request.json()
                formdata = await get_formdata(request)
            else:
                formdata = None
            
        # return new instance
        return cls(request, formdata=formdata, **kwargs)

    
    async def _validate_async(self, validator, field):
        """Execute async validator
        """
        try:
            await validator(self, field)
        except ValidationError as e:
            field.errors.append(e.args[0])
            return False
        return True

    
    async def validate(self, extra_validators=None):
        """Overload :meth:`validate` to handle custom async validators
        """
        if extra_validators is not None:
            extra = extra_validators.copy()
        else:
            extra = {}

        async_validators = {}
            
        # use extra validators to check for StopValidation errors
        completed = []
        def record_status(form, field):
            completed.append(field.name)
        
        for name, field in self._fields.items():
            func = getattr(self.__class__, f"async_validate_{name}", None)
            if func:
                async_validators[name] = (func, field)
                extra.setdefault(name, []).append(record_status)
                
        # execute non-async validators
        success = super().validate(extra_validators=extra)

        # execute async validators
        tasks = [self._validate_async(*async_validators[name]) for name in \
                 completed]
        async_results = await asyncio.gather(*tasks)

        # check results
        if False in async_results:
            success = False
                         
        return success
    
    
    def is_submitted(self):
        """Consider the form submitted if there is an active request and
        the method is ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
        """
        return self._request.method in SUBMIT_METHODS
    
        
    async def validate_on_submit(self, extra_validators=None):
        """Call :meth:`validate` only if the form is submitted.
        This is a shortcut for ``form.is_submitted() and form.validate()``.
        """
        return self.is_submitted() and \
            await self.validate(extra_validators=extra_validators)
