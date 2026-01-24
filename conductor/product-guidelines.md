# Product Guidelines: CAPL Analyzer

## 1. Prose Style

The CAPL Analyzer uses a **Balanced Technical** prose style that combines:

### Technical Precision (for error messages and reports)
*   **Precision:** Exact terminology aligned with CAPL specifications
*   **Accuracy:** Factually correct information about code issues
*   **Technical Detail:** Respects developer expertise with specific references

### Practical Clarity (for suggestions and auto-fix output)
*   **Actionable Guidance:** Clear "why this is wrong" and "how to fix it"
*   **Examples:** Show before/after code snippets
*   **Progressive Disclosure:** Brief summary + detailed explanation on demand

**Example Error Message:**
```
❌ ERROR: MyNode.can:25 [E006] - Variable 'badVar' declared outside 'variables {}' block
   💡 Move 'badVar' declaration into the variables {} block
   🔧 Auto-fixable
```

## 2. Target Audience

### Primary Users
*   **Embedded Software Engineers** - Writing CAPL test scripts for automotive systems
*   **Test Automation Engineers** - Maintaining large CAPL test suites
*   **Code Reviewers** - Enforcing standards across teams

### Expertise Assumptions
*   Users understand CAPL syntax and semantics
*   Familiar with static analysis concepts
*   May not know every tree-sitter or linting detail (we handle that)

### Communication Goals
*   **Errors**: Technical precision - explain WHAT is wrong
*   **Suggestions**: Practical guidance - explain WHY and HOW to fix
*   **Reports**: Structured data - scannable and CI/CD friendly

## 3. Message Types and Tone

### ERROR Messages
- **Style**: Direct, technical, authoritative
- **Format**: `[E00X] <precise description>` (e.g., E001, E006)
- **Must Include**: Line number, rule violation code, CAPL specification reference

### WARNING Messages  
- **Style**: Advisory, best-practice oriented
- **Format**: `<issue> - <potential impact>`
- **Should Include**: Suggestion for resolution

### Auto-Fix Output
- **Style**: Transparent, confidence-building
- **Format**: `✓ Fixed <count> issues` with summary
- **Must Show**: What changed and why
