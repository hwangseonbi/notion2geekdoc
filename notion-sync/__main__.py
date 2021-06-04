import os

import click
from converter import NotionConverter


# python3 notion-sync --root "https://www.notion.so/hwangseonbi/Draft-699ba9fe0d5946bebd8ede8d7134b4f1"
@click.command()
@click.argument('root_page_url')
@click.option('--content', default="./content", help='Where do you produce?')
def cli(root_page_url, content):
    notion_converter = NotionConverter(os.getenv('NOTION_TOKEN_V2'), content)
    notion_converter.convert(root_page_url)


if __name__ == '__main__':
    cli()
