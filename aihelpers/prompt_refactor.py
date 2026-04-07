import re
import os

def refactor_prompt(text):
    if not text:
        return ""

    # 1. 基础术语替换 (Terminology Replacement)
    # 使用正则确保只匹配完整的单词，防止误伤
    replacements = {
        r"\bClaude Code\b": "Gemini AI Extension",
        r"\bClaude\b": "Gemini",
        r"\bAnthropic\b": "Google",
        r"(?i)use claude reasoning": "use step-by-step reasoning",
        # Claude 常用的思维草稿箱，转为注释或 Markdown 块
        r"<scratchpad>": "\n",
        r"</scratchpad>": "\n"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    # 2. 结构化 XML 标签转换为 Markdown 标题 (XML to Markdown)
    # 匹配 <tag>...</tag> 结构，支持跨行匹配 (re.DOTALL)
    def tag_replacer(match):
        tag_name = match.group(1).replace("_", " ").title() # 例如 <system_prompt> 变 System Prompt
        content = match.group(2).strip()
        # 转换为清晰的 Markdown 二级标题
        return f"\n\n## {tag_name}\n\n{content}\n\n"

    # 使用非贪婪匹配 (.*?) 捕获标签内容
    text = re.sub(r'<([a-zA-Z0-9_-]+)>(.*?)</\1>', tag_replacer, text, flags=re.DOTALL)

    # 3. 清理多余的空行 (格式美化)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 4. 追加 Gemini 最佳实践提示语
    gemini_tail = "\n\n**Note**: Please provide direct, concise answers and format your output strictly using Markdown."
    
    return text.strip() + gemini_tail

def refactor_file(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"  ⚠️ Prompt file missing: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = refactor_prompt(content)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  ✨ Refactored Prompt: Stripped XML tags and mapped to Gemini Markdown.")

# 测试桩 (可选)
if __name__ == "__main__":
    sample_claude_prompt = """
    You are Claude.
    <instructions>
    Always be polite and use Claude reasoning.
    </instructions>
    <example>
    User: Hi
    AI: Hello!
    </example>
    """
    print(refactor_prompt(sample_claude_prompt))
