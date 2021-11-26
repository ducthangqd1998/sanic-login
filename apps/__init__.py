import os
from sanic import Sanic


def create_app():
    app = Sanic("My Hello, world app")
    from .main.views import main
    app.blueprint(main)
    app.static("static", "./apps/static")
    return app
