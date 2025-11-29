from parsel import Selector
import asyncio
import sys

try:
    from Worker import PlaywrightWorker
except ImportError as e:
    print(f"[-] Falha ao importar Worker: {e}")
    sys.exit(1)



class ParserEngine:
    def __init__(self, site_cfg):
        self.cfg = site_cfg
        self.groups_cfg = site_cfg["groups"]
        self.url = site_cfg["url"]
        self.worker = PlaywrightWorker(site_cfg)

    async def parse(self, pages_html):
        result = {}

        root_groups = [g for g, c in self.groups_cfg.items() if c.get("parent_group") is None]

        for root in root_groups:
            result[root] = []
            for html in pages_html:
                parsed = await self._parse_group(root, html)
                result[root].append(parsed)

        return result


    async def _parse_group(self, group_name, html):
        group_cfg = self.groups_cfg[group_name]

        sel = Selector(html)
        type_ = group_cfg["type"]
        members = group_cfg.get("members", {})

        group_output = {}

        for key, rule in members.items():
            if key.startswith("selector:"):
                css = key.split("selector:")[1]
                nodes = sel.css(css)

                if type_ == "single":
                    group_output[key] = await self._extract_single(nodes, rule)
                else:
                    group_output[key] = await self._extract_all(nodes, rule)

        child_groups = [
            name for name, cfg in self.groups_cfg.items()
            if cfg.get("parent_group") == group_name
        ]

        for child in child_groups:
            group_output[child] = await self._parse_group(child, html)

        return group_output


    async def _extract_single(self, nodes, rule):
        if not nodes:
            return None
        return await self._extract_node(nodes[0], rule)


    async def _extract_all(self, nodes, rule):
        output = []
        for n in nodes:
            output.append(await self._extract_node(n, rule))
        return output


    async def _extract_node(self, node, rule):
        attr = rule.get("attribute")
        follow = rule.get("follow_link", False)

        if attr:
            value = node.attrib.get(attr)
        else:
            value = node.xpath("string()").get().strip()

        # if follow and value:
        #     pages = await self.worker.execute(value)
        #     return {"url": value, "pages": pages}

        return value
