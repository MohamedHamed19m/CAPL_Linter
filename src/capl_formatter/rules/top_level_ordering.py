from typing import Any

from ..models import CommentAttachment, FormatterConfig
from .base import ASTRule, FormattingContext, Transformation


class TopLevelOrderingRule(ASTRule):
    """Enforces standardized CAPL top-level ordering."""

    def __init__(self, config: FormatterConfig):
        self.config = config
        # Canonical Order
        self.ordering_hierarchy = [
            "includes",  # includes { ... }
            "variables",  # variables { ... }
            "testcases",  # testcase ... { ... }
            "event_handlers",  # on ... { ... }
            "functions",  # void/int ... { ... }
        ]

    @property
    def rule_id(self) -> str:
        return "F015"

    @property
    def name(self) -> str:
        return "top-level-ordering"

    def analyze(self, context: FormattingContext) -> list[Transformation]:
        if not self.config.reorder_top_level:  # Config flag check
            return []

        if not context.tree:
            return []

        root = context.tree.root_node

        # 1. Safety Check: Bail out on root-level errors
        # We allow ERROR nodes if they are just wrapper nodes for 'variables' or similar
        # but we must be careful. For now, strict safety: bail on any ERROR that isn't
        # clearly just a keyword wrapper.
        for child in root.children:
            if child.type == "ERROR":
                text = child.text.decode("utf-8", errors="ignore")
                if "variables" not in text and "on" not in text and "includes" not in text:
                    return []

        # 2. Pre-process Comments for fast lookup
        # Map: node.id -> List[CommentAttachment] (sorted by line)
        comment_lookup: dict[int, list[CommentAttachment]] = {}
        if context.metadata and "comment_attachments" in context.metadata:
            for attachment in context.metadata["comment_attachments"].values():
                if attachment.attachment_type == "header" and attachment.target_node:
                    nid = attachment.target_node.id
                    if nid not in comment_lookup:
                        comment_lookup[nid] = []
                    comment_lookup[nid].append(attachment)

            # Sort comments for each node by line number
            for nid in comment_lookup:
                comment_lookup[nid].sort(key=lambda x: x.comment_line)

        # 3. Categorize Nodes
        buckets = {k: [] for k in self.ordering_hierarchy}

        children = root.children
        i = 0
        while i < len(children):
            child = children[i]

            if child.type in ["comment", "line_comment"]:
                i += 1
                continue

            # pattern matching for multi-node structures
            text = child.text.decode("utf-8", errors="ignore") if child.text else ""

            # Pattern 1: 'includes' or 'variables' keyword + compound_statement
            # parsed as expression_statement (id) + compound_statement
            is_keyword_block = False
            keyword_type = ""

            if child.type == "expression_statement":
                # Check if it contains just an identifier
                if len(child.children) > 0 and child.children[0].type == "identifier":
                    id_text = child.children[0].text.decode("utf-8", errors="ignore")
                    if id_text in ["includes", "variables"]:
                        is_keyword_block = True
                        keyword_type = id_text

            # Also handle if it's an ERROR node containing the keyword
            if child.type == "ERROR" and ("includes" in text or "variables" in text):
                if "includes" in text:
                    is_keyword_block = True
                    keyword_type = "includes"
                elif "variables" in text:
                    is_keyword_block = True
                    keyword_type = "variables"

            if is_keyword_block and i + 1 < len(children):
                next_child = children[i + 1]
                if next_child.type == "compound_statement":
                    # Found split block (includes/variables)
                    full_text = self._extract_merged_text(
                        [child, next_child], context.source, comment_lookup
                    )
                    buckets[keyword_type].append(("", full_text))
                    i += 2
                    continue

            # Pattern 2: Complex Event Handler (on message ...)
            # declaration (on message) + expression_statement (signature) + compound_statement (body)
            # OR declaration (on message) + compound_statement (if signature is missing/implicit?)
            if child.type == "declaration" and "on" in text and "message" in text:
                # Look ahead for compound_statement
                nodes_to_merge = [child]
                consumed_count = 1

                # Try to consume up to 2 more siblings to find the body
                found_body = False
                for offset in range(1, 3):
                    if i + offset < len(children):
                        sibling = children[i + offset]
                        nodes_to_merge.append(sibling)
                        if sibling.type == "compound_statement":
                            found_body = True
                            consumed_count = offset + 1
                            break

                if found_body:
                    # Extract sort key from the middle node(s) (signature)
                    signature = ""
                    if consumed_count == 3:
                        signature = nodes_to_merge[1].text.decode("utf-8", errors="ignore")

                    sort_key = f"message {signature}".strip().lower()
                    full_text = self._extract_merged_text(
                        nodes_to_merge, context.source, comment_lookup
                    )
                    buckets["event_handlers"].append((sort_key, full_text))
                    i += consumed_count
                    continue

            # Standard Classification (Single Node)
            category = self._classify_node(child)
            if category:
                text = self._extract_node_text(child, context.source, comment_lookup)
                sort_key = self._get_sort_key(child)
                buckets[category].append((sort_key, text))

            i += 1

        # 4. Generate Content
        new_content_parts = []

        for category in self.ordering_hierarchy:
            items = buckets[category]
            if not items:
                continue

            # Sort if needed
            if category in ["event_handlers", "functions"]:
                items.sort(key=lambda x: x[0])  # Sort by name

            # Add to content
            for _, text in items:
                new_content_parts.append(text)

        new_content = "\n\n".join(new_content_parts).strip() + "\n"

        if new_content == context.source:
            return []

        return [Transformation(0, len(context.source), new_content)]

    def _classify_node(self, node) -> str:
        t = node.type
        if t == "includes":
            return "includes"
        # If 'variables' block is a single node (unlikely in tree-sitter-c but possible)
        if t == "variables_block":
            return "variables"

        if t == "testcase_definition":
            return "testcases"

        if t == "function_definition":
            # Check for 'on ...'
            if len(node.children) > 0:
                first = node.children[0]
                first_text = first.text.decode("utf-8", errors="ignore")
                if first_text == "on":
                    return "event_handlers"
            return "functions"

        return None

    def _get_sort_key(self, node) -> str:
        """Extract name/signature for alphabetical sorting."""
        if node.type == "function_definition":
            # Event Handler: 'on message MsgName' -> 'message msgname'
            if (
                len(node.children) > 0
                and node.children[0].text.decode("utf-8", errors="ignore") == "on"
            ):
                # Collect remaining identifiers for sort key
                parts = []
                for child in node.children[1:]:
                    if child.type in ["identifier", "type_identifier", "number_literal"]:
                        parts.append(child.text.decode("utf-8", errors="ignore").lower())
                    if child.type == "parameter_list":  # Stop at parameters
                        break
                return " ".join(parts)

            # Function: 'void FuncName' -> 'funcname'
            # The function name is usually the 'declarator' -> 'identifier'
            # Simplified: look for the first identifier that isn't a type
            for child in node.children:
                if child.type == "function_declarator":
                    for sub in child.children:
                        if sub.type == "identifier":
                            return sub.text.decode("utf-8", errors="ignore").lower()
        return ""

    def _extract_node_text(self, node, source, comment_lookup) -> str:
        """Extract node text prepended with all attached header comments."""
        comments = comment_lookup.get(node.id, [])

        parts = []
        for c in comments:
            parts.append(c.comment_node.text.decode("utf-8", errors="ignore"))

        parts.append(source[node.start_byte : node.end_byte])
        return "\n".join(parts)

    def _extract_merged_text(self, nodes: list[Any], source, comment_lookup) -> str:
        """Extract text for a split block (keyword + body), handling comments on the keyword."""
        if not nodes:
            return ""

        # Comments are usually attached to the first node (the keyword)
        first_node = nodes[0]
        last_node = nodes[-1]

        comments = comment_lookup.get(first_node.id, [])

        parts = []
        for c in comments:
            parts.append(c.comment_node.text.decode("utf-8", errors="ignore"))

        # Get text from start of first node to end of last node
        text = source[first_node.start_byte : last_node.end_byte]
        parts.append(text)

        return "\n".join(parts)
