import json

from discord import Embed
from discord import Colour

with open('./config.json') as data:
    EMBED_COLOUR = json.load(data)["embed color"]

def get_default_color():
    return EMBED_COLOUR

def create_embed(**kwargs) -> Embed:
    """Creates a discord embed object."""
    embed_type = kwargs.get('type', Embed.Empty)
    title = kwargs.get('title', Embed.Empty)
    description = kwargs.get('description', Embed.Empty)
    color = kwargs.get('color', get_default_color())
    timestamp = kwargs.get('timestamp', Embed.Empty)
    url = kwargs.get('url', Embed.Empty)

    return Embed(
        type=embed_type,
        title=title,
        description=description,
        url=url,
        color=color,
        timestamp=timestamp
    )

def create_success_embed(**kwargs) -> Embed:
    return create_embed(color=Colour.green(), **kwargs)

def error(content: str) -> Embed:
    return create_error_embed(description=content)

def create_error_embed(title=Embed.Empty, description=Embed.Empty) -> Embed:
    return create_embed(title=title, description=description, color=Colour.red())

def build_embed(**kwargs):
    """Creates a discord embed object."""
    return create_embed(**kwargs)


def setup(client):
    pass

def teardown(client):
    pass