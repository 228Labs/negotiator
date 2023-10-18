from flask import Blueprint, render_template
from flask.typing import ResponseReturnValue


def index_page() -> Blueprint:
    page = Blueprint('index_page', __name__)

    @page.get('/')
    def index() -> ResponseReturnValue:
        return render_template('index.html')

    return page
