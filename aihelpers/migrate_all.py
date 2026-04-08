import os
import shutil
import json
from aihelpers.plugin_usage_ranker import rank_plugins
from aihelpers.convert_claude_plugin import convert_plugin
from aihelpers.prompt_refactor import refactor_file
from aihelpers.gemini_compat_check import run_check

from aihelpers.config import SOURCE_DIR, TARGET_DIR
PLUGIN_ROOT = str(SOURCE_DIR)
OUTPUT_ROOT = str(TARGET_DIR)
STATE_FILE = "migration_state.json"
BATCH_SIZE = 2  # 🌟 核心：每次只迁移 2 个插件，保护 Token 额度

def load_state():
    """加载迁移进度账本"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": []}

def save_state(state):
    """保存迁移进度账本"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def migrate():
    print("🚀 Starting AI Helpers Smart Migration Pipeline (Batch Mode)...\n")

    state = load_state()
    completed_plugins = set(state.get("completed", []))

    # 1. 评估与排序
    ranked = rank_plugins(PLUGIN_ROOT)
    if not ranked:
        print("⚠️ No plugins found in source directory.")
        return

    # 2. 过滤掉已经迁移过的插件
    pending_plugins = [p for p in ranked if p not in completed_plugins]
    
    if not pending_plugins:
        print("🎉 All plugins have already been migrated! Nothing to do.")
        return

    print(f"📊 Progress: {len(completed_plugins)} completed, {len(pending_plugins)} pending.")
    
    # 3. 截取今天的批次
    current_batch = pending_plugins[:BATCH_SIZE]
    print(f"📦 Today's Batch ({len(current_batch)} plugins): {current_batch}\n")

    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    # 4. 执行本批次迁移
    for plugin in current_batch:
        print(f"{'-'*40}")
        print(f"⚙️ Processing: {plugin}")
        print(f"{'-'*40}")
        
        src_dir = os.path.join(PLUGIN_ROOT, plugin)
        dst_dir = os.path.join(OUTPUT_ROOT, plugin)

        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir,
                        ignore=shutil.ignore_patterns('.claude-plugin'))

        # 转换流程
        convert_plugin(src_dir, dst_dir)
        
        src_prompt = os.path.join(src_dir, "command.md")
        dst_prompt = os.path.join(dst_dir, "prompt.md")
        if os.path.exists(src_prompt):
            refactor_file(src_prompt, dst_prompt)

        run_check(dst_dir)

        # 🌟 关键：迁移成功后，记入账本并保存
        state["completed"].append(plugin)
        save_state(state)
        print(f"✅ {plugin} marked as completed in state file.")

    print(f"\n⏸️ Batch completed. {len(pending_plugins) - len(current_batch)} plugins left for next time.")
    print(f"Run this script again tomorrow or when your token quota resets.")

if __name__ == "__main__":
    migrate()
    # After all plugins are migrated, run generate_toml.py to produce the
    # .toml files required by Gemini CLI's FileCommandLoader:
    #   python3 generate_toml.py
    #   python3 validate_toml.py
