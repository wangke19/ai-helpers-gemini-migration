import os
import re
from aihelpers.config import TARGET_DIR

def check_code_file(filepath):
    """扫描 Python/JS/TS 源码中的不兼容 API 调用"""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        return issues  # 跳过非文本文件

    filename = os.path.basename(filepath)

    # 1. 扫描 Python 源码
    if filepath.endswith('.py'):
        # 检查 import
        if re.search(r'^import\s+anthropic', content, re.MULTILINE) or \
           re.search(r'^from\s+anthropic\s+import', content, re.MULTILINE):
            issues.append(f"[{filename}] Hardcoded 'anthropic' Python SDK import detected. Needs migration to 'google.generativeai'.")
        # 检查客户端初始化
        if 'Anthropic(' in content or 'AsyncAnthropic(' in content:
            issues.append(f"[{filename}] Anthropic() client initialization detected.")
        # 检查特有参数 (如 max_tokens 映射到 max_output_tokens)
        if 'max_tokens=' in content:
            issues.append(f"[{filename}] 'max_tokens' found. Note: Gemini uses 'max_output_tokens'.")

    # 2. 扫描 JavaScript/TypeScript 源码
    elif filepath.endswith(('.js', '.ts')):
        if '@anthropic-ai/sdk' in content:
            issues.append(f"[{filename}] '@anthropic-ai/sdk' import detected. Needs migration to '@google/generative-ai'.")
        if 'new Anthropic' in content:
            issues.append(f"[{filename}] 'new Anthropic()' instantiation detected.")

    return issues

def check_prompt(prompt_path):
    """扫描 Prompt 中的遗留问题"""
    issues = []
    if not os.path.exists(prompt_path):
        return issues

    with open(prompt_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 检查 Claude 特有的 Slash Command
    if "/command" in text:
        issues.append("[prompt.md] Slash command syntax detected. Gemini Extensions typically use natural language triggers.")

    # 检查是否还有遗漏的 XML 标签
    if re.search(r'<[a-zA-Z0-9_-]+>', text):
        issues.append("[prompt.md] Unresolved XML tags might still be present. Check if refactor missed any.")

    return issues

def run_check(extension_dir):
    print(f"  🔍 Running Deep Compatibility Check...")
    all_issues = []

    # 1. 检查重构后的 Prompt
    prompt_path = os.path.join(extension_dir, "prompt.md")
    all_issues.extend(check_prompt(prompt_path))

    # 2. 遍历扫描所有源代码文件
    for root, _, files in os.walk(extension_dir):
        for file in files:
            if file.endswith(('.py', '.js', '.ts')):
                filepath = os.path.join(root, file)
                all_issues.extend(check_code_file(filepath))

    # 3. 输出审计报告
    if all_issues:
        print("  ⚠️ Compatibility issues found (Manual Review or AI Auto-Fix Required):")
        for issue in all_issues:
            print(f"     - {issue}")
    else:
        print("  ✅ Code & Prompt are clean! Fully compatible with Gemini ecosystem.")

# CLI support for single plugin check
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        plugin_name = sys.argv[1]
        extension_dir = str(TARGET_DIR / plugin_name)
        if os.path.exists(extension_dir):
            run_check(extension_dir)
        else:
            print(f"Plugin directory not found: {extension_dir}")
            sys.exit(1)
    else:
        print("Usage: python3 gemini_compat_check.py <plugin_name>")
        sys.exit(1)
