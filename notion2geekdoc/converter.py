from pathlib import Path
from notion.client import NotionClient
from notion import block
from yaml import dump as yaml_dump
import requests


class Resources:
    SIZE_TINY = 'tiny'
    SIZE_SMALL = 'small'
    SIZE_MEDIUM = 'medium'
    SIZE_LARGE = 'large'

    def __init__(self, file_id, display_source, width):
        self.file_id = file_id
        self.display_source = display_source
        self.width = width

    def get_file_name_path(self):
        return Path("%s.png" % self.file_id)

    def get_size(self, width):
        if width < 450:
            return self.SIZE_SMALL
        elif width < 500:
            return self.SIZE_MEDIUM
        else:
            return self.SIZE_LARGE

    def to_dict(self):
        return {
            "name": str(self.get_file_name_path()),
            "src": str(self.get_file_name_path()),
            "title": ''
        }


class NotionConverter:
    def __init__(self, notion_token, output_root_dir):
        self.client = NotionClient(token_v2=notion_token)
        self.root_dir_path = Path(output_root_dir)

        self._init_dir(self.root_dir_path)

    def _init_dir(self, root_dir_path):
        import shutil
        if root_dir_path.is_dir():
            shutil.rmtree(root_dir_path)

    def make_category_dir(self, name):
        name_path = Path(name)
        (self.root_dir_path / name_path).mkdir()

    def block_to_geekdoc(self, content, weight=0):
        blog_content_list = []
        header = ''
        resources = []

        def analyze_page(page, recursive=0):
            for child in page.children:
                tab = "\t" * recursive

                child_type = block.BLOCK_TYPES.get(child.type)

                if child_type == None:
                    if child.type == 'table_of_contents':
                        blog_content_list.append("{{< toc >}}")

                elif child_type == block.HeaderBlock:
                    safe_md = child.title.replace("<", "&lt;").replace(">", "&gt;")
                    blog_content_list.append("# %s" % safe_md)

                elif child_type == block.SubheaderBlock:
                    safe_md = child.title.replace("<", "&lt;").replace(">", "&gt;")
                    blog_content_list.append("## %s" % safe_md)

                elif child_type == block.SubsubheaderBlock:
                    safe_md = child.title.replace("<", "&lt;").replace(">", "&gt;")
                    blog_content_list.append("### %s" % safe_md)

                elif child_type == block.TextBlock:
                    if child.title == '':
                        blog_content_list.append("<br>")
                    safe_md = child.title.replace("__", "**").replace("<", "&lt;").replace(">", "&gt;")
                    blog_content_list.append(tab + safe_md)
                    # analyze_page(child, recursive=recursive + 1)

                elif child_type == block.ToggleBlock:
                    safe_md = child.title.replace("\"", "'").replace("__", "").replace("<", "&lt;").replace(">", "&gt;")
                    blog_content_list.append(tab + "{{< expand \"▼ %s\">}}" % safe_md)
                    analyze_page(child, recursive=recursive)
                    blog_content_list.append(tab + "{{< /expand >}}")

                elif child_type == block.DividerBlock:
                    blog_content_list.append("---")

                elif child_type == block.ImageBlock:
                    r = Resources(child.file_id, child.display_source, child.width)
                    resources.append(r)
                    blog_content_list.append(tab +
                                             "{{< img name=\"%s\" size=\"%s\" width=\"%d\" lazy=false >}}"
                                             % (r.get_file_name_path(), r.get_size(r.width), r.width))

                elif child_type == block.NumberedListBlock:
                    safe_md = child.title.replace("__", "**").replace("<", "&lt;").replace(">", "&gt;")
                    blog_content_list.append("%s1. %s" % ("\t" * recursive, safe_md))
                    analyze_page(child, recursive=recursive + 1)

                elif child_type == block.QuoteBlock:
                    safe_md = "***" + child.title.replace("\n", "<br>").strip() + "***"
                    safe_md = "> " + safe_md
                    blog_content_list.append(safe_md)

                elif child_type == block.BulletedListBlock:
                    safe_md = tab + "- " + child.title
                    blog_content_list.append(safe_md)
                    analyze_page(child, recursive=recursive + 1)

                elif child_type == block.TodoBlock:
                    safe_md = tab + "- [%s] " % (' ' if child.checked else 'x') + child.title
                    blog_content_list.append(safe_md)
                    analyze_page(child, recursive=recursive + 1)
                elif child_type == block.VideoBlock:
                    blog_content_list.append("{{< youtube %s >}}" % Path(child.source).name)
                    analyze_page(child, recursive=recursive + 1)
                else:
                    print("[%s] %s" % (child_type, child))

        page = self.client.get_block(content.id)
        analyze_page(page)

        header = """---\n%s\n---\n""" % yaml_dump({
            "title": page.title,
            "date": page.LastEditedTime,
            "weight": weight,
            "resources": list(map(lambda r: r.to_dict(), resources))
        }, allow_unicode=True)

        return header, "\n\n".join(blog_content_list), resources

    def write_content(self, content_file_path, header, blog_content):
        with open(content_file_path, 'w') as f:
            f.write(header)
            f.write(blog_content)

    def download_resources(self, content_dir_path, resources):
        for resource in resources:
            resource_path = (content_dir_path / resource.get_file_name_path())

            with open(resource_path, "wb") as f:  # open in binary mode
                response = requests.get(resource.display_source)  # get request
                f.write(response.content)  # write to file

    def create_category_index_file(self, category_dir_path, title, weight):
        index_file_name = "_index.md"
        file_path = category_dir_path / Path(index_file_name)

        header = """---\n%s\n---\n""" % yaml_dump({
            "title": title,
            "weight": weight,
            "geekdocCollapseSection": True
        }, allow_unicode=True)

        with open(file_path, "w") as f:
            f.write(header)

    def convert(self, root_page_url, draft=False):
        self.root_dir_path.mkdir()

        root_page = self.client.get_block(root_page_url)
        collection_view_list = [child for child in root_page.children if
                                block.BLOCK_TYPES.get(child.type) == block.CollectionViewBlock]

        for seq, collection_view in enumerate(collection_view_list):
            category_dir_path = self.root_dir_path / Path(collection_view.title)
            category_dir_path.mkdir()
            self.create_category_index_file(category_dir_path, title=collection_view.title, weight=seq)

            contents = collection_view.collection.get_rows()
            for content_seq, content in enumerate(contents):
                publish_ok = False
                if content.status == "Published":
                    publish_ok = True
                elif content.status == "Draft" and draft:
                    publish_ok = True
                else:
                    print("Unknown content status : %s" % content.status)

                if publish_ok:
                    content_dir_path = category_dir_path / Path(content.id)
                    content_dir_path.mkdir()

                    header, blog_content, resources = self.block_to_geekdoc(content, weight=content_seq)

                    self.write_content(
                        content_file_path=content_dir_path / Path("_index.md"),
                        header=header,
                        blog_content=blog_content)
                    self.download_resources(content_dir_path, resources)
