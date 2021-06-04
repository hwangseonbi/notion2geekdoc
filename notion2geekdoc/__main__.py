import os
import click
from converter import NotionConverter


@click.command()
@click.argument('root_page_url')
@click.option('--draft', default=False, help='Build include draft')
@click.option('--content', default="./content", help='Where do you produce?')
def cli(root_page_url, draft, content):
    notion_converter = NotionConverter(os.getenv('NOTION_TOKEN_V2'), content)
    notion_converter.convert(root_page_url, draft=draft)


if __name__ == '__main__':
    cli()
