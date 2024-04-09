from jinja2 import Template
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, HTMLResponse
from starlette_wtf import StarletteForm
from wtforms import StringField
from wtforms.validators	import DataRequired


class MyForm(StarletteForm):
    name = StringField('name', validators=[DataRequired()])


template = Template('''
<html>
  <body>
    <form method="post" novalidate>
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


app = Starlette()


@app.route('/', methods=['GET', 'POST'])
async def index(request):
    form = await MyForm.from_formdata(request)
    
    if await form.validate_on_submit():
        return PlainTextResponse('SUCCESS')

    html = template.render(form=form)
    return HTMLResponse(html)
