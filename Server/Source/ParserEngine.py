from parsel import Selector
import time
import re
import os
import json


class UniversalParser:
    def __init__(self, site_cfg):
        self.cfg = site_cfg
        self.url = site_cfg.get("url", "")

    async def parse(self, pages_html):
        selector_map = {}
        element_order = {}
        
        for html in pages_html:
            sel = Selector(html)
            elements = sel.xpath("//*")

            for idx, element in enumerate(elements):
                root = element.root
                selector = self._build_selector(element)
                
                text = element.xpath("normalize-space(.)").get()
                if not text:
                    continue

                element_order.setdefault(selector, []).append(idx)

                if selector not in selector_map:
                    selector_map[selector] = []
                selector_map[selector].append(text)

                ancestral_selectors = self._find_ancestral_selectors_in_order(root)
                
                for ancestral in ancestral_selectors:
                    if ancestral:
                        combined_tag = f"{ancestral} {root.tag}"
                        if combined_tag not in selector_map:
                            selector_map[combined_tag] = []
                        selector_map[combined_tag].append(text)
                        
                        if selector.startswith(".") or selector.startswith("#"):
                            combined_selector = f"{ancestral} {selector}"
                            if combined_selector not in selector_map:
                                selector_map[combined_selector] = []
                            selector_map[combined_selector].append(text)

                        attrs = root.attrib
                        raw_classes = (attrs.get("class") or "").strip()
                        classes = [c for c in raw_classes.split() if c.strip()] if raw_classes else []
                        
                        if classes:
                            for cls in classes:
                                combined_class = f"{ancestral} .{cls}"
                                if combined_class not in selector_map:
                                    selector_map[combined_class] = []
                                selector_map[combined_class].append(text)

        ordered_selector_map = self._order_selectors_by_appearance(selector_map, element_order)
        
        return ordered_selector_map

    def _order_selectors_by_appearance(self, selector_map, element_order):
        ordered_map = {}
        
        for selector, texts in selector_map.items():
            if selector in element_order:
                order_indices = element_order[selector]
                
                if len(texts) == len(order_indices):
                    ordered_map[selector] = texts
                else:
                    ordered_map[selector] = texts
            else:
                ordered_map[selector] = texts
        
        return ordered_map

    def _find_ancestral_selectors_in_order(self, element):
        ancestors = []
        parent = element.getparent()
        
        while parent is not None:
            attrib = parent.attrib

            if "id" in attrib and attrib["id"].strip():
                id_selector = f"#{attrib['id'].strip()}"
                if id_selector not in ancestors:
                    ancestors.append(id_selector)
            
            if "class" in attrib and attrib["class"].strip():
                cls_list = [c for c in attrib["class"].split() if c.strip()]
                if cls_list:
                    full_class_selector = "." + ".".join(cls_list)
                    if full_class_selector not in ancestors:
                        ancestors.append(full_class_selector)
                    
                    if len(cls_list) > 1:
                        first_class_selector = f".{cls_list[0]}"
                        if first_class_selector not in ancestors:
                            ancestors.append(first_class_selector)
            
            parent = parent.getparent()
        
        return ancestors

    def _build_selector(self, element):
        root = element.root
        tag = root.tag
        attrs = root.attrib

        element_id = (attrs.get("id") or "").strip()
        raw_classes = (attrs.get("class") or "").strip()
        classes = [c for c in raw_classes.split() if c.strip()] if raw_classes else []

        if element_id:
            return f"#{element_id}"

        if classes:
            return "." + ".".join(classes)
        
        return tag


