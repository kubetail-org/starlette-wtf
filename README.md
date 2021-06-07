# Starlette-WTF

Starlette-WTF is a simple tool for integrating [Starlette](https://www.starlette.io/) and [WTForms](https://wtforms.readthedocs.io/en/stable/). It is modeled on the excellent [Flask-WTF](https://flask-wtf.readthedocs.io) library.

## Table of Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Creating Forms](#creating-forms)
  * [The StarletteForm Class](#the-starletteform-class)
  * [Validation](#validation)
  * [Async Custom Validators](#async-custom-validators)
- [CSRF Protection](#csrf-protection)
  * [Setup](#setup)
  * [Protect Views](#protect-views)
  * [HTML Forms](#html-forms)
  * [JavaScript Requests](#javascript-requests)
  * [Disable in Unit Tests](#disable-in-unit-tests)
  * [Configuration](#configuration)
- [Development](#development)
  * [Get the code](#get-the-code)
  * [Run unit tests](#run-unit-tests)

## Installation

Installing Starlette-WTF is simple with [pip](https://pip.pypa.io/en/stable/):

```bash
$ pip install starlette-wtf
```

## Quickstart

The following code implements a simple form handler with CSRF protection. The form has a required string field and validation errors are handled by the html template. Note that CSRF protection requires `SessionMiddleware`, `CSRFProtectMiddleware`, `@csrf_protect` and the `csrf_token` field to be added to the HTML form.

First, install the dependencies for this quickstart:

```bash
$ pip install starlette starlette-wtf jinja2 uvicorn 
```

Next, create a Python file (app.py) with the following code:

```python
from jinja2 import Template
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse, HTMLResponse
from starlette_wtf import StarletteForm, CSRFProtectMiddleware, csrf_protect
from wtforms import StringField
from wtforms.validators	import DataRequired


class MyForm(StarletteForm):
    name = StringField('name', validators=[DataRequired()])


template = Template('''
<html>
  <body>
    <form method="post" novalidate>
      {{ form.csrf_token }}
      <div>
        {{ form.name(placeholder='Name') }}
        {% if form.name.errors -%}
        <span>{{ form.name.errors[0] }}</span>
        {%- endif %}
      </div>
      <button type="submit">Submit</button>
    </form>
  </body>
</html>
''')


app = Starlette(middleware=[
    Middleware(SessionMiddleware, secret_key='***REPLACEME1***'),
    Middleware(CSRFProtectMiddleware, csrf_secret='***REPLACEME2***')
])


@app.route('/', methods=['GET', 'POST'])
@csrf_protect
async def index(request):
    """GET|POST /: form handler
    """
    form = await MyForm.from_formdata(request)
    
    if await form.validate_on_submit():
        return PlainTextResponse('SUCCESS')

    html = template.render(form=form)
    return HTMLResponse(html)
```
    
Finally, run the app using the following command:
    
```bash
$ uvicorn app:app
```

## Creating Forms

### The StarletteForm Class

Starlette-WTF provides a form class that makes it easy to add form validation and CSRF protection to Starlette apps. To make a form, subclass the `StarletteForm` class and use [WTForms](https://wtforms.readthedocs.io/) fields, validators and widgets to define the inputs. The `StarletteForm` class inherits from the WTForms `Form` class so you can use WTForms features and methods to add more advanced functionality to your app:

```python
from starlette_wtf import StarletteForm
from wtforms import TextField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo
from wtforms.widgets import PasswordInput


class CreateAccountForm(StarletteForm):
    email = TextField(
        'Email address',
        validators=[
            DataRequired('Please enter your email address'),
            Email()
        ]
    )

    password = PasswordField(
        'Password',
        widget=PasswordInput(hide_value=False),
        validators=[
            DataRequired('Please enter your password'),
            EqualTo('password_confirm', message='Passwords must match')
        ]
    )

    password_confirm = PasswordField(
        'Confirm Password',
        widget=PasswordInput(hide_value=False),
        validators=[
            DataRequired('Please confirm your password')
        ]
    )
```

Often you will want to initialize form objects using default values on GET requests and from submitted formdata on POST requests. To make this easier you can use the `.from_formdata()` async class method which does this for you automatically:

```python
@app.route('/create-account', methods=['GET', 'POST'])
async def create_account(request):
    """GET|POST /create-account: Create account form handler
    """
    form = await CreateAccountForm.from_formdata(request)
    return PlainTextResponse()
```

### Validation

The `StarletteForm` class has a useful `.validate_on_submit()` method that performs input validation for POST, PUT, PATCH and DELETE requests and returns a boolean indicating whether or not there were any errors. After validation, errors are available via the `.errors` attribute attached to each input field instance. Note that validation is asynchronous to handle async field validators (see below):

```python
from jinja2 import Template
from starlette.applications import Starlette
from starlette.responses import (PlainTextResponse, RedirectResponse,
                                 HTMLResponse)


template = Template('''
<html>
  <body>
    <h1>Create Account</h1>
    <form method="post" novalidate>
      <div>
        {{ form.email(placeholder='Email address',
                      autofocus='true',
                      type='email',
                      spellcheck='false') }}
        {% if form.email.errors -%}
        <span>{{ form.email.errors[0] }}</span>
        {%- endif %}
      </div>
      <div>
        {{ form.password(placeholder="Password") }}
        {% if form.password.errors -%}
        <span>{{ form.password.errors[0] }}</span>
        {%- endif %}
      </div>
      <div>
        {{ form.password_confirm(placeholder="Confirm password") }}
        {% if form.password_confirm.errors -%}
        <span>{{ form.password_confirm.errors[0] }}</span>
        {%- endif %}
      </div>
      <button type="submit">Create account</button>
    </form>
  </body>
</html>
''')


app = Starlette()


@app.route('/', methods=['GET'])
async def index(request):
    """GET /: Return home page
    """
    return PlainTextResponse()


@app.route('/create-account', methods=['GET', 'POST'])
async def create_account(request):
    """GET|POST /create-account: Create account form handler
    """
    # initialize form
    form = await CreateAccountForm.from_formdata(request)

    # validate form
    if await form.validate_on_submit():
        # TODO: Save account credentials before returning redirect response
        return RedirectResponse(url='/', status_code=303)

    # generate html
    html = template.render(form=form)

    # return response
    status_code = 422 if form.errors else 200
    return HTMLResponse(html, status_code=status_code)
```

### Async Custom Validators

The `StarletteForm` class allows you to implement asynchronous [WTForms-like custom validators](https://wtforms.readthedocs.io/en/stable/validators/#custom-validators) by adding `async_validate_{fieldname}` methods to your form classes:

```python
from starlette_wtf import StarletteForm
from wtforms import TextField, PasswordField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo


class CreateAccountForm(StarletteForm):
    email = TextField(
        'Email address',
        validators=[
            DataRequired('Please enter your email address'),
            Email()
        ]
    )

    password = PasswordField(
        'Password',
        widget=PasswordInput(hide_value=False),
        validators=[
            DataRequired('Please enter your password'),
            EqualTo('password_confirm', message='Passwords must match')
        ]
    )

    password_confirm = PasswordField(
        'Confirm Password',
        widget=PasswordInput(hide_value=False),
        validators=[
            DataRequired('Please confirm your password')
        ]
    )

    async def async_validate_email(self, field):
        """Asynchronous validator to check if email is already in-use
        """
        # replace this with your own code
        if await make_database_request_here():
            raise ValidationError('Email is already in use')
```

## CSRF Protection

In order to add CSRF protection to your app, first you must ensure that Starlette's `SessionMiddleware` is enabled, second you must configure Starlette-WTF using `CSRFProtectMiddleware`, third you must use the `@csrf_protect` decorator to protect individual endpoints, and fourth you must add the CSRF token to your HTML forms or JavaScript requests.

### Setup

To enable CSRF protection for your app, first you must ensure that Starlette's `SessionMiddleware` is enabled, and second you must configure Starlette-WTF using `CSRFProtectMiddleware`.

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import CSRFProtectMiddleware


app = Starlette(middleware=[
    Middleware(SessionMiddleware, secret_key='***REPLACEME1***'),
    Middleware(CSRFProtectMiddleware, csrf_secret='***REPLACEME2***')
])
```

### Protect Views

Once Starlette-WTF has been configured using `CSRFProtectMiddleware` you can enable CSRF protection for individual endpoints using the `@csrf_protect` decorator. The `@csrf_protect` decorator will automatically look for `csrf_token` in the form data or in the request headers (`X-CSRFToken`) and it will raise an `HTTPException` if the token is missing or invalid. CSRF token validation will only be performed on submission requests (POST, PUT, PATCH, DELETE). Note that the `@csrf_protect` must run after `@app.route()`:

```python
from starlette.responses import PlainTextResponse
from starlette_wtf import csrf_protect


@app.route('/form-handler', methods=['GET', 'POST'])
@csrf_protect
async def form_handler(request):
    """GET|POST /form-handler: Form handler
    """
    # this code won't run unless the CSRF token has been validated
    return PlainTextResponse()
```

The `@csrf_protect` decorator can also be used with class-based views (e.g. [HTTPEndpoint](https://www.starlette.io/endpoints/)):
```python
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from starlette_wtf import csrf_protect


@csrf_protect
class Endpoint(HTTPEndpoint):
    async def get(self, request):
        # this code will run without a CSRF check
        return PlainTextResponse()

    async def post(self, request):
        # this code won't run unless the CSRF token has been validated
        return PlainTextResponse()
```

The `@csrf_protect` decorator can also be used with bound methods attached to class-based views:
```python
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from starlette_wtf import csrf_protect


class Endpoint(HTTPEndpoint):
    async def get(self, request):
        # this code will run without a CSRF check
        return PlainTextResponse()

    @csrf_protect
    async def post(self, request):
        # this code won't run unless the CSRF token has been validated
        return PlainTextResponse()
```

### HTML Forms

When using `StarletteForm` you can render the form's CSRF token field like this:

```html
<form method="post">
  {{ form.csrf_token }}
</form>
```

### JavaScript Requests

When sending an AJAX request, add the `X-CSRFToken` header to allow Starlette-WTF to perform CSRF validation. For example, in jQuery you can configure all requests to send the token:

```html
<script type="text/javascript">
  var csrf_token = "{{ csrf_token(request) }}";

  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
      }
    }
  });
</script>
```

### Disable in Unit Tests

To disable CSRF protection in unit tests you can toggle the `enabled` attribute in `CSRFProtectionMiddleware`:

```python
from starlette.applications import Starlette
from starlette.config import environ
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import CSRFProtectMiddleware


app = Starlette(middleware=[
    Middleware(SessionMiddleware, secret_key='***REPLACEME1***'),
    Middleware(CSRFProtectMiddleware,
               enable=!environ.get('TESTING', False),
               csrf_secret='***REPLACEME2***')
])
```

### Configuration

`CSRFProtectMiddleware` accepts the following options:

| Argument          | Description
| ----------------- | -----------
| enabled         | If true, enables CSRF protection. Default to True.
| csrf_secret     | The CSRF token signing key.
| csrf_field_name | The CSRF token's field name in the session. Defaults to "csrf_token"
| csrf_time_limit | The time limit for each signed token in seconds. Defaults to 3600.
| csrf_headers    | List of CSRF HTTP header field names. Defaults to ["X-CSRFToken", "X-CSRF-Token"]
| csrf_ssl_strict | If enabled, ensures same origin policy on https requests. Defaults to True.

## Development

### Get the code

Starlette-WTF is actively developed on GitHub. You can clone the repository using git:

```bash
$ git clone git@github.com:muicss/starlette-wtf.git
```

Once you have a copy of the source, you can install it into your site-packages in development mode so you can modify and execute the code:

```bash
$ python setup.py develop
```

### Run unit tests

To install unit test dependencies:

```bash
$ pip install -e .[test]
```

To run unit tests:

```bash
$ pytest
```
