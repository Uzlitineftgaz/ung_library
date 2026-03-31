import os
import re
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set

ROOT_DIR = r"F:\kutubxona\ung_library\booklore-api"
SRC_DIR = os.path.join(ROOT_DIR, "src", "main", "java")
CONTROLLERS_DIR = os.path.join(SRC_DIR, "org", "booklore", "controller")

OUTPUT_COLLECTION = os.path.join(ROOT_DIR, "postman_collection.json")
OUTPUT_ENV = os.path.join(ROOT_DIR, "postman_environment.json")


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def list_java_files(root: str) -> List[str]:
    out: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".java"):
                out.append(os.path.join(dirpath, fn))
    return out


def build_type_index(java_files: List[str]) -> Dict[str, str]:
    """
    Map simple type name -> source file path.
    We only index class/record/enum definitions.
    """
    index: Dict[str, str] = {}
    type_def_re = re.compile(r"\b(class|record|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    for p in java_files:
        try:
            txt = read_text(p)
        except UnicodeDecodeError:
            continue
        m = type_def_re.search(txt)
        if m:
            name = m.group(2)
            # Keep the first occurrence to avoid ambiguity.
            if name not in index:
                index[name] = p
    return index


PRIMITIVE_EXAMPLES: Dict[str, Any] = {
    "String": "string",
    "CharSequence": "string",
    "UUID": "00000000-0000-0000-0000-000000000000",
    "Long": 1,
    "long": 1,
    "Integer": 1,
    "int": 1,
    "Short": 1,
    "short": 1,
    "Byte": 1,
    "byte": 1,
    "Double": 1.0,
    "double": 1.0,
    "Float": 1.0,
    "float": 1.0,
    "Boolean": True,
    "boolean": True,
    "BigDecimal": 1.0,
    "byte[]": "<base64>",
}


def sanitize_var_key(key: str) -> str:
    # Postman variable keys are usually simple; keep it safe.
    key = key.strip()
    # Sometimes annotation parsers may capture literal quotes.
    key = key.strip('"').strip("'")
    key = re.sub(r"[^A-Za-z0-9_]+", "_", key)
    if re.match(r"^[0-9]", key):
        key = "v_" + key
    return key


def split_top_level_commas(s: str) -> List[str]:
    """
    Split by commas not inside <...> and not inside (...).
    Useful for parsing Java generic types and parameter lists,
    especially when annotations like @RequestParam(value=..., required=...) contain commas.
    """
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    paren_depth = 0
    in_str = False
    str_char = ""
    for ch in s:
        if in_str:
            buf.append(ch)
            if ch == str_char:
                in_str = False
            continue
        if ch in ("'", '"'):
            in_str = True
            str_char = ch
            buf.append(ch)
            continue
        if ch == "<":
            depth += 1
            buf.append(ch)
            continue
        if ch == ">":
            depth = max(0, depth - 1)
            buf.append(ch)
            continue
        if ch == "(":
            paren_depth += 1
            buf.append(ch)
            continue
        if ch == ")":
            paren_depth = max(0, paren_depth - 1)
            buf.append(ch)
            continue
        if ch == "," and depth == 0 and paren_depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            continue
        buf.append(ch)
    last = "".join(buf).strip()
    if last:
        parts.append(last)
    return parts


def extract_class_base_path(controller_text: str) -> str:
    # Find first @RequestMapping at class-level (heuristic).
    # Examples:
    # @RequestMapping("/api/v1/version")
    # @RequestMapping(("/api/v1/shelves"))
    # @RequestMapping("/api/v1/books/{bookId}/files")
    m = re.search(r"@RequestMapping\s*(?:\(\s*)?[\(\s]*[\"']([^\"']+)[\"']", controller_text)
    if m:
        return m.group(1)
    return ""


def extract_tag(controller_text: str) -> Optional[str]:
    m = re.search(r"@Tag\s*\(\s*name\s*=\s*[\"']([^\"']+)[\"']", controller_text)
    if m:
        return m.group(1).strip()
    return None


def find_enclosing_preauthorize(method_block: str) -> Optional[str]:
    """
    Look for @PreAuthorize("...") in method block (heuristic).
    """
    m = re.search(r"@PreAuthorize\s*\(\s*[\"']([^\"']+)[\"']\s*\)", method_block)
    if m:
        return m.group(1).strip()
    return None


def find_mapping_consumes(mapping_chunk: str) -> Optional[str]:
    m = re.search(r'consumes\s*=\s*["\']([^"\']+)["\']', mapping_chunk)
    if m:
        return m.group(1).strip()
    return None


def find_mapping_paths(mapping_chunk: str) -> List[str]:
    # Extract first quoted path string(s). Most controllers have one.
    # Examples:
    # @GetMapping("/notification")
    # @GetMapping("/{fileId}/download")
    # @PostMapping(value = "/upload/bookdrop", consumes = "multipart/form-data")
    strings = re.findall(r'["\']([^"\']+)["\']', mapping_chunk)
    # In @GetMapping(params="x"), the strings list includes params too; keep only likely path strings starting with "/" or empty.
    paths = [s for s in strings if s.startswith("/")]
    return paths


def parse_mapping_method(annotation_name: str) -> str:
    return {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
    }.get(annotation_name, "GET")


def matching_parentheses_end(text: str, start_idx: int) -> int:
    """
    Return index of matching ')' for '(' at start_idx.
    """
    depth = 0
    in_str = False
    str_char = ""
    for i in range(start_idx, len(text)):
        ch = text[i]
        if in_str:
            if ch == str_char:
                in_str = False
            continue
        if ch in ("'", '"'):
            in_str = True
            str_char = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def parse_method_signature(signature_chunk: str) -> Tuple[Optional[str], List[str], Optional[str]]:
    """
    Returns (method_name, params_texts, return_type_text).
    signature_chunk should start at 'public' and end before '{'.
    """
    # Grab method name and params
    m = re.search(r"\bpublic\b\s+(?P<ret>.+?)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", signature_chunk, flags=re.S)
    if not m:
        # Some controllers use 'public ResponseEntity<?> foo(' still covered.
        return None, [], None
    method_name = m.group("name")
    return_type = m.group("ret").strip()
    # params block
    paren_start = signature_chunk.find("(", m.start("name"))
    if paren_start == -1:
        return method_name, [], return_type
    paren_end = matching_parentheses_end(signature_chunk, paren_start)
    if paren_end == -1:
        return method_name, [], return_type
    params_text = signature_chunk[paren_start + 1:paren_end].strip()
    params = []
    if params_text:
        params = split_top_level_commas(params_text)
    return method_name, params, return_type


def remove_annotations_and_modifiers(param_decl: str) -> str:
    # Remove annotations like @RequestParam("x"), @Valid, @Parameter(...)
    decl = re.sub(r"@\w+(?:\s*\([^)]*\))?\s*", "", param_decl)
    decl = decl.replace("final ", "")
    decl = decl.replace("volatile ", "")
    decl = decl.strip()
    return decl


def parse_param_decl(param_decl: str) -> Dict[str, Any]:
    """
    Output:
    {
      "annotations": { "RequestBody": True, "PathVariable": {"name":...}, ... },
      "type": "Long" or "Map<String,String>" etc,
      "name": "id" etc,
    }
    """
    out: Dict[str, Any] = {"raw": param_decl, "annotations": {}}

    # RequestBody
    if "@RequestBody" in param_decl:
        out["annotations"]["RequestBody"] = True
    # MultipartFile / file
    if "MultipartFile" in param_decl:
        out["annotations"]["MultipartFile"] = True

    # PathVariable
    m = re.search(r"@PathVariable(?:\s*\(\s*[\"']([^\"']+)[\"']\s*\))?", param_decl)
    if m:
        out["annotations"]["PathVariable"] = {"name": m.group(1) if m.group(1) else None}

    # RequestParam
    m = re.search(r"@RequestParam(?:\s*\(\s*[\"']([^\"']+)[\"']\s*\))?", param_decl)
    if m:
        out["annotations"]["RequestParam"] = {"name": m.group(1) if m.group(1) else None}

    # RequestHeader
    m = re.search(r"@RequestHeader(?:\s*\(\s*[\"']([^\"']+)[\"']\s*\))?", param_decl)
    if m:
        out["annotations"]["RequestHeader"] = {"name": m.group(1) if m.group(1) else None}

    # Determine type & name
    clean = remove_annotations_and_modifiers(param_decl)
    # clean could contain things like "long pathId" or "Pageable pageable"
    # Get last token as name
    parts = clean.split()
    if len(parts) >= 2:
        out["name"] = parts[-1]
        out["type"] = " ".join(parts[:-1])
    else:
        out["name"] = None
        out["type"] = clean
    return out


def extract_preferred_dto_fields(dto_text: str, dto_type_name: str) -> List[Tuple[str, str]]:
    """
    Return list of (fieldType, fieldName).
    Depth is handled later.
    """
    fields: List[Tuple[str, str]] = []

    # record: record X(String a, int b) { }
    m = re.search(rf"\brecord\s+{re.escape(dto_type_name)}\s*\(([^)]*)\)", dto_text)
    if m:
        comps = m.group(1)
        for comp in split_top_level_commas(comps):
            comp = comp.strip()
            if not comp:
                continue
            tokens = comp.split()
            if len(tokens) >= 2:
                f_name = tokens[-1]
                f_type = " ".join(tokens[:-1])
                fields.append((f_type.strip(), f_name.strip()))
        return fields

    # Lombok/POJO: private Type field;
    # Also handle private final Type field;
    for fm in re.finditer(r"\bprivate\s+(?:final\s+)?([^;=]+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*[;=]", dto_text):
        f_type = fm.group(1).strip()
        f_name = fm.group(2).strip()
        fields.append((f_type, f_name))

    return fields


def parse_enum_constants(enum_text: str, enum_type_name: str) -> List[str]:
    m = re.search(rf"\benum\s+{re.escape(enum_type_name)}\b[^\{{]*\{{(.*?)\}}", enum_text, flags=re.S)
    if not m:
        return []
    body = m.group(1)
    # Take constants until ';' if present
    before = body.split(";", 1)[0]
    # Remove comments and whitespace
    before = re.sub(r"//.*?$|/\*.*?\*/", "", before, flags=re.M | re.S)
    # Split by commas
    candidates = [c.strip() for c in before.split(",") if c.strip()]
    # Remove possible constructor args fragments like A(1)
    cleaned: List[str] = []
    for c in candidates:
        cleaned.append(c.split("(", 1)[0].strip())
    return [c for c in cleaned if c]


def example_for_type(type_text: str, type_index: Dict[str, str], depth: int, visited: Set[str]) -> Any:
    type_text = type_text.strip()
    if not type_text or type_text == "void":
        return None

    if depth <= 0:
        return {}

    # Normalize whitespace
    type_text = re.sub(r"\s+", "", type_text)

    # Handle generic containers
    m = re.match(r"^(List|Set|Collection|Page)<(.+)>$", type_text)
    if m:
        inner = m.group(2)
        return [example_for_type(inner, type_index, depth - 1, visited)]

    m = re.match(r"^Map<([^,]+),(.+)>$", type_text)
    if m:
        return {}

    m = re.match(r"^Optional<(.+)>$", type_text)
    if m:
        return example_for_type(m.group(1), type_index, depth - 1, visited)

    # Arrays
    if type_text.endswith("[]"):
        inner = type_text[:-2]
        return [example_for_type(inner, type_index, depth - 1, visited)]

    # Primitives / known types
    if type_text in PRIMITIVE_EXAMPLES:
        return PRIMITIVE_EXAMPLES[type_text]

    # Some DTO types might come with wildcards.
    type_text = type_text.replace("?", "")

    # Avoid cycles by type name
    simple = type_text
    simple = re.sub(r"<.*>", "", simple)
    simple = simple.split(".")[-1]
    if simple in visited:
        return {}
    visited.add(simple)

    if simple in type_index:
        src = type_index[simple]
        try:
            txt = read_text(src)
        except Exception:
            return {}

        # Enum?
        if re.search(rf"\benum\s+{re.escape(simple)}\b", txt):
            enums = parse_enum_constants(txt, simple)
            return enums[0] if enums else simple

        # Record/class fields
        fields = extract_preferred_dto_fields(txt, simple)
        if not fields:
            return {}

        obj: Dict[str, Any] = {}
        for f_type, f_name in fields[:25]:
            obj[f_name] = example_for_type(f_type, type_index, depth - 1, visited)
        return obj

    return {}


def type_is_multipart(request_consumes: Optional[str], method_params: List[Dict[str, Any]]) -> bool:
    if request_consumes and "multipart/form-data" in request_consumes:
        return True
    for p in method_params:
        if p.get("annotations", {}).get("MultipartFile"):
            return True
    return False


def example_value_for_query(type_text: str) -> str:
    type_text = re.sub(r"\s+", "", type_text)
    if type_text in ("long", "Long", "int", "Integer", "short", "Short", "byte", "Byte"):
        return "1"
    if type_text in ("double", "Double", "float", "Float", "BigDecimal"):
        return "1.0"
    if type_text in ("boolean", "Boolean"):
        return "true"
    if type_text.startswith("List") or type_text.startswith("Set") or type_text.startswith("Collection"):
        return "[]"
    return ""


def replace_path_vars_with_postman_vars(path: str, var_names: Set[str]) -> str:
    # Replace {var} -> {{var}}
    out = path
    for vn in var_names:
        out = out.replace("{" + vn + "}", "{{" + vn + "}}")
    return out


def parse_controller_methods(
    controller_path: str,
    class_base: str,
    type_index: Dict[str, str],
    controller_name: str,
) -> List[Dict[str, Any]]:
    controller_text = read_text(controller_path)
    tag = extract_tag(controller_text)

    # Find mapping annotations
    # Handle @GetMapping(...), @PostMapping(...), etc
    mapping_re = re.compile(r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*(\((?:[^()]|\([^()]*\))*\))?", flags=re.S)

    # For each mapping annotation, we locate the next method signature.
    methods: List[Dict[str, Any]] = []
    for mm in mapping_re.finditer(controller_text):
        mapping_name = mm.group(1)
        mapping_args = mm.group(2) or ""
        mapping_chunk = mapping_name + mapping_args

        http_method = parse_mapping_method(mapping_name)
        mapping_paths = find_mapping_paths(mapping_chunk)
        consumes = find_mapping_consumes(mapping_chunk)

        # Find the next 'public ... {' after this mapping
        after = controller_text[mm.end():]
        # locate signature start
        sig_match = re.search(r"\bpublic\b[\s\S]{0,2000}\{", after)
        if not sig_match:
            continue
        sig_start_in_after = sig_match.start()
        sig_end_in_after = sig_match.end()
        sig_chunk = after[sig_start_in_after:sig_end_in_after]

        # Strip method body by taking up to first '{'
        brace_idx = sig_chunk.find("{")
        signature_chunk = sig_chunk[:brace_idx].strip()

        # Parse preauthorize within a window around this mapping.
        # Some controllers place @PreAuthorize *before* @GetMapping/@PostMapping.
        window_start = max(0, mm.start() - 800)
        window_end = mm.end() + sig_start_in_after + 800
        method_window = controller_text[window_start:window_end]
        preauthorize = find_enclosing_preauthorize(method_window)

        method_name, params_text, return_type = parse_method_signature(signature_chunk)
        if not method_name:
            continue

        param_decls: List[Dict[str, Any]] = []
        for ptxt in params_text:
            param_decls.append(parse_param_decl(ptxt))

        # Determine request body DTO
        request_body_param = None
        for p in param_decls:
            if p.get("annotations", {}).get("RequestBody"):
                request_body_param = p
                break

        # Determine path variables and query params / headers
        path_vars: Set[str] = set()
        query_params: List[Dict[str, Any]] = []
        headers: List[Dict[str, Any]] = []

        for p in param_decls:
            ann = p.get("annotations", {})
            pname = p.get("name")
            ptype = p.get("type", "")
            if ann.get("PathVariable"):
                key = pname
                out_name = ann["PathVariable"]["name"] or key
                path_vars.add(out_name)
            if ann.get("RequestParam"):
                qn = ann["RequestParam"]["name"] or pname
                query_params.append({"name": qn, "type": ptype})
            if ann.get("RequestHeader"):
                hn = ann["RequestHeader"]["name"] or pname
                headers.append({"name": hn, "type": ptype})

        # Add Pageable as typical query params if present
        if any(p.get("type", "").strip() == "Pageable" for p in param_decls):
            query_params.append({"name": "page", "type": "int"})
            query_params.append({"name": "size", "type": "int"})

        # Compose full path; if mapping_paths empty => base path unchanged
        method_path = mapping_paths[0] if mapping_paths else ""
        full_path = (class_base.rstrip("/") + "/" + method_path.lstrip("/")).replace("//", "/")
        if not mapping_paths:
            full_path = class_base

        # Some controllers might have @GetMapping with params only; mapping_paths empty => use base path
        # Keep query param info from @RequestParam.

        body_mode = None
        body_raw = None
        formdata = None
        is_multipart = type_is_multipart(consumes, param_decls)

        if request_body_param and not is_multipart:
            body_type = request_body_param.get("type", "")
            example = example_for_type(body_type, type_index, depth=2, visited=set())
            body_raw = json.dumps(example if example is not None else {}, ensure_ascii=False, indent=2)
            body_mode = "raw"
        elif is_multipart:
            # Build form-data items from request params and multipart file params.
            form_items: List[Dict[str, Any]] = []
            # multipart file
            for p in param_decls:
                if p.get("annotations", {}).get("MultipartFile"):
                    form_items.append({"key": p.get("name"), "value": "", "type": "file"})
                elif p.get("annotations", {}).get("RequestParam"):
                    key = p["annotations"]["RequestParam"]["name"] or p.get("name")
                    val = example_value_for_query(p.get("type", ""))
                    form_items.append({"key": key, "value": val, "type": "text"})
                # Also include request params without RequestParam annotation (best effort)
            formdata = form_items

        # Build Postman variables
        variables_used: Set[str] = set()
        for v in path_vars:
            variables_used.add(v)
        for qp in query_params:
            variables_used.add(qp["name"])
        for h in headers:
            variables_used.add(sanitize_var_key(h["name"]))

        # Replace {var} with {{var}} in raw path
        url_raw = replace_path_vars_with_postman_vars(full_path, path_vars)

        preauth_text = preauthorize or ""
        methods.append(
            {
                "controller": controller_name,
                "tag": tag or "",
                "name": method_name,
                "http_method": http_method,
                "path": full_path,
                "url_raw": url_raw,
                "preauthorize": preauth_text,
                "headers": headers,
                "path_vars": sorted(list(path_vars)),
                "query_params": query_params,
                "request_body": {
                    "mode": body_mode,
                    "raw": body_raw,
                    "formdata": formdata,
                    "request_body_type": request_body_param.get("type") if request_body_param else None,
                },
                "return_type": return_type,
                "consumes": consumes,
            }
        )
    return methods


def build_postman_collection(items: List[Dict[str, Any]], base_env_url_var: str = "{{url}}") -> Dict[str, Any]:
    collection: Dict[str, Any] = {
        "info": {
            "name": "Booklore API",
            "_postman_id": str(uuid.uuid4()),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [],
        "item": [],
    }

    # Global variables for path/query placeholders
    var_defaults: Dict[str, str] = {}

    def add_var(k: str, v: str) -> None:
        if k and k not in var_defaults:
            var_defaults[k] = v

    for it in items:
        for v in it["path_vars"]:
            add_var(v, "1")
        for qp in it["query_params"]:
            add_var(qp["name"], example_value_for_query(qp["type"]))
        # header vars for remote auth or others are only used in header list; we don't auto-fill.

    collection["variable"] = [{"key": k, "value": v} for k, v in sorted(var_defaults.items())]

    # Group endpoints by controller (each controller becomes a folder)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        grouped.setdefault(it.get("controller", "Other"), []).append(it)

    for controller, controller_items in sorted(grouped.items(), key=lambda kv: kv[0]):
        folder_item: Dict[str, Any] = {"name": controller, "item": []}

        for it in controller_items:
            headers_list: List[Dict[str, str]] = []
            auth_needed = bool(it["preauthorize"])
            # Default: most secured endpoints use Bearer token.
            uses_basic = "/opds" in it["path"]

            if auth_needed:
                if uses_basic:
                    headers_list.append({"key": "Authorization", "value": "Basic {{token}}"})
                else:
                    headers_list.append({"key": "Authorization", "value": "Bearer {{token}}"})

            for hdr in it["headers"]:
                hdr_key = hdr["name"]
                var_key = sanitize_var_key(hdr_key)
                headers_list.append({"key": hdr_key, "value": f"{{{{{var_key}}}}}"})
                add_var(var_key, "")

            request: Dict[str, Any] = {
                "method": it["http_method"],
                "header": headers_list,
                "url": {
                    "raw": "{{url}}" + it["url_raw"],
                    "host": ["{{url}}"],
                    "path": [seg for seg in it["url_raw"].lstrip("/").split("/") if seg],
                },
            }

            body = it["request_body"]
            if body.get("mode") == "raw" and body.get("raw") is not None:
                request["body"] = {
                    "mode": "raw",
                    "raw": body["raw"],
                    "options": {"raw": {"language": "json"}},
                }
            elif body.get("formdata") is not None:
                request["body"] = {
                    "mode": "formdata",
                    "formdata": body["formdata"],
                }

            desc_bits = []
            if it["tag"]:
                desc_bits.append(f"Tag: {it['tag']}")
            if it["preauthorize"]:
                desc_bits.append(f"PreAuthorize: {it['preauthorize']}")
            if it["query_params"]:
                desc_bits.append(
                    "Query params: " + ", ".join([qp["name"] for qp in it["query_params"]])
                )
            if it["path_vars"]:
                desc_bits.append("Path vars: " + ", ".join(it["path_vars"]))

            # Human-friendly request name
            item_obj: Dict[str, Any] = {
                "name": f"{it['name']}: {it['http_method']} {it['url_raw']}",
                "request": request,
            }
            if desc_bits:
                item_obj["description"] = "\n".join(desc_bits)

            folder_item["item"].append(item_obj)

        collection["item"].append(folder_item)
    return collection


def main() -> None:
    java_files = list_java_files(SRC_DIR)
    type_index = build_type_index(java_files)

    controller_files: List[str] = []
    for dirpath, _, filenames in os.walk(CONTROLLERS_DIR):
        for fn in filenames:
            if fn.endswith(".java"):
                controller_files.append(os.path.join(dirpath, fn))

    all_items: List[Dict[str, Any]] = []
    for cpath in sorted(controller_files):
        ctext = read_text(cpath)
        controller_name = os.path.splitext(os.path.basename(cpath))[0]
        base = extract_class_base_path(ctext)
        if not base.startswith("/api"):
            # Still include non-/api mappings; user asked /api** but these are our heuristics.
            # We'll keep them if they include '/api'.
            pass
        methods = parse_controller_methods(cpath, base, type_index, controller_name=controller_name)
        all_items.extend(methods)

    # Filter: only /api and /api/v1 and /api/v2 and other /api/* (as user requested "barchasi")
    filtered = [it for it in all_items if it.get("path", "").startswith("/api")]

    collection = build_postman_collection(filtered)

    env = {
        "id": str(uuid.uuid4()),
        "name": "Booklore Environment",
        "values": [
            {"key": "url", "value": "http://localhost:6060"},
            {"key": "token", "value": ""},
        ],
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/postman_environment.json",
    }

    with open(OUTPUT_COLLECTION, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)
    with open(OUTPUT_ENV, "w", encoding="utf-8") as f:
        json.dump(env, f, ensure_ascii=False, indent=2)

    print(f"Endpoints included: {len(filtered)}")
    print(f"Wrote: {OUTPUT_COLLECTION}")
    print(f"Wrote: {OUTPUT_ENV}")


if __name__ == "__main__":
    main()