class DataOrganizer:
    def __init__(self, site_cfg):
        self.site_cfg = site_cfg
        self.groups_cfg = site_cfg.get("groups", {})
        self.group_cache = {}
        self.processed_selector_map_cache = {}
        self.first_cyclic_blocks = {}


    async def organize(self, selector_map):
        self._preprocess_selector_map(selector_map)
        
        hierarchy = self._build_groups_hierarchy()
        organized_data = self._process_groups_hierarchically(hierarchy, self.processed_selector_map_cache)
        return organized_data


    def _preprocess_selector_map(self, selector_map):
        for group_name, group_config in self.groups_cfg.items():
            members = group_config.get("members", {})
            for member, member_cfg in members.items():
                if member in selector_map:
                    original_texts = selector_map[member]
                    
                    if member_cfg.get("unique_consecutive", False):
                        processed_texts = self._remove_consecutive_duplicates(original_texts)
                    else:
                        processed_texts = original_texts.copy() if original_texts else []
                    
                    if member_cfg.get("trim_whitespace", True):
                        processed_texts = [text.strip() if text else text for text in processed_texts]
                    
                    if member_cfg.get("remove_empty", False):
                        processed_texts = [text for text in processed_texts if text and text.strip()]

                    not_reorder_target = member_cfg.get("not_reorder")
                    if not_reorder_target:
                        processed_texts = self._apply_not_reorder(processed_texts, not_reorder_target, selector_map)

                    value_not = member_cfg.get("not")
                    if value_not:
                        not_texts = self._get_not_texts(value_not, selector_map)
                        mode = member_cfg.get("not_mode", "global")
                        processed_texts = self._apply_not_operation_to_list(processed_texts, not_texts, mode)
                    
                    if member_cfg.get("cyclic", False):
                        block_size = member_cfg.get("cyclic_block_size")
                        if block_size and block_size > 0:
                            first_block = processed_texts[:block_size]
                            self.first_cyclic_blocks[member] = first_block
                        else:
                            self.first_cyclic_blocks[member] = processed_texts.copy()
                    
                    self.processed_selector_map_cache[member] = processed_texts
        
        for selector, texts in selector_map.items():
            if selector not in self.processed_selector_map_cache:
                self.processed_selector_map_cache[selector] = texts.copy() if texts else []


    def _apply_not_reorder(self, member_texts, target_selector, selector_map):
        if not member_texts:
            return member_texts
        
        target_texts = selector_map.get(target_selector, [])
        if not target_texts:
            return member_texts
        
        if target_selector in self.first_cyclic_blocks:
            target_block = self.first_cyclic_blocks[target_selector]
            
            if len(member_texts) != len(target_block):
                return self._reorder_by_cyclic_target(member_texts, target_block, target_texts)
            
            return member_texts
        
        return self._reorder_by_simple_target(member_texts, target_texts)


    def _reorder_by_cyclic_target(self, member_texts, target_block, target_full_texts):
        if not member_texts or not target_block:
            return member_texts
        
        if len(member_texts) > len(target_block):
            block_size = len(target_block)
            num_blocks = len(member_texts) // block_size
            
            if num_blocks > 0:
                reordered = []
                for block_idx in range(num_blocks):
                    start = block_idx * block_size
                    end = start + block_size
                    block = member_texts[start:end]
                    reordered.extend(block)

                remaining = member_texts[num_blocks * block_size:]
                reordered.extend(remaining)
                return reordered
        
        return member_texts[:len(target_block)]


    def _reorder_by_simple_target(self, member_texts, target_texts):
        if not member_texts or not target_texts:
            return member_texts
        
        if len(member_texts) == len(target_texts):
            return member_texts
        
        if len(member_texts) < len(target_texts):
            return member_texts + [None] * (len(target_texts) - len(member_texts))
        
        return member_texts[:len(target_texts)]


    def _remove_consecutive_duplicates(self, texts):
        if not texts:
            return texts
        
        result = []
        last_value = None
        
        for text in texts:
            if text != last_value:
                result.append(text)
                last_value = text
        
        return result


    def _build_groups_hierarchy(self):
        hierarchy = {}
        
        for group_name, group_config in self.groups_cfg.items():
            parent = group_config.get("parent_group")
            hierarchy[group_name] = {
                "config": group_config,
                "parent": parent,
                "children": []
            }

        for group_name, group_info in hierarchy.items():
            parent = group_info["parent"]
            if parent and parent in hierarchy:
                hierarchy[parent]["children"].append(group_name)
        
        return hierarchy
    

    def _get_not_texts(self, value_not, selector_map):
        if not value_not:
            return []
        if value_not in self.first_cyclic_blocks:
            return self.first_cyclic_blocks[value_not]
        return selector_map.get(value_not, [])


    def _process_groups_hierarchically(self, hierarchy, selector_map):
        root_groups = [name for name, info in hierarchy.items() if info["parent"] is None]
        
        result = {}
        for root_group in root_groups:
            root_data = self._process_root_group(root_group, hierarchy, selector_map)
            result[root_group] = root_data
        
        return result


    def _process_root_group(self, group_name, hierarchy, selector_map):
        group_info = hierarchy[group_name]
        group_config = group_info["config"]
        group_type = group_config.get("type", "single")
        
        total_items = self._get_root_group_total_items(group_config, selector_map)
        
        all_items = []
        for item_index in range(total_items):
            item_data = self._process_group_item(group_name, hierarchy, selector_map, group_type, item_index, total_items)
            all_items.append(item_data)
        
        return all_items


    def _get_root_group_total_items(self, group_config, selector_map):
        members = group_config.get("members", {})
        group_type = group_config.get("type", "single")
        
        if group_type == "all":
            return 1

        max_items = 0
        for member, member_cfg in members.items():
            member_items = selector_map.get(member, [])
            if len(member_items) > max_items:
                max_items = len(member_items)
        
        return max_items


    def _process_group_item(self, group_name, hierarchy, selector_map, group_type, item_index, total_items):
        group_info = hierarchy[group_name]
        group_config = group_info["config"]
        children = group_info["children"]
        
        item_data = self._process_item_members(group_config, selector_map, group_type, item_index, total_items)
        
        for child_name in children:
            child_data = self._process_child_for_item(child_name, hierarchy, selector_map, group_type, item_index, total_items)
            item_data[child_name] = child_data
        
        return item_data
    

    def _process_item_members(self, group_config, selector_map, group_type, item_index, total_items):
        members = group_config.get("members", {})
        
        if group_type == "all":
            return self._process_all_members_for_item(members, selector_map)
        elif isinstance(group_type, dict) and "multiple" in group_type:
            count = group_type["multiple"]
            return self._process_multiple_members_for_item(members, selector_map, count, item_index, total_items)
        else:  # single
            return self._process_single_members_for_item(members, selector_map, item_index, total_items)
    

    def _process_all_members_for_item(self, members, selector_map):
        result = {}
        for member, member_cfg in members.items():
            if member in self.first_cyclic_blocks:
                result[member] = self.first_cyclic_blocks[member].copy()
            else:
                member_occurrences = selector_map.get(member, [])

                value_not = member_cfg.get("not")
                if value_not:
                    not_occurrences = self._get_not_texts(value_not, selector_map)
                    mode = member_cfg.get("not_mode", "global")
                    processed = self._apply_not_operation_to_list(member_occurrences, not_occurrences, mode)
                    result[member] = processed
                else:
                    result[member] = member_occurrences

        return result
    

    def _process_single_members_for_item(self, members, selector_map, item_index, total_items):
        result = {}

        for member, member_cfg in members.items():
            if member in self.first_cyclic_blocks:
                first_block = self.first_cyclic_blocks[member]
                if first_block:
                    position = item_index % len(first_block)
                    text = first_block[position]
                else:
                    text = None

                value_not = member_cfg.get("not")
                if value_not and text:
                    not_texts = self._get_not_texts(value_not, selector_map)
                    if not_texts:
                        not_text = not_texts[item_index % len(not_texts)]
                        if not_text and not_text in text:
                            text = text.replace(not_text, "").strip()

                result[member] = text
                continue

            all_texts = selector_map.get(member, [])
            text = all_texts[item_index] if item_index < len(all_texts) else None

            value_not = member_cfg.get("not")
            if value_not and text:
                not_texts = self._get_not_texts(value_not, selector_map)
                if not_texts and item_index < len(not_texts):
                    not_text = not_texts[item_index]
                    if not_text and not_text in text:
                        text = text.replace(not_text, "").strip()

            result[member] = text

        return result
    

    def _process_multiple_members_for_item(self, members, selector_map, count, item_index, total_items):
        result = {}

        for member, member_cfg in members.items():
            if member in self.first_cyclic_blocks:
                first_block = self.first_cyclic_blocks[member]
                block_values = first_block[:min(count, len(first_block))]

                value_not = member_cfg.get("not")
                if value_not:
                    not_list = self._get_not_texts(value_not, selector_map)
                    cleaned = []
                    for i, val in enumerate(block_values):
                        if val is None:
                            cleaned.append(val)
                            continue
                        if not_list:
                            not_txt = not_list[i % len(not_list)]
                            if not_txt and not_txt in val:
                                val = val.replace(not_txt, "").strip()
                        cleaned.append(val)
                    result[member] = cleaned
                else:
                    result[member] = block_values.copy()
                continue

            all_texts = selector_map.get(member, [])

            value_not = member_cfg.get("not")
            if value_not:
                not_texts_all = self._get_not_texts(value_not, selector_map)
                if not_texts_all and all_texts:
                    mode = member_cfg.get("not_mode", "global")
                    all_texts = self._apply_not_operation_to_list(all_texts, not_texts_all, mode)

            start_idx = item_index * count
            end_idx = start_idx + count
            block_values = all_texts[start_idx:end_idx] if start_idx < len(all_texts) else []
            result[member] = block_values

        return result
    

    def _process_child_for_item(self, child_name, hierarchy, selector_map, parent_group_type, parent_item_index, total_parent_items):
        if parent_group_type == "all":
            return self._process_group(child_name, hierarchy, selector_map, 0, 1)    
        elif isinstance(parent_group_type, dict) and "multiple" in parent_group_type:
            count = parent_group_type["multiple"]
            return self._process_group(child_name, hierarchy, selector_map, parent_item_index, total_parent_items)    
        else:  # single
            return self._process_group(child_name, hierarchy, selector_map, parent_item_index, total_parent_items)
    

    def _process_group(self, group_name, hierarchy, selector_map, parent_index=0, total_parent_items=1):
        group_info = hierarchy[group_name]
        group_config = group_info["config"]
        group_type = group_config.get("type", "single")
        children = group_info["children"]
        
        group_data = self._process_group_members(group_config, selector_map, group_type, parent_index, total_parent_items)
        
        if children:
            for child_name in children:
                child_data = self._process_child_for_group(child_name, hierarchy, selector_map, group_type, group_data, parent_index, total_parent_items)
                self._add_child_data_to_group(group_data, child_name, child_data, group_type)
        
        return group_data


    def _process_group_members(self, group_config, selector_map, group_type, parent_index, total_parent_items):
        members = group_config.get("members", {})
        
        if group_type == "all":
            return self._process_all_members(members, selector_map)
        elif isinstance(group_type, dict) and "multiple" in group_type:
            count = group_type["multiple"]
            return self._process_multiple_members(members, selector_map, count, parent_index, total_parent_items)
        else:  # single
            return self._process_single_members(members, selector_map, parent_index, total_parent_items)


    def _process_all_members(self, members, selector_map):
        result = {}
        for member, member_cfg in members.items():
            if member in self.first_cyclic_blocks:
                result[member] = self.first_cyclic_blocks[member].copy()
            else:
                member_occurrences = selector_map.get(member, [])
                value_not = member_cfg.get("not")
                if value_not:
                    not_occurrences = self._get_not_texts(value_not, selector_map)
                    mode = member_cfg.get("not_mode", "global")
                    processed = self._apply_not_operation_to_list(member_occurrences, not_occurrences, mode)
                    result[member] = processed
                else:
                    result[member] = member_occurrences

        return result


    def _process_single_members(self, members, selector_map, parent_index, total_parent_items):
        result = {}

        for member, member_cfg in members.items():
            if member in self.first_cyclic_blocks:
                first_block = self.first_cyclic_blocks[member]
                if first_block:
                    position = parent_index % len(first_block)
                    text = first_block[position]
                else:
                    text = None
            else:
                all_texts = selector_map.get(member, [])
                idx = parent_index if parent_index < len(all_texts) else 0
                text = all_texts[idx] if idx < len(all_texts) else None

            value_not = member_cfg.get("not")
            if value_not and text:
                not_texts = self._get_not_texts(value_not, selector_map)
                if not_texts:
                    not_idx = parent_index if parent_index < len(not_texts) else 0
                    if not_idx < len(not_texts):
                        not_text = not_texts[not_idx]
                        if not_text and not_text in text:
                            text = text.replace(not_text, "").strip()

            result[member] = text

        return result


    def _process_multiple_members(self, members, selector_map, count, parent_index, total_parent_items):
        result = {}

        for member, member_cfg in members.items():
            if member in self.first_cyclic_blocks:
                first_block = self.first_cyclic_blocks[member]
                block_values = first_block[:min(count, len(first_block))]

                value_not = member_cfg.get("not")
                if value_not:
                    not_list = self._get_not_texts(value_not, selector_map)
                    cleaned = []
                    for i, val in enumerate(block_values):
                        if val is None:
                            cleaned.append(val)
                            continue
                        if not_list:
                            not_txt = not_list[i % len(not_list)]
                            if not_txt and not_txt in val:
                                val = val.replace(not_txt, "").strip()
                        cleaned.append(val)
                    result[member] = cleaned
                else:
                    result[member] = block_values.copy()
                continue

            all_texts = selector_map.get(member, [])

            value_not = member_cfg.get("not")
            if value_not:
                not_texts_all = self._get_not_texts(value_not, selector_map)
                if not_texts_all and all_texts:
                    mode = member_cfg.get("not_mode", "global")
                    all_texts = self._apply_not_operation_to_list(all_texts, not_texts_all, mode)

            items_per_parent = len(all_texts) // total_parent_items if total_parent_items > 0 else 0
            start_idx = parent_index * items_per_parent
            end_idx = start_idx + count
            block_values = all_texts[start_idx:end_idx] if all_texts else []
            result[member] = block_values

        return result


    def _process_child_for_group(self, child_name, hierarchy, selector_map, parent_group_type, parent_group_data, parent_index, total_parent_items):
        if parent_group_type == "all":
            return self._process_group(child_name, hierarchy, selector_map, 0, 1)     
        elif isinstance(parent_group_type, dict) and "multiple" in parent_group_type:
            count = parent_group_type["multiple"]
            
            if isinstance(parent_group_data, dict):
                for member_value in parent_group_data.values():
                    if isinstance(member_value, list):
                        child_items = []
                        for i in range(len(member_value)):
                            child_item = self._process_group(child_name, hierarchy, selector_map, 
                                                           i, len(member_value))
                            child_items.append(child_item)
                        return child_items
            
            return self._process_group(child_name, hierarchy, selector_map, parent_index, total_parent_items) 
        else:  # single
            return self._process_group(child_name, hierarchy, selector_map, parent_index, total_parent_items)


    def _add_child_data_to_group(self, group_data, child_name, child_data, group_type):
        if group_type == "all":
            group_data[child_name] = child_data      
        elif isinstance(group_type, dict) and "multiple" in group_type:
            group_data[child_name] = child_data       
        else:  # single
            group_data[child_name] = child_data


    def _apply_not_operation_to_list(self, main_texts, remove_texts, mode="global"):
        """
        mode = "position"
                main[i] remove remove_texts[i]

        mode = "global"
            - Remove qualquer substring de remove_texts em todos os itens de main_texts

        mode = "cyclic"
            - Se remove_texts for menor (ex: bloco cíclico),
              aplica remove_texts[i % len(remove_texts)] em main_texts[i]
        """

        if not main_texts or not remove_texts:
            return main_texts

        if mode == "position":
            result = []
            limit = min(len(main_texts), len(remove_texts))

            for i in range(limit):
                main = main_texts[i]
                rem = remove_texts[i]

                if rem and main and rem in main:
                    main = main.replace(rem, "").strip()
                result.append(main)

            if len(main_texts) > limit:
                result.extend(main_texts[limit:])

            return result

        if mode == "global":
            remove_set = set([r for r in remove_texts if r])
            result = []

            for main in main_texts:
                txt = main
                if txt:
                    for rem in remove_set:
                        if rem in txt:
                            txt = txt.replace(rem, "").strip()
                result.append(txt)

            return result

        if mode == "cyclic":
            result = []
            remove_len = len(remove_texts)

            for i, main in enumerate(main_texts):
                txt = main
                rem = remove_texts[i % remove_len]

                if txt and rem and rem in txt:
                    txt = txt.replace(rem, "").strip()

                result.append(txt)

            return result

        return self._apply_not_operation_to_list(main_texts, remove_texts, mode="global")





class ParserEngine:
    def __init__(self, site_cfg):
        self.site_cfg = site_cfg

    async def parse(self, pages_html):
        parser = UniversalParser(self.site_cfg)
        organizer = DataOrganizer(self.site_cfg)

        selector_map = await parser.parse(pages_html)
        result = await organizer.organize(selector_map)

        os.makedirs("debug", exist_ok=True)
        with open("debug/debug_selector_map.json", "w", encoding="utf-8") as json_file:
            json.dump(selector_map, json_file, indent=4)

        return result