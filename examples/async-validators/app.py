import asyncio

from jinja2 import Template
from starlette.applications import Starlette
from starlette.responses import RedirectResponse, HTMLResponse
from starlette.requests import Request
from starlette.status import (HTTP_201_CREATED, HTTP_303_SEE_OTHER,
                              HTTP_400_BAD_REQUEST)
from starlette_wtf import StarletteForm
from wtforms import PasswordField, SubmitField, TextField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo
from wtforms.widgets import PasswordInput


async def db():    
    await asyncio.sleep(.5)
    userdb = {'username':'testpwd', 'username2':'testpwd2'}
    return userdb
    
    
class UserTable():
    async def get_user_by_username(self, username):
        userdb = await db()
        if username:
            return userdb[username]
        
        raise Exception


get_repo = UserTable()


async def check_username_is_taken(table: UserTable, username: str) -> bool:
    try:
        await table.get_user_by_username(username=username)
    except KeyError:
        return False

    return True


class CreateAccountForm(StarletteForm):    
    username = TextField(
        'Username',
        validators=[DataRequired('Please provide username')]
    )
    
    password = PasswordField(
        'Password',
        widget=PasswordInput(hide_value=False),
        validators=[DataRequired('Please enter your password'), EqualTo('password_confirm', message='Passwords must match')]
    )

    password_confirm = PasswordField(
        'Confirm Password',
        widget=PasswordInput(hide_value=False),
        validators=[DataRequired('Please confirm your password')]
    )

    submit = SubmitField('Join Now')


    async def async_validate_username(self, username, user_table: UserTable=get_repo):        
        if await check_username_is_taken(user_table, username.data):
            raise ValidationError('Please use a different username.')


template = Template('''
<html>
  <body>
    <form method="post" novalidate>
      <div>
        {{ form.username(placeholder='Enter username') }}
        {% if form.username.errors -%}
        <span>{{ form.username.errors[0] }}</span>
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
      <p>
        {{ form.submit() }}
      </p>
    </form>
  </body>
</html>    
''')


app = Starlette()


@app.route('/', methods=['GET', 'POST'])
async def index(request: Request):
    """GET|POST /: Form handler
    """
    form = await CreateAccountForm.from_formdata(request)

    if await form.validate_on_submit():
        print('writing to db')
    
    html = template.render(form=form)
    return HTMLResponse(html)
