from sanic import Sanic
from sanic import response
from sanic_jinja2 import SanicJinja2
from sanic import Blueprint

app = Blueprint(__name__)
jinja = SanicJinja2(app, pkg_name="main")


@app.routes("/")
async def index(request):
    return jinja.render("main/index.js", request)



