from typing import Union

from sanic import Request, HTTPResponse
from sanic.exceptions import (
    NotFound,
    FileNotFound,
    Forbidden,
    ServerError
)
from sanic.response import json

from apps.config.constant import PAGE_NOT_FOUND, FORBIDDEN, INTERNAL_SERVER_ERROR
from apps.main.views import main


@main.exception(NotFound)
async def page_not_found(request: Request,
                         exceptions: Union[FileNotFound, NotFound]) -> HTTPResponse:
    return json({
        "result": True,
        "message": "Page not found"
    }, status=PAGE_NOT_FOUND)


@main.exception(Forbidden)
async def forbidden(request: Request, exception: Forbidden) -> HTTPResponse:
    return json({
        "result": True,
        "message": "Forbidden"
    }, status=FORBIDDEN)


@main.exception(ServerError)
async def server_error(request: Request, exception: ServerError) -> HTTPResponse:
    return json({
        "result": True,
        "message": "Internal Server Error"
    }, status=INTERNAL_SERVER_ERROR)