import scrapy
from collections import defaultdict
from scrapy_playwright.page import PageMethod


class ClassDiscovererSpider(scrapy.Spider):
    name = 'ClassDiscoverer'
    common_names = (
        'clear', 'clearfix', 'active', 'hidden', 'visible', 'row', 'col',
        'container', 'wrapper', 'main', 'header', 'footer', 'section',
        'menu', 'nav', 'btn', 'button', 'image', 'img', 'icon', 'form',
        'input', 'table', 'unj-', 'aside', 'navbar', 'open', 'close', 
        'glyph', 'mb-', 'lh-', 'line-', 'dropdown', 'show', 'modal', 'fade',
        'alert', 'tooltip', 'spw', 'web', 'seta', 'botao', 'gif',
        'div', 'logout', 'inner', 'placeholder', 'fechar', 'fundo', 'bt',
        'offcanvas', 'popup', 'tabela', 'errors', 'action', 'campo', 'bgn',
        'background'
    )

    def __init__(self, p_Url=None):
        self.start_urls = [p_Url] if p_Url else []
        self.class_examples = defaultdict(dict)
        self.id_examples = defaultdict(dict)
        self.other_datas = defaultdict(dict)

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        # Expande todos os colapsáveis
                        PageMethod(
                            "evaluate",
                            """() => {
                                document.querySelectorAll('[class*="collapse"]').forEach(el => {
                                    if (el.style.display === "none" || el.getAttribute("aria-expanded") === "false") {
                                        el.click?.();
                                    }
                                });
                            }"""
                        ),
                        PageMethod("wait_for_timeout", 1000),  # espera carregar
                    ]
                },
                callback=self.parse
            )

    async def parse(self, p_Response):
        self.logger.info(f'Analisando site: {p_Response.url}')
        elements_with_class_or_id = p_Response.xpath('//*[@id or @class]')

        for element in elements_with_class_or_id:
            self.process_element(element, p_Response)

        yield {
            'url': p_Response.url,
            'classes': dict(self.class_examples),
            'ids': dict(self.id_examples),
            'other_datas': dict(self.other_datas),
            'total_classes': len(self.class_examples),
            'total_ids': len(self.id_examples),
            'total_other_datas': len(self.other_datas),
        }

    def process_element(self, p_Element, p_Response):
        tag_name = p_Element.xpath('name()').get()

        id_attr = p_Element.xpath('@id').get()
        class_attr = p_Element.xpath('@class').get()

        if id_attr:
            if self.is_valid_id(id_attr):
                self.add_id(id_attr, p_Element, p_Response)
                return
            else:
                self.add_other_data("id", id_attr, p_Element, p_Response)
                return

        if class_attr:
            classes = class_attr.strip().split()
            valid_added = False
            for css_class in classes:
                if css_class and self.is_valid_class(css_class):
                    self.add_class(css_class, p_Element, p_Response)
                    valid_added = True
            if not valid_added:
                for css_class in classes:
                    self.add_other_data("class", css_class, p_Element, p_Response)

    def is_valid_class(self, p_CssClass):
        return (
            len(p_CssClass) > 2
            and not p_CssClass.startswith(self.common_names)
            and p_CssClass not in self.common_names
            and not p_CssClass.endswith(self.common_names)
        )

    def is_valid_id(self, p_ID):
        return (
            len(p_ID) > 2 
            and not p_ID.startswith(self.common_names)
            and p_ID not in self.common_names
            and not p_ID.endswith(self.common_names)
        )

    def add_class(self, p_CssClass, p_Element, p_Response):
        if p_CssClass not in self.class_examples:
            self.class_examples[p_CssClass] = self.build_data(p_Element, p_Response)

    def add_id(self, p_ID, p_Element, p_Response):
        if p_ID not in self.id_examples:
            self.id_examples[p_ID] = self.build_data(p_Element, p_Response)

    def add_other_data(self, p_Kind, p_Value, p_Element, p_Response):
        key = f"{p_Kind}:{p_Value}"
        if key not in self.other_datas:
            self.other_datas[key] = self.build_data(p_Element, p_Response)

    def build_data(self, p_Element, p_Response):
        tag_name = p_Element.xpath('name()').get()
        attrs = self.get_attributes(p_Element)

        is_link = False
        href = attrs.get('href', '')
        onclick = attrs.get('onclick', '')
        if tag_name == 'a' and (href and not href.startswith('#')):
            is_link = True
        elif 'window.location' in onclick or (href and not href.startswith('#')):
            is_link = True

        return {
            'tag': tag_name,
            'html': self.limit(p_Element.get().strip()),
            'text': p_Element.xpath('string()').get().strip(),
            'xpath': self.get_full_xpath(p_Element),
            'attributes': attrs,
            'has_children': bool(p_Element.xpath('./*')),
            'is_link': is_link
        }


    def limit(self, p_Text, p_MaxLength=200):
        return p_Text[:p_MaxLength] + '...' if len(p_Text) > p_MaxLength else p_Text

    def get_full_xpath(self, p_Element):
        tag_name = p_Element.xpath('name()').get()
        id_attr = p_Element.xpath('@id').get()
        class_attr = p_Element.xpath('@class').get()

        if id_attr:
            return f"//{tag_name}[@id='{id_attr}']"
        elif class_attr:
            classes = class_attr.strip().split()
            if classes:
                return f"//{tag_name}[contains(@class, '{classes[0]}')]"
        return f"//{tag_name}"

    def get_attributes(self, p_Element):
        attributes = {}
        for attr_name, attr_value in p_Element.attrib.items():
            if attr_name and attr_value and attr_name != 'class':
                attributes[attr_name] = self.limit(attr_value, 50)
        return attributes
