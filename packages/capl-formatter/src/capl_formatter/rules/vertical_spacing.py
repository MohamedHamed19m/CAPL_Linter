from typing import List
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

LOGIC_NODE_TYPES = {
    "expression_statement",
    "if_statement",
    "if_else_statement",
    "for_statement",
    "while_statement",
    "do_statement",
    "switch_statement",
    "return_statement",
}


class VerticalSpacingRule(ASTRule):
    """
    Manages vertical whitespace (blank lines).
    - Compresses local variable declarations at the start of blocks (Setup Zone).
    - Preserves single blank lines between logic statements (Logic Zone).
    - Cleans up blank lines at block boundaries (after { and before }).
    """

    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str:
        return "F015"

    @property
    def name(self) -> str:
        return "vertical-spacing"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not context.tree:
            return []

        transformations = []

        def _should_process_block(node) -> bool:
            """
            Global variables blocks should be skipped for compression.
            Local variables blocks or compound statements should be processed.
            """
            if node.type == "compound_statement":
                # In CAPL, global variables blocks are often compound_statements
                # directly under the translation_unit (preceded by 'variables' keyword
                # which might be in an ERROR node).
                if node.parent and node.parent.type == "translation_unit":
                    return False
                return True
            return False

        def traverse(node):
            if _should_process_block(node):
                is_setup_zone = True
                prev_child = None

                # Brace Edge Cleanup (Start): Space between { and first child
                open_brace = next((c for c in node.children if c.type == "{"), None)
                if open_brace:
                    first_child = None
                    for child in node.children:
                        if child.start_byte >= open_brace.end_byte and child.type not in ["{", "}"] and child.is_named:
                            first_child = child
                            break
                    
                    if first_child:
                        # If row diff > 1, there is a blank line
                        if first_child.start_point[0] > open_brace.end_point[0] + 1:
                            transformations.append(Transformation(
                                start_byte=open_brace.end_byte,
                                end_byte=first_child.start_byte,
                                new_content="\n",
                                priority=10
                            ))

                for child in node.children:
                    # Skip boundary tokens
                    if child.type in ["{", "}", "variables", ":"] or not child.is_named:
                        continue

                    # Determine if we transitioned to Logic Zone
                    if child.type != "comment" and is_setup_zone and child.type in LOGIC_NODE_TYPES:
                        is_setup_zone = False

                    # Setup Zone Compression
                    if is_setup_zone:
                        if prev_child:
                            # If row diff > 1, there is a blank line
                            if child.start_point[0] > prev_child.end_point[0] + 1:
                                transformations.append(Transformation(
                                    start_byte=prev_child.end_byte,
                                    end_byte=child.start_byte,
                                    new_content="\n",
                                    priority=5
                                ))

                    prev_child = child

                # Brace Edge Cleanup (End): Space between last child and }
                close_brace = next((c for c in reversed(node.children) if c.type == "}"), None)
                if close_brace:
                    last_child = None
                    for child in reversed(node.children):
                        if child.end_byte <= close_brace.start_byte and child.type not in ["{", "}"] and child.is_named:
                            last_child = child
                            break
                    
                    if last_child:
                        if close_brace.start_point[0] > last_child.end_point[0] + 1:
                            transformations.append(Transformation(
                                start_byte=last_child.end_byte,
                                end_byte=close_brace.start_byte,
                                new_content="\n",
                                priority=10
                            ))

            for child in node.children:
                traverse(child)

        traverse(context.tree.root_node)
        return transformations