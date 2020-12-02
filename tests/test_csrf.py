import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from starlette_wtf import (CSRFProtectMiddleware, StarletteForm, csrf_protect,
                           csrf_token)


@pytest.fixture
def make_csrf_app(app):
    def _make_csrf_app(**options):
        app = Starlette(middleware=[
            Middleware(SessionMiddleware, secret_key='xxx'),
            Middleware(CSRFProtectMiddleware, csrf_secret='yyy', **options)
        ])

        @app.route('/', methods=['GET', 'POST'])
        async def index(request):
            return PlainTextResponse()

        @app.route('/token', methods=['GET'])
        async def token(request):
            token = csrf_token(request)
            return PlainTextResponse(token)

        @app.route('/new-token', methods=['GET'])
        async def new_token(request):
            if 'csrf_token' in request.session:
                request.session.pop('csrf_token')
            token = csrf_token(request)
            return PlainTextResponse(token)
        
        client = TestClient(app)

        return app, client
    
    return _make_csrf_app


def test_disabled_by_default(app, client):
    @app.route('/', methods=['GET'])
    async def index(request):
        form = StarletteForm(request)
        assert hasattr(form, 'csrf_token') == False
        return PlainTextResponse()

    client.get('/')


def test_wtf_form_handling_without_decorator(make_csrf_app):
    app, client = make_csrf_app()

    @app.route('/endpoint', methods=['POST'])
    async def endpoint(request):
        form = await StarletteForm.from_formdata(request)

        if await form.validate_on_submit():
            return PlainTextResponse('SUCCESS')

        # verify that the CSRF token is invalid
        assert form.errors['csrf_token'] == ['The CSRF token is invalid.']
        
        return PlainTextResponse('FAIL')

    # submit form without token
    response = client.post('/endpoint', data={'csrf_token': 'fail'})
    assert response.status_code == 200
    assert response.text == 'FAIL'

    # submit form with token
    signed_token = client.get('/token').text
    response = client.post('/endpoint', data={'csrf_token': signed_token})
    assert response.status_code == 200
    assert response.text == 'SUCCESS'


def test_wtf_form_handling_with_decorator(make_csrf_app, BasicForm):
    app, client = make_csrf_app()

    @app.route('/endpoint', methods=['GET', 'POST'])
    @csrf_protect
    async def endpoint(request):
        form = await BasicForm.from_formdata(request)

        if await form.validate_on_submit():
            return PlainTextResponse('SUCCESS')

        if request.method == 'GET':
            text = 'FORM'
        else:
            text = 'FAIL'
            
        return PlainTextResponse(text)

    # test get request without token
    response = client.get('/endpoint')
    assert response.status_code == 200
    assert response.text == 'FORM'
    
    # test submission without token
    response = client.post('/endpoint', data={'mykey': 'myval'})
    assert response.status_code == 403

    # test submission with token but without required field
    signed_token = client.get('/token').text
    response = client.post('/endpoint', data={'csrf_token': signed_token})
    assert response.status_code == 200
    assert response.text == 'FAIL'

    # test submission with token and required field
    response = client.post('/endpoint', data={
        'csrf_token': signed_token,
        'name': 'myval'
    })
    assert response.status_code == 200
    assert response.text == 'SUCCESS'
                                              

def test_raw_form_handling_with_decorator(make_csrf_app):
    app, client = make_csrf_app()
    
    @app.route('/endpoint', methods=['POST'])
    @csrf_protect
    async def endpoint(request):
        formdata = await request.form()
        assert formdata.get('mykey') == 'myval'
        return PlainTextResponse()

    # test request without token
    response = client.post('/endpoint', data={'mykey': 'myval'})
    assert response.status_code == 403

    # test request with token
    signed_token = client.get('/token').text
    response = client.post('/endpoint', data={
        'mykey': 'myval',
        'csrf_token': signed_token
    })
    assert response.status_code == 200
    

def test_csrf_validation_with_decorator(make_csrf_app):
    app, client = make_csrf_app()
    
    @app.route('/endpoint', methods=['GET', 'POST'])
    @csrf_protect
    async def endpoint(request):
        return PlainTextResponse('SUCCESS')
    
    # test that initial request doesn't have a session token
    response = client.post('/endpoint', data={'csrf_token': 'badtoken'})
    assert response.status_code == 403
    assert response.text == 'The CSRF session token is missing.'

    # populate the session token and use a signed token to make request
    signed_token = client.get('/token').text
    response = client.post('/endpoint', data={'csrf_token': signed_token})
    assert response.status_code == 200
    assert response.text == 'SUCCESS'
    
    # test missing token
    response = client.post('/endpoint')
    assert response.status_code == 403
    assert response.text == 'The CSRF token is missing.'

    # test invalid token
    response = client.post('/endpoint', data={'csrf_token': 'badtoken'})
    assert response.status_code == 403
    assert response.text == 'The CSRF token is invalid.'

    # generate new token and test old token
    client.get('/new-token')
    response = client.post('/endpoint', data={'csrf_token': signed_token})
    assert response.status_code == 403
    assert response.text == 'The CSRF tokens do not match.'


def test_csrf_valid_flag(make_csrf_app):
    app, client = make_csrf_app()

    @app.route('/endpoint', methods=['POST'])
    @csrf_protect
    async def endpoint(request):
        if request.method == 'POST':
            assert hasattr(request.state, 'csrf_valid') == True
        return PlainTextResponse()

    # get token and execute POST
    signed_token = client.get('/token').text
    client.post('/endpoint', data={'csrf_token': signed_token})


def test_method_not_allowed(make_csrf_app):
    app, client = make_csrf_app()

    @app.route('/endpoint', methods=['POST'])
    @csrf_protect
    async def endpoint(request):
        return PlainTextResponse()

    # test request with unexpected method
    response = client.get('/endpoint')
    assert response.status_code == 405


def test_csrf_headers(make_csrf_app):
    app, client = make_csrf_app()

    @app.route('/endpoint', methods=['POST'])
    @csrf_protect
    async def endpoint(request):
        return PlainTextResponse()

    signed_token = client.get('/token').text

    # good X-CSRFToken
    response = client.post('/endpoint', headers={'X-CSRFToken': signed_token})
    assert response.status_code == 200

    # good X-CSRF-Token
    response = client.post('/endpoint', headers={'X-CSRF-Token': signed_token})
    assert response.status_code == 200
    
    # check capitalization
    response = client.post('/endpoint', headers={'x-csrf-token': signed_token})
    assert response.status_code == 200

    # bad token
    response = client.post('/endpoint', headers={'X-CSRFToken': 'xxx'})
    assert response.status_code == 403


def test_csrf_ssl_strict(make_csrf_app):
    app, client = make_csrf_app()

    @app.route('/endpoint', methods=['POST'])
    @csrf_protect
    async def endpoint(request):
        assert request.url.scheme == 'https'
        assert request.headers['REFERER'] == 'https://testserver/'
        return PlainTextResponse()

    signed_token = client.get('/token').text

    # same origin
    response = client.post('https://testserver/endpoint',
                           headers={'REFERER': 'https://testserver/'},
                           data={'csrf_token': signed_token})
    assert response.status_code == 200

    # different scheme
    response = client.post('https://testserver/endpoint',
                           headers={'REFERER': 'http://testserver/'},
                           data={'csrf_token': signed_token})
    assert response.status_code == 403

    # different hostname
    response = client.post('https://testserver/endpoint',
                           headers={'REFERER': 'https://testserver2/'},
                           data={'csrf_token': signed_token})
    assert response.status_code == 403

    # different port
    response = client.post('https://testserver/endpoint',
                           headers={'REFERER': 'https://testserver:8080/'},
                           data={'csrf_token': signed_token})
    assert response.status_code == 403
