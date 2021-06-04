import os

import click
from converter import NotionConverter


@click.command()
@click.argument('root_page_url')
@click.option('--content', default="./content", help='Where do you produce?')
def cli(root_page_url, content):
    notion_converter = NotionConverter(os.getenv('NOTION_TOKEN_V2'), content)
    notion_converter.convert(root_page_url)


if __name__ == '__main__':
    cli()
