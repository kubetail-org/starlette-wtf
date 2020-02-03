import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient
from wtforms import FileField, StringField, BooleanField
from wtforms.validators import DataRequired
from wtforms.widgets import CheckboxInput

from starlette_wtf.form import StarletteForm


@pytest.fixture
def app():
    """Create Starlette app instance
    """
    return Starlette()


@pytest.fixture
def client(app):
    """Create Starlette test client
    """
    return TestClient(app)


@pytest.fixture
def BasicForm():
    """Return BasicForm class
    """
    class BasicForm(StarletteForm):
        name = StringField(validators=[DataRequired()])
        avatar = FileField()
        checkbox = BooleanField(widget=CheckboxInput(), default=True)
        
    return BasicForm
