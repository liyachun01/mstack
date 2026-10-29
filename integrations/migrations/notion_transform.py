"""Loss-accounted Notion -> AnyBlock transformation, without destination writes.

References remain symbolic until the writer has created every destination object.
Raw Notion responses remain the preservation record for unsupported presentation.
"""
from collections import Counter
import hashlib
import html
import json
import re
from urllib.parse import unquote, urlsplit

from notion_snapshot import title


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()[:20]


def plain(values):
    return "".join(v.get("plain_text", v.get("text", {}).get("content", "")) for v in values)


def escaped(value):
    return re.sub(r"([\\*`\[\]~<])", r"\\\1", value)


class Transform:
    def __init__(self, snapshot):
        self.s = snapshot
        self.assets, self.properties, self.types, self.warnings = {}, {}, {}, []
        self.known = set(snapshot["pages"]) | set(snapshot["databases"]) | set(snapshot["data_sources"])
        self.known_compact = {k.replace("-", ""): k for k in self.known}
        self.property_maps, self.property_ids = {}, {}
        self.rich_links = {}
        self.external_relations = []
        self.schema()

    def ref(self, identity):
        if identity in self.s["databases"]:
            sources = self.database_sources(identity)
            if len(sources) == 1:
                identity = sources[0]["id"]
        return "notion:" + identity

    def database_sources(self, identity):
        sources = {v["id"]: v for v in self.s["databases"][identity].get("data_sources", [])}
        for view in self.s["views"].values():
            if view["parent"].get("database_id") == identity:
                sources.setdefault(view["data_source_id"], {"id": view["data_source_id"]})
        return list(sources.values())

    def url(self, value):
        if not value:
            return value
        parsed = urlsplit(value)
        if parsed.hostname and (parsed.hostname in ("notion.so", "www.notion.so", "app.notion.com") or parsed.hostname.endswith(".notion.site")):
            matches = re.findall(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", parsed.path)
            if matches:
                key = matches[-1].replace("-", "").lower()
                if key in self.known_compact:
                    return "anytype://object?objectId=" + self.ref(self.known_compact[key])
        return value

    def rich(self, values):
        # Markdown delimiters cannot enclose trailing whitespace. Coalesce equal
        # neighbouring annotations so adjacent bold spans do not become ****.
        spans = []
        for original in values:
            v = dict(original)
            raw = v.get("plain_text", v.get("text", {}).get("content", ""))
            key = (v.get("type", "text"), json.dumps(v.get("annotations", {}), sort_keys=True),
                   v.get("href") or (v.get("text", {}).get("link") or {}).get("url"))
            if spans and key == spans[-1][0] and key[0] == "text":
                spans[-1][1]["plain_text"] += raw
            else:
                v["plain_text"] = raw
                spans.append((key, v))
        result, previous_annotations = [], {}
        for _, v in spans:
            t = v.get("type", "text")
            raw = v.get("plain_text", v.get("text", {}).get("content", ""))
            leading, core, trailing = re.fullmatch(r"(\s*)(.*?)(\s*)", raw, re.S).groups()
            text = escaped(core)
            target = v.get("href") or (v.get("text", {}).get("link") or {}).get("url")
            if t == "mention":
                mention = v["mention"]
                kind = mention.get("type")
                if kind in ("page", "database"):
                    identity = mention[kind]["id"]
                    target = "anytype://object?objectId=" + self.ref(identity) if identity in self.known else "https://www.notion.so/" + identity.replace("-", "")
            elif t == "equation":
                text = escaped(v["equation"].get("expression", raw))
                self.warnings.append({"kind": "inline-equation-as-source-text"})
            ann = v.get("annotations", {})
            if ann.get("code"):
                delimiter = "`" * (max([len(m) for m in re.findall(r"`+", core)] or [0]) + 1)
                text = delimiter + core + delimiter
            if ann.get("bold"):
                text = "**" + text + "**"
            if ann.get("italic"):
                text = "*" + text + "*"
            if ann.get("strikethrough"):
                text = "~~" + text + "~~"
            if ann.get("underline"):
                text = "<u>" + text + "</u>"
            color = ann.get("color", "default")
            if color != "default":
                attr = "background" if color.endswith("_background") else "color"
                text = '<font ' + attr + '="' + color.removesuffix("_background") + '">' + text + "</font>"
            if target:
                text = "[" + text + "](" + self.url(target) + ")"
            piece = leading + text + trailing if core else raw
            if (result and ann.get("bold") and previous_annotations.get("bold") and
                    not ann.get("italic") and not previous_annotations.get("italic") and
                    result[-1].endswith("**") and piece.startswith("**")):
                result[-1] = result[-1][:-2] + piece[2:]
            else:
                result.append(piece)
            previous_annotations = ann
        return "".join(result)

    def asset(self, value, fallback_name="attachment"):
        t = value.get("type")
        if t not in ("file", "external"):
            raise ValueError("Unknown source file representation")
        url = value[t]["url"]
        parsed = urlsplit(url)
        identity = digest(parsed.scheme + "://" + parsed.netloc + parsed.path)
        name = value.get("name") or unquote(parsed.path.rsplit("/", 1)[-1]) or fallback_name
        self.assets[identity] = {"url": url, "name": name, "source_file_type": t}
        return "asset:" + identity

    def icon(self, source):
        if not source:
            return None
        t = source.get("type")
        if t == "emoji":
            return {"format": "emoji", "emoji": source["emoji"]}
        if t in ("file", "external"):
            return {"format": "file", "file": self.asset(source, "icon")}
        if t == "custom_emoji":
            return {"format": "file", "file": self.asset({"type": "external", "external": {"url": source[t]["url"]}}, "icon")}
        self.warnings.append({"kind": "named-icon-not-portable", "source_icon": source.get(t)})
        return None

    def schema(self):
        # Explicit keys keep identically named fields of different tables distinct.
        formats = {"rich_text": "text", "number": "number", "select": "select", "multi_select": "multi_select",
                   "status": "select", "date": "date", "checkbox": "checkbox", "relation": "objects",
                   "files": "files", "url": "url", "email": "email", "phone_number": "phone",
                   "created_time": "date", "last_edited_time": "date", "people": "text"}
        for source_id, source in self.s["data_sources"].items():
            names, ids, definitions = {}, {}, []
            for name, prop in source.get("properties", {}).items():
                if prop["type"] == "title":
                    key = "name"
                else:
                    key = "ntn_" + digest(source_id + ":" + prop["id"])
                    fmt = formats.get(prop["type"], "text")
                    if prop["type"] == "formula":
                        examples = [self.s["pages"][i].get("properties", {}).get(name, {}).get("formula", {}) for i in self.s["rows"].get(source_id, []) if i in self.s["pages"]]
                        kinds = {v.get("type") for v in examples if v.get(v.get("type")) is not None}
                        if len(kinds) == 1:
                            fmt = {"number": "number", "boolean": "checkbox", "date": "date"}.get(next(iter(kinds)), "text")
                    body = {"key": key, "name": name, "format": fmt}
                    if prop["type"] in ("select", "multi_select", "status"):
                        body["options"] = [{"name": o["name"], **({"color": "grey" if o.get("color") in ("gray", "default") else "orange" if o.get("color") == "brown" else o["color"]} if o.get("color") else {})}
                                           for o in prop[prop["type"]].get("options", [])]
                    self.properties[key] = body
                    definitions.append({"property": key, "section": "featured"})
                names[name], ids[unquote(prop["id"])] = key, key
            self.property_maps[source_id], self.property_ids[source_id] = names, ids
            type_key = "ntn_" + digest(source_id)
            self.types[type_key] = {"api_key": type_key, "name": title(source) or "Untitled", "plural_name": title(source) or "Untitled",
                                    "layout": "basic", "property_definitions": definitions}
            icon = self.icon(source.get("icon"))
            if icon and icon["format"] == "emoji":
                self.types[type_key]["icon"] = icon
        for key, name, fmt in [("notion_source_id", "Notion ID", "text"), ("notion_created_at", "Notion created at", "date"),
                               ("notion_edited_at", "Notion edited at", "date"), ("notion_parent", "Parent", "objects")]:
            self.properties[key] = {"key": key, "name": name, "format": fmt}

    def page_properties(self, identity, page):
        result = {"name": title(page), "source": page.get("url") or "https://www.notion.so/" + identity.replace("-", ""),
                  "notion_source_id": identity, "notion_created_at": page["created_time"], "notion_edited_at": page["last_edited_time"]}
        parent = page["parent"]
        source_id = parent.get("data_source_id")
        parent_id = source_id or parent.get("page_id") or parent.get("block_id")
        if parent_id in self.known:
            result["notion_parent"] = [self.ref(parent_id)]
        if source_id not in self.property_maps:
            return result
        for name, prop in page.get("properties", {}).items():
            t, key = prop["type"], self.property_maps[source_id].get(name)
            if t == "title" or not key:
                continue
            value = prop.get(t)
            if t == "rich_text":
                result[key] = plain(value)
            elif t in ("select", "status"):
                result[key] = [value["name"]] if value else []
            elif t == "multi_select":
                result[key] = [v["name"] for v in value]
            elif t == "relation":
                items = self.s["property_items"].get(identity + ":" + name)
                if isinstance(items, list):
                    value = [v["relation"] for v in items if v.get("type") == "relation"]
                inside = [self.ref(v["id"]) for v in value if v["id"] in self.known]
                outside = [v["id"] for v in value if v["id"] not in self.known]
                result[key] = inside
                if outside:
                    self.external_relations.append({"page": identity, "property": name, "targets": outside})
            elif t == "date":
                result[key] = value["start"] if value else None
                if value and value.get("end"):
                    end_key = key + "_end"
                    self.properties[end_key] = {"key": end_key, "name": name + " (end)", "format": "date"}
                    result[end_key] = value["end"]
                    self.warnings.append({"kind": "date-range-split", "page": identity, "property": name})
            elif t == "people":
                result[key] = ", ".join(v.get("name") or v["id"] for v in value)
                if value:
                    self.warnings.append({"kind": "notion-person-preserved-as-text", "page": identity, "property": name})
            elif t == "files":
                result[key] = [self.asset(v) for v in value]
            elif t == "formula":
                kind = value.get("type")
                calculated = value.get(kind)
                result[key] = calculated.get("start") if kind == "date" and calculated else calculated
                self.warnings.append({"kind": "formula-snapshot", "page": identity, "property": name})
            elif t in ("checkbox", "number", "url", "email", "phone_number", "created_time", "last_edited_time"):
                result[key] = value
            else:
                result[key] = json.dumps(value, ensure_ascii=False)
                self.warnings.append({"kind": "property-as-source-text", "page": identity, "property": name, "type": t})
        return result

    def property_key(self, source_id, key):
        return self.property_maps[source_id].get(key) or self.property_ids[source_id].get(unquote(key))

    def filter(self, source_id, value):
        if "and" in value or "or" in value:
            operator = "and" if "and" in value else "or"
            return {"operator": operator, "filters": [self.filter(source_id, v) for v in value[operator]]}
        property_name = self.property_key(source_id, value["property"])
        if not property_name:
            raise ValueError("View filter names an unavailable property: " + value["property"])
        t = next(k for k in value if k != "property")
        condition, raw = next(iter(value[t].items()))
        equivalents = {"equals": "equal", "does_not_equal": "not_equal", "contains": "contains", "does_not_contain": "not_contains",
                       "is_empty": "empty", "is_not_empty": "not_empty", "greater_than": "greater", "less_than": "less",
                       "greater_than_or_equal_to": "greater_or_equal", "less_than_or_equal_to": "less_or_equal",
                       "before": "less", "after": "greater", "on_or_before": "less_or_equal", "on_or_after": "greater_or_equal"}
        if condition not in equivalents:
            raise ValueError("Unsupported saved-view filter: " + condition)
        converted = {"property": property_name, "condition": equivalents[condition]}
        if t in ("select", "multi_select", "status") and condition not in ("is_empty", "is_not_empty"):
            source_prop = next(p for p in self.s["data_sources"][source_id]["properties"].values() if self.property_key(source_id, p["id"]) == property_name)
            options = source_prop[source_prop["type"]].get("options", [])
            option_names = {o["id"]: o["name"] for o in options}
            groups = {g["name"]: [option_names[i] for i in g["option_ids"]] for g in source_prop[source_prop["type"]].get("groups", [])}
            source_values = raw if isinstance(raw, list) else [raw]
            names = []
            for v in source_values:
                names.extend(groups[v] if v in groups else [option_names.get(v, v)])
            converted["condition"] = "not_in" if condition in ("does_not_equal", "does_not_contain") else "in"
            converted["value"] = names
        elif condition not in ("is_empty", "is_not_empty"):
            if t == "date" and raw in ("today", "tomorrow", "yesterday"):
                converted["date_preset"] = raw
            else:
                converted["value"] = raw
        return converted

    def views(self, source_id, database_id=None):
        result = []
        for view in self.s["views"].values():
            if view["data_source_id"] != source_id or (database_id and view["parent"].get("database_id") != database_id):
                continue
            conf = view.get("configuration", {})
            view_type = {"board": "kanban", "timeline": "calendar"}.get(view["type"], view["type"])
            if view["type"] == "timeline":
                self.warnings.append({"kind": "timeline-rendered-as-calendar", "view": view["id"]})
            converted = {"name": view.get("name") or "Untitled", "type": view_type, "columns": []}
            for col in conf.get("properties", []):
                key = self.property_key(source_id, col.get("property_name") or col["property_id"])
                if not key:
                    self.warnings.append({"kind": "stale-view-column", "view": view["id"], "property_id": col["property_id"]})
                    continue
                converted["columns"].append({"property": key, "hidden": not col.get("visible", True), **({"width": round(col["width"])} if col.get("width") else {})})
            sorts = []
            for sort in view.get("sorts") or []:
                key = self.property_key(source_id, sort["property"])
                if key:
                    sorts.append({"property": key, "direction": "asc" if sort["direction"] == "ascending" else "desc"})
                else:
                    self.warnings.append({"kind": "stale-view-sort", "view": view["id"]})
            converted["sorts"] = sorts
            filters = []
            if view.get("filter"):
                filters.append(self.filter(source_id, view["filter"]))
            for prop, condition in (view.get("quick_filters") or {}).items():
                filters.append(self.filter(source_id, {"property": prop, **condition}))
            converted["filters"] = filters
            if conf.get("group_by"):
                converted["group_by"] = self.property_key(source_id, conf["group_by"]["property_id"])
            if conf.get("date_property_id"):
                date_key = self.property_key(source_id, conf["date_property_id"])
                converted["group_by"] = date_key
                if any(self.property_maps[source_id].get(name) == date_key and prop.get("type") == "date" and
                       prop.get("date") and prop["date"].get("end") for page_id in self.s["rows"].get(source_id, [])
                       for name, prop in self.s["pages"][page_id].get("properties", {}).items()):
                    converted["end_property"] = date_key + "_end"
            if conf.get("wrap_cells"):
                converted["wrap_content"] = True
            result.append(converted)
        return result or [{"name": "All", "type": "table", "columns": [{"property": k} for k in self.property_maps[source_id].values()], "sorts": [], "filters": []}]

    def blocks(self, parent, indent=0):
        if indent > 32:
            raise ValueError("Source nesting exceeds Anytype's limit")
        result = []
        for identity in self.s["children"].get(parent, []):
            block = self.s["blocks"][identity]
            t, source = block["type"], block[block["type"]]
            converted = {"type": t, "indent": indent}
            if t in ("paragraph", "heading_1", "heading_2", "heading_3", "quote", "toggle", "bulleted_list_item", "numbered_list_item", "to_do", "callout", "code"):
                converted["text"] = plain(source.get("rich_text", [])) if t == "code" else self.rich(source.get("rich_text", []))
                if t == "to_do":
                    converted.update(type="checkbox", checked=source["checked"])
                if t == "code":
                    converted["language"] = source.get("language", "plain text")
                if t.startswith("heading_") and source.get("is_toggleable"):
                    converted["type"] = "toggle_" + t
                if source.get("color", "default") != "default":
                    color = source["color"]
                    converted["background_color" if color.endswith("_background") else "color"] = color.removesuffix("_background")
                if t == "callout":
                    icon = self.icon(source.get("icon"))
                    if icon:
                        converted["icon"] = icon
            elif t == "child_page":
                converted.update(type="link", object_id=self.ref(identity))
            elif t == "child_database":
                sources = self.database_sources(identity)
                for item in sources:
                    result.append({"type": "dataview", "indent": indent, "object_id": self.ref(item["id"]), "_views": self.views(item["id"], identity)})
                if not sources:
                    self.warnings.append({"kind": "database-without-data-source", "block": identity})
                continue
            elif t == "column_list":
                converted["type"] = "row"
            elif t == "column":
                if source.get("width_ratio"):
                    self.warnings.append({"kind": "column-width-ratio-not-authorable", "block": identity, "ratio": source["width_ratio"]})
            elif t == "table":
                converted["columns"] = [{} for _ in range(source["table_width"])]
                rows = []
                for i, row_id in enumerate(self.s["children"].get(identity, [])):
                    row = self.s["blocks"][row_id]["table_row"]
                    cells = [self.rich(v) for v in row["cells"]]
                    if source.get("has_row_header") and cells:
                        cells[0] = "**" + cells[0] + "**"
                    rows.append({"cells": cells, "is_header": bool(i == 0 and source.get("has_column_header"))})
                converted["rows"] = rows
            elif t in ("image", "file", "video", "audio", "pdf"):
                if not source.get(source.get("type"), {}).get("url"):
                    source_page = block["parent"].get("page_id", parent)
                    converted.update(type="paragraph", text="[Original Notion attachment](https://www.notion.so/" + source_page.replace("-", "") + "#" + identity.replace("-", "") + ")")
                    result.append(converted)
                    self.warnings.append({"kind": "source-attachment-unavailable", "block": identity, "page": source_page})
                    continue
                converted["object_id"] = self.asset(source, t)
                if t == "file" and self.assets[converted["object_id"].split(":")[1]]["name"].lower().endswith(".pdf"):
                    converted["type"] = "pdf"
            elif t in ("bookmark", "link_preview"):
                if source.get("url"):
                    converted.update(type="bookmark", url=self.url(source["url"]))
                else:
                    source_page = block["parent"].get("page_id", parent)
                    converted.update(type="paragraph", text="[Original Notion preview](https://www.notion.so/" + source_page.replace("-", "") + "#" + identity.replace("-", "") + ")")
                    self.warnings.append({"kind": "source-preview-unavailable", "block": identity, "page": source_page})
            elif t == "link_to_page":
                target = source.get(source.get("type"))
                if target in self.known:
                    converted.update(type="link", object_id=self.ref(target))
                else:
                    converted.update(type="paragraph", text="[Original Notion page](https://www.notion.so/" + (target or identity).replace("-", "") + ")")
                    self.warnings.append({"kind": "external-page-link", "block": identity, "target": target})
            elif t in ("divider", "table_of_contents"):
                pass
            elif t == "equation":
                converted.update(type="equation", processor="latex", text=source["expression"])
            elif t == "synced_block":
                synced = source.get("synced_from")
                result.extend(self.blocks(synced["block_id"] if synced else identity, indent))
                continue
            elif t in ("unsupported", "embed", "breadcrumb"):
                source_page = block["parent"].get("page_id", parent)
                url = source.get("url") or "https://www.notion.so/" + source_page.replace("-", "") + "#" + identity.replace("-", "")
                label = "Original Notion attachment" if source.get("block_type") == "alias" else "Original Notion content"
                converted.update(type="paragraph", text="[" + label + "](" + url + ")")
                self.warnings.append({"kind": "source-block-unavailable", "block": identity, "type": source.get("block_type", t), "page": source_page})
            else:
                raise ValueError("Unmapped source block type: " + t)
            result.append(converted)
            if t not in ("child_page", "child_database", "table") and block.get("has_children"):
                result.extend(self.blocks(identity, indent + 1))
            caption = source.get("caption")
            if caption:
                result.append({"type": "paragraph", "indent": indent, "text": self.rich(caption)})
        return result

    def build(self):
        pages, collections = {}, {}
        for identity, page in self.s["pages"].items():
            source_id = page["parent"].get("data_source_id")
            typ = "ntn_" + digest(source_id) if source_id in self.s["data_sources"] else "page"
            obj = {"formatVersion": "2.0", "type": typ, "template": "none", "properties": self.page_properties(identity, page), "blocks": self.blocks(identity)}
            icon = self.icon(page.get("icon"))
            if icon:
                obj["icon"] = icon
            if page.get("cover"):
                obj["cover"] = {"format": "image", "file": self.asset(page["cover"], "cover")}
            # Anytype text properties have no portable per-span formatting.
            # Keep their cell text and render formatted/linked spans in the page.
            rich_properties = [(name, prop["rich_text"]) for name, prop in page.get("properties", {}).items()
                               if prop.get("type") == "rich_text" and any(v.get("type") != "text" or v.get("href") or
                                  any(val for key, val in v.get("annotations", {}).items() if key != "color") or
                                  v.get("annotations", {}).get("color", "default") != "default" for v in prop["rich_text"])]
            if rich_properties:
                obj["blocks"].append({"type": "divider", "indent": 0})
                for name, values in rich_properties:
                    obj["blocks"].extend([{"type": "heading_3", "indent": 0, "text": escaped(name)},
                                          {"type": "paragraph", "indent": 0, "text": self.rich(values)}])
                self.warnings.append({"kind": "formatted-property-also-rendered-in-body", "page": identity, "properties": [name for name, _ in rich_properties]})
            pages[identity] = obj
        for identity, source in self.s["data_sources"].items():
            collections[identity] = {"formatVersion": "2.0", "type": "collection", "template": "none",
                                     "properties": {"name": title(source), "notion_source_id": identity, "source": source.get("url", "")},
                                     "collection_items": [self.ref(v) for v in self.s["rows"].get(identity, [])],
                                     "blocks": [{"type": "dataview", "is_collection": True, "views": self.views(identity)}]}
            icon = self.icon(source.get("icon"))
            if icon:
                collections[identity]["icon"] = icon
        return {"version": 1, "source_completed_at": self.s.get("completed_at"), "source_errors": self.s["errors"],
                "pages": pages, "collections": collections, "properties": self.properties, "types": self.types,
                "assets": self.assets, "warnings": self.warnings, "external_relations": self.external_relations,
                "source_counts": {k: len(self.s[k]) for k in ("pages", "databases", "data_sources", "blocks", "views")},
                "warning_counts": Counter(w["kind"] for w in self.warnings)}
