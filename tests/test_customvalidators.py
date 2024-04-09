from starlette.responses import PlainTextResponse


def test_custom_validator_success(app, client, FormWithCustomValidators):
    async def index(request):
        form = await FormWithCustomValidators.from_formdata(request)
        assert form.field1.data == 'value1'
        assert form.field2.data == 'value2'

        # validate and check again
        success = await form.validate()
        assert success == True

        # check values and errors
        assert form.field1.data == 'value1'
        assert 'field1' not in form.errors
        
        assert form.field2.data == 'value2'
        assert 'field2' not in form.errors

        return PlainTextResponse()

    app.add_route('/', methods=['POST'], route=index)

    client.post('/', data={'field1': 'value1', 'field2': 'value2'})


def test_custom_validator_failure(app, client, FormWithCustomValidators):
    async def index(request):
        form = await FormWithCustomValidators.from_formdata(request)
        assert form.field1.data == 'xxx1'
        assert form.field2.data == 'xxx2'
        
        success = await form.validate()
        assert success == False

        # check values and errors
        assert form.field1.data == 'xxx1'
        assert 'field1' in form.errors

        assert form.field2.data == 'xxx2'
        assert 'field2' in form.errors

        return PlainTextResponse()

    app.add_route('/', methods=['POST'], route=index)

    client.post('/', data={'field1': 'xxx1', 'field2': 'xxx2'})
