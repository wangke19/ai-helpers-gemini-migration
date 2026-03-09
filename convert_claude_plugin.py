import json
import os
import yaml

def convert_plugin(plugin_dir, output_dir):
    plugin_file = os.path.join(plugin_dir, "plugin.json")
    if not os.path.exists(plugin_file):
        print(f"  ⚠️ Skipping schema conversion: plugin.json not found in {plugin_dir}")
        return

    with open(plugin_file, "r", encoding="utf-8") as f:
        try:
            plugin = json.load(f)
        except json.JSONDecodeError:
            print(f"  ❌ Invalid JSON format in {plugin_file}")
            return

    # 核心：提取 Claude 的工具参数定义
    claude_schema = plugin.get("input_schema", {})
    plugin_name = plugin.get("name", "unnamed_plugin").replace("-", "_") # Gemini 更偏好下划线命名
    
    # 构建 Gemini Extension 基础骨架
    extension = {
        "name": plugin_name,
        "version": plugin.get("version", "1.0.0"),
        "description": plugin.get("description", "Migrated from Claude AI Helpers"),
        "capabilities": [
            {
                "type": "prompt",
                "file": "prompt.md"
            }
        ]
    }

    # 如果有参数定义，将其转换为 Gemini 的 Function Declaration 格式
    if claude_schema:
        extension["tools"] = [{
            "functionDeclarations": [{
                "name": plugin_name,
                "description": plugin.get("description", ""),
                "parameters": claude_schema  # 将 Claude Schema 映射过来
            }]
        }]

    os.makedirs(output_dir, exist_ok=True)

    # 导出为 Gemini 偏好的 YAML 格式
    yaml_path = os.path.join(output_dir, "extension.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(extension, f, sort_keys=False, allow_unicode=True)

    # 清理遗留的 plugin.json
    legacy_json = os.path.join(output_dir, "plugin.json")
    if os.path.exists(legacy_json):
        os.remove(legacy_json)

    print(f"  ✅ Converted Schema: input_schema -> Gemini functionDeclarations")
