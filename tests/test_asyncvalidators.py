from starlette.responses import PlainTextResponse


def test_async_validator_success(app, client, FormWithAsyncValidators):
    async def index(request):
        form = await FormWithAsyncValidators.from_formdata(request)
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


def test_async_validator_error(app, client, FormWithAsyncValidators):
    async def index(request):
        form = await FormWithAsyncValidators.from_formdata(request)
        assert form.field1.data == 'xxx1'
        assert form.field2.data == 'xxx2'

        # validate and check again
        success = await form.validate()
        assert success == False
        assert form.field1.data == 'xxx1'
        assert form.field2.data == 'xxx2'

        # check errors
        assert len(form.errors['field1']) == 1
        assert form.errors['field1'][0] == 'Field value is incorrect.'

        assert len(form.errors['field2']) == 1
        assert form.errors['field2'][0] == 'Field value is incorrect.'

        return PlainTextResponse()

    app.add_route('/', methods=['POST'], route=index)

    client.post('/', data={'field1': 'xxx1', 'field2': 'xxx2'})


def test_data_required_error(app, client, FormWithAsyncValidators):
    async def index(request):
        form = await FormWithAsyncValidators.from_formdata(request)
        assert form.field1.data == 'xxx1'
        assert form.field2.data in ["", None]  # WTForms >= 3.0.0a1 is None

        # validate and check again
        success = await form.validate()
        assert success == False
        assert form.field1.data == 'xxx1'

        # check errors
        assert len(form.errors['field1']) == 1
        assert form.errors['field1'][0] == 'Field value is incorrect.'

        assert len(form.errors['field2']) == 1
        assert form.errors['field2'][0] == 'This field is required.'

        return PlainTextResponse()

    app.add_route('/', methods=['POST'], route=index)

    client.post('/', data={'field1': 'xxx1'})


def test_async_validator_exception(app, client, FormWithAsyncException):
    async def index(request):
        form = await FormWithAsyncException.from_formdata(request)
        try:
            await form.validate()
        except Exception as err:
            assert err.args[0] == 'test'
        else:
            assert False

        return PlainTextResponse()

    app.add_route('/', methods=['POST'], route=index)

    client.post('/', data={'field1': 'xxx1', 'field2': 'xxx2'})


def test_async_validator_with_prefix_success(app, client, FormWithAsyncValidators):
    async def index(request):
        form = await FormWithAsyncValidators.from_formdata(
            request,
            prefix="myprefix-",
        )
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

    client.post('/', data={'myprefix-field1': 'value1', 'myprefix-field2': 'value2'})


def test_async_validator_with_prefix_error(app, client, FormWithAsyncValidators):
    async def index(request):
        form = await FormWithAsyncValidators.from_formdata(
            request,
            prefix="myprefix-",
        )
        assert form.field1.data == 'xxx1'
        assert form.field2.data == 'xxx2'

        # validate and check again
        success = await form.validate()
        assert success == False
        assert form.field1.data == 'xxx1'
        assert form.field2.data == 'xxx2'

        # check errors
        assert len(form.errors['field1']) == 1
        assert form.errors['field1'][0] == 'Field value is incorrect.'

        assert len(form.errors['field2']) == 1
        assert form.errors['field2'][0] == 'Field value is incorrect.'

        return PlainTextResponse()

    app.add_route('/', methods=['POST'], route=index)

    client.post('/', data={'myprefix-field1': 'xxx1', 'myprefix-field2': 'xxx2'})
