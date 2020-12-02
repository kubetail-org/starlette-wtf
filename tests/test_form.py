import json
from io import BytesIO

from starlette.datastructures import ImmutableMultiDict
from starlette.responses import PlainTextResponse
from wtforms.widgets import HiddenInput


def test_populate_from_get_request(app, client, BasicForm):
    @app.route('/', methods=['GET'])
    async def index(request):
        form = await BasicForm.from_formdata(request)
        assert form.name.data == None
        assert form.avatar.data == None
        assert form.checkbox.data == True
        return PlainTextResponse()

    client.get('/')

        
def test_populate_from_post_request_form(app, client, BasicForm):
    @app.route('/', methods=['POST'])
    async def index(request):
        form = await BasicForm.from_formdata(request)
        assert form.name.data == 'x'
        return PlainTextResponse()

    client.post('/', data={'name': 'x'})


def test_populate_from_post_request_files(app, client, BasicForm):
    @app.route('/', methods=['POST'])
    async def index(request):
        form = await BasicForm.from_formdata(request)
        assert form.avatar.data is not None
        assert form.avatar.data.filename == 'starlette.png'
        return PlainTextResponse()

    f = BytesIO()
    f.name = 'starlette.png'
    client.post('/', files={'avatar': f})


def test_populate_from_post_request_json(app, client, BasicForm):
    @app.route('/', methods=['POST'])
    async def index(request):
        form = await BasicForm.from_formdata(request)
        assert form.name.data == 'json'
        return PlainTextResponse()
    
    client.post('/',
                data=json.dumps({'name': 'json'}),
                headers={'content-type': 'application/json'})


def test_populate_manually(app, client, BasicForm):
    @app.route('/', methods=['POST'])
    async def index(request):
        form = BasicForm(request, request.query_params)
        assert form.name.data == 'args'
        return PlainTextResponse()
    
    client.post('/?name=args')



def test_populate_missing(app, client, BasicForm):
    @app.route('/', methods=['POST'])
    async def index(request):
        form = BasicForm(request)
        assert form.name.data is None
        return PlainTextResponse()

    client.post('/', data={'name': 'ignore'})


def test_populate_after_init(app, client, BasicForm):
    @app.route('/', methods=['POST'])
    async def index(request):
        form = BasicForm(request)
        form.process(formdata=await request.form())
        assert form.name.data == 'x'
        return PlainTextResponse()

    client.post('/', data={'name': 'x'})
    

def test_is_submitted(app, client, BasicForm):
    @app.route('/', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
    async def index(request):
        form = await BasicForm.from_formdata(request)
        return PlainTextResponse(str(form.is_submitted()))

    assert client.get('/').text == 'False'
    assert client.post('/').text == 'True'
    assert client.put('/').text == 'True'
    assert client.patch('/').text == 'True'
    assert client.delete('/').text == 'True'
    

def test_validate(app, client, BasicForm):
    @app.route('/', methods=['GET'])
    async def index(request):
        form = await BasicForm.from_formdata(request)
        await form.validate()
        assert 'name' in form.errors
        return PlainTextResponse()
    
    client.get('/')


def test_manual_populate_and_validate(app, client, BasicForm):
    @app.route('/', methods=['POST'])
    async def index(request):
        formdata = ImmutableMultiDict({'name': 'value1'})

        # initialize and check value
        form = BasicForm(request, formdata)
        assert form.name.data == 'value1'

        # validate and check value again
        await form.validate()
        assert form.name.data == 'value1'

        return PlainTextResponse()

    client.post('/', data={'name': 'value0'})


def test_validate_on_submit(app, client, BasicForm):
    @app.route('/', methods=['GET', 'POST'])
    async def index(request):
        form = await BasicForm.from_formdata(request)

        if await form.validate_on_submit():
            assert request.method == 'POST'

        return PlainTextResponse(str('name' in form.errors))

    # test is_submitted() == False
    assert client.get('/').text == 'False'

    # test is_submitted() == True and validate() == False
    assert client.post('/').text == 'True'

    # test is_submitted() == True and validate() == True
    assert client.post('/', data={'name': 'value'}).text == 'False'
