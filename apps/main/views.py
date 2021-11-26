from sanic import Request
from sanic.response import json, html
from sanic import Blueprint
from apps.config.constant import SUCCESS

main = Blueprint(__name__)


@main.route("/")
async def index(request: Request):

    # return json({
    #     "success": True,
    #     "message": "Success"
    # }, status=SUCCESS)
    with open('apps/templates/main/login.html', "r") as f:
        h = f.read()

    return html(h)




