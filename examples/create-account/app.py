from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from starlette_wtf import StarletteForm, CSRFProtectMiddleware, csrf_protect
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo
from wtforms.widgets import PasswordInput


templates = Jinja2Templates('templates')


class CreateAccountForm(StarletteForm):
    """Create account form
    """
    email = StringField(
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


app = Starlette(middleware=[
    Middleware(SessionMiddleware, secret_key='***REPLACEME1***'),
    Middleware(CSRFProtectMiddleware, csrf_secret='***REPLACEME2***')
])


@app.route('/', methods=['GET'])
async def index(request):
    """GET|POST /: return home page
    """
    return templates.TemplateResponse('/index.html', {'request': request})

    
@app.route('/create-account', methods=['GET', 'POST'])
@csrf_protect
async def create_account(request):
    """GET|POST /create-account: create account form handler
    """
    # initialize form
    form = await CreateAccountForm.from_formdata(request)

    # validate form
    if await form.validate_on_submit():
        # TODO: Save account credentials before returning redirect response
        return RedirectResponse(url='/', status_code=303)
        
    # return form html
    context = {'request': request, 'form': form}
    status_code = 422 if form.errors else 200
    
    return templates.TemplateResponse('/create-account.html',
                                      context=context,
                                      status_code=status_code)
