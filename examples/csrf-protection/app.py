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
