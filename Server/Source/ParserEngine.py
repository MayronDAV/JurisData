from parsel import Selector
import sys
import time



class UniversalParser:
    def __init__(self, site_cfg):
        self.cfg = site_cfg
        self.url = site_cfg.get("url", "")
        
    async def parse_all_texts_with_tags(self, pages_html):
        all_results = []
        
        for page_num, html in enumerate(pages_html, 1):
            page_results = await self._parse_page(html, page_num)
            all_results.extend(page_results)
            
        return all_results
    
    async def _parse_page(self, html, page_num):
        results = []
        sel = Selector(html)
        
        elements = sel.xpath('//*[normalize-space(text())]')
        
        for element in elements:
            tag_name = element.root.tag
            
            text = element.xpath('normalize-space(.)').get()
            
            if text and text.strip():
                attrs = dict(element.root.attrib) if element.root.attrib else {}
                xpath = await self._get_element_xpath(element)
                
                parent_hierarchy = await self._get_parent_hierarchy(element)
                
                results.append({
                    "page": page_num,
                    "tag": tag_name,
                    "text": text.strip(),
                    "attrs": attrs,
                    "xpath": xpath,
                    "parent_hierarchy": parent_hierarchy,
                    "full_html": element.get()
                })
        
        return results
    
    async def _get_element_xpath(self, element):
        try:
            parts = []
            current = element
            
            while current.root.getparent() is not None:
                parent = current.root.getparent()
                index = 1
                
                # Conta irmãos com a mesma tag
                siblings = [sibling for sibling in parent if sibling.tag == current.root.tag]
                if len(siblings) > 1:
                    for i, sibling in enumerate(siblings, 1):
                        if sibling == current.root:
                            index = i
                            break
                    tag_part = f"{current.root.tag}[{index}]"
                else:
                    tag_part = current.root.tag
                
                parts.insert(0, tag_part)
                current = Selector(root=parent)
            
            return "/" + "/".join(parts)
        except:
            return "//*[contains(text(), '{}')]".format(element.xpath('normalize-space(.)').get()[:50])
    
    async def _get_parent_hierarchy(self, element, max_depth=5):
        hierarchy = []
        current = element
        depth = 0
        
        while current.root.getparent() is not None and depth < max_depth:
            parent = current.root.getparent()
            parent_sel = Selector(root=parent)

            parent_info = {
                "tag": parent.tag,
                "attrs": dict(parent.attrib) if parent.attrib else {},
                "class": parent.get("class", ""),
                "id": parent.get("id", "")
            }
            
            hierarchy.append(parent_info)
            current = parent_sel
            depth += 1
        
        return hierarchy
    
    async def parse_with_config(self, pages_html, custom_config=None):
        config = custom_config or {
            "tags": "*",
            "min_text_length": 3,
            "exclude_empty": True,
            "include_attributes": ["class", "id", "href", "src", "style"]
        }
        
        all_results = []
        
        for page_num, html in enumerate(pages_html, 1):
            sel = Selector(html)
            results = []

            if config["tags"] == "*":
                xpath_query = '//*[normalize-space(text())]'
            else:
                tags_list = config["tags"]
                tags_query = "|".join([f"//{tag}[normalize-space(text())]" for tag in tags_list])
                xpath_query = f"{tags_query}"
            
            elements = sel.xpath(xpath_query)
            
            for element in elements:
                text = element.xpath('normalize-space(.)').get()
                
                if config["exclude_empty"] and (not text or len(text.strip()) < config["min_text_length"]):
                    continue
                
                if text and text.strip():
                    tag_name = element.root.tag
                    
                    attrs = {}
                    if config.get("include_attributes"):
                        for attr_name in config["include_attributes"]:
                            attr_value = element.root.get(attr_name)
                            if attr_value:
                                attrs[attr_name] = attr_value
                    
                    results.append({
                        "page": page_num,
                        "tag": tag_name,
                        "text": text.strip(),
                        "attrs": attrs,
                        "full_element": element.get()
                    })
            
            all_results.extend(results)
        
        return all_results



class ParserEngine:
    def __init__(self, site_cfg):
        self.site_cfg = site_cfg
        self.universal_parser = UniversalParser(site_cfg)
    
    async def parse(self, pages_html):
        complete_data = await self.universal_parser.parse_all_texts_with_tags(pages_html)

        formatted_result = await self._format(complete_data, pages_html)
        
        return formatted_result
    
    async def _format(self, parsed_data, pages_html):
        result = {
            self.site_cfg["url"]: {
                "all_text_elements": parsed_data,
                "metadata": {
                    "total_pages": len(pages_html),
                    "total_elements": len(parsed_data),
                    "timestamp": time.time()
                }
            }
        }
        return result
