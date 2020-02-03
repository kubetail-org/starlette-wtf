import pytest
import time
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient
from wtforms import ValidationError

from starlette_wtf.util import generate_csrf, validate_csrf


@pytest.fixture
def make_app(app):
    def _make_app():
        wrapped = SessionMiddleware(app, secret_key='xxx')
        client = TestClient(wrapped)

        return app, client

    return _make_app


def test_generate_csrf(make_app):
    app, client = make_app()

    @app.route('/', methods=['GET'])
    async def index(request):
        kwargs = dict(secret_key='yyy', field_name='csrf_token')
        
        # verify that state is empty
        assert hasattr(request.state, 'csrf_token') == False
        
        # generate token
        signed_token = generate_csrf(request, **kwargs)

        assert signed_token != None

        # verify idempotence within a request
        assert signed_token == generate_csrf(request, **kwargs)

        return PlainTextResponse()
    
    client.get('/')


def test_generate_csrf_with_typeerror(make_app):
    app, client = make_app()

    @app.route('/', methods=['GET'])
    async def index(request):
        # seed with bad data
        request.session['y'] = 1

        # run generate method
        signed_token = generate_csrf(request, secret_key='x', field_name='y')

        return PlainTextResponse()

    client.get('/')
    
        
def test_validate_csrf(make_app):
    app, client = make_app()

    @app.route('/', methods=['GET'])
    async def index(request):
        kwargs = {'secret_key': 'yyy', 'field_name': 'csrf_token'}
        
        # generate token
        signed_token = generate_csrf(request, **kwargs)

        # test valid data
        validate_csrf(request, signed_token, **kwargs)

        # test invalid data
        with pytest.raises(ValidationError) as excinfo:
            validate_csrf(request, 'notvalid', **kwargs)

        assert str(excinfo.value) == 'The CSRF token is invalid.'
        
        return PlainTextResponse()

    client.get('/')


def test_validate_csrf_expired(make_app):
    app, client = make_app()

    @app.route('/', methods=['GET'])
    async def index(request):
        kwargs = {'secret_key': 'yyy', 'field_name': 'csrf_token'}
        
        # generate token
        signed_token = generate_csrf(request, **kwargs)

        # test valid data
        validate_csrf(request, signed_token, **kwargs)

        # test expired data
        with pytest.raises(ValidationError) as excinfo:
            validate_csrf(request, signed_token, time_limit=-1, **kwargs)

        assert str(excinfo.value) == 'The CSRF token has expired.'
            
        return PlainTextResponse()

    client.get('/')


def test_validation_across_clients(app):
    # make clients
    wrapped = SessionMiddleware(app, secret_key='xxx')
    client1 = TestClient(wrapped)
    client2 = TestClient(wrapped)

    # make app
    kwargs = dict(secret_key='yyy', field_name='csrf_token')
    
    @app.route('/generate', methods=['GET'])
    async def generate(request):
        signed_token = generate_csrf(request, **kwargs)
        return PlainTextResponse(signed_token)

    @app.route('/validate', methods=['GET'])
    async def validate(request):
        signed_token = request.query_params['csrf_token']

        try:
            validate_csrf(request, signed_token, **kwargs)
        except ValidationError:
            return PlainTextResponse('False')

        return PlainTextResponse('True')

    # get signed token from client1
    signed_token1 = client1.get('/generate').text

    # client1 should accept the token
    response = client1.get('/validate', params={'csrf_token': signed_token1})
    assert response.text == 'True'
    
    # client2 should reject the token
    response = client2.get('/validate', params={'csrf_token': signed_token1})
    assert response.text == 'False'

    # get signed token from client2
    signed_token2 = client2.get('/generate').text

    # client1 should reject the token
    response = client1.get('/validate', params={'csrf_token': signed_token2})
    assert response.text == 'False'
    
    # client2 should accept the token
    response = client2.get('/validate', params={'csrf_token': signed_token2})
    assert response.text == 'True'
