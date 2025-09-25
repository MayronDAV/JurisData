import scrapy
from collections import defaultdict



class ClassDiscovererSpider(scrapy.Spider):
    name = 'ClassDiscoverer'
    
    def __init__(self, p_Url=None):
        self.start_urls = [p_Url] if p_Url else []
        self.class_examples = defaultdict(list)
        self.id_examples = defaultdict(list)

    def parse(self, p_Response):
        self.logger.info(f'Analisando site: {p_Response.url}')
        elements_with_class = p_Response.xpath('//*[@class]')
        
        for element in elements_with_class:
            self.ProcessElement(element, p_Response)
        
        yield {
            'url': p_Response.url,
            'classes': dict(self.class_examples),
            'ids': dict(self.id_examples),
            'total_classes': len(self.class_examples),
            'total_ids': len(self.id_examples)
        }

    def ProcessElement(self, p_Element, p_Response):
        tag_name = p_Element.xpath('name()').get()

        id_attr = p_Element.xpath('@id').get()
        if id_attr and self.IsValidID(id_attr):
            self.AddIDExample(id_attr, p_Element, p_Response)
            return

        if tag_name == 'div':
            has_child_id_or_class = p_Element.xpath('.//*[@id or @class]')
            if has_child_id_or_class:
                return

        class_attr = p_Element.xpath('@class').get()
        if class_attr:
            classes = class_attr.strip().split()
            for css_class in classes:
                if css_class and self.IsValidClass(css_class):
                    self.AddClassExample(css_class, p_Element, p_Response)

    def IsValidClass(self, p_CssClass):
        common_classes = {
            'clear', 'clearfix', 'active', 'hidden', 'visible', 
            'row', 'col', 'container', 'wrapper', 'main', 'header',
            'footer', 'content', 'section', 'menu', 'nav', 'btn',
            'button', 'text', 'image', 'img', 'icon', 'form', 'input',
            'label', 'table', 'tr', 'td', 'th', 'ul', 'li', 'ol'
        }
        
        return (len(p_CssClass) > 2 and 
                not p_CssClass.startswith(('js-', 'is-', 'has-', 'wp-', 'unj-', 'col-', 'aside-', 'header', 'navbar')) and
                p_CssClass not in common_classes and
                not p_CssClass.endswith(('-wrapper', '-container', '-inner')))

    def IsValidID(self, p_ID):
        """Filtra IDs válidos"""
        return (len(p_ID) > 2 and 
                not p_ID.startswith(('js-', 'is-', 'has-', 'wp-', 'col-')) and
                not p_ID.endswith(('-wrapper', '-container', '-inner')))

    def AddClassExample(self, p_CssClass, p_Element, p_Response):
        if p_CssClass not in self.class_examples:
            example = {
                'tag': p_Element.xpath('name()').get(),
                'html': self.Limit(p_Element.get().strip()),
                'text': p_Element.xpath('string()').get().strip(),
                'xpath': self.GetFullXPath(p_Element),
                'attributes': self.GetAttributes(p_Element),
                'has_children': bool(p_Response.xpath('./*'))
            }
            self.class_examples[p_CssClass] = example

    def AddIDExample(self, p_ID, p_Element, p_Response):
        if p_ID not in self.id_examples:
            example = {
                'tag': p_Element.xpath('name()').get(),
                'html': self.Limit(p_Element.get().strip()),
                'text': p_Element.xpath('string()').get().strip(),
                'xpath': self.GetFullXPath(p_Element),
                'attributes': self.GetAttributes(p_Element),
                'has_children': bool(p_Element.xpath('./*'))
            }
            self.id_examples[p_ID] = example

    def Limit(self, p_Html, p_MaxLength=200):
        if len(p_Html) > p_MaxLength:
            return p_Html[:p_MaxLength] + '...'
        return p_Html

    def GetFullXPath(self, p_Element):
        tag_name = p_Element.xpath('name()').get()
        class_attr = p_Element.xpath('@class').get()
        id_attr = p_Element.xpath('@id').get()
        
        if id_attr:
            return f"//{tag_name}[@id='{id_attr}']"
        elif class_attr:
            classes = class_attr.strip().split()
            if classes:
                return f"//{tag_name}[contains(@class, '{classes[0]}')]"
        
        return f"//{tag_name}"
    
    def GetAttributes(self, p_Element):
        attributes = {}
        for attr_name, attr_value in p_Element.attrib.items():
            if attr_name and attr_value and attr_name != 'class':
                attributes[attr_name] = self.Limit(attr_value, 50)
        return attributes
    
__all__ = [
    'ClassDiscovererSpider'
]