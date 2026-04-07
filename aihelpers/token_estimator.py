import os
import json
from plugin_usage_ranker import rank_plugins

PLUGIN_ROOT = "ai-helpers/plugins"
STATE_FILE = "migration_state.json"
BATCH_SIZE = 2  # 必须与 migrate_all.py 保持一致

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": []}

def estimate_file_tokens(filepath):
    """使用通用启发式算法估算 Token (1 token ≈ 3.5 字符)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # 代码中符号较多，3.5 是一个偏保守（更安全）的估算值
            return int(len(content) / 3.5)
    except UnicodeDecodeError:
        return 0  # 跳过图片等非文本文件

def estimate_batch():
    print("🧮 Running Token Estimator for Today's Batch...\n")
    
    state = load_state()
    completed = set(state.get("completed", []))
    
    ranked = rank_plugins(PLUGIN_ROOT)
    if not ranked:
        print("⚠️ No plugins found.")
        return

    pending = [p for p in ranked if p not in completed]
    if not pending:
        print("🎉 All plugins migrated! 0 tokens needed.")
        return
        
    current_batch = pending[:BATCH_SIZE]
    
    total_tokens = 0
    print(f"📦 Batch to process: {current_batch}")
    print("-" * 40)
    
    for plugin in current_batch:
        plugin_dir = os.path.join(PLUGIN_ROOT, plugin)
        plugin_tokens = 0
        
        for root, _, files in os.walk(plugin_dir):
            for file in files:
                filepath = os.path.join(root, file)
                file_tokens = estimate_file_tokens(filepath)
                plugin_tokens += file_tokens
                
        print(f"  - {plugin}: ~{plugin_tokens:,} tokens")
        total_tokens += plugin_tokens

    print("-" * 40)
    print(f"📊 Total Input Token Estimate: ~{total_tokens:,} tokens")
    
    # 结合 Claude 默认上下文和输出消耗给出的安全建议
    estimated_total_cost = total_tokens * 2.5 # 包含输出和思考冗余的粗略倍率
    print(f"💡 Expected Context Window Cost (Input + Output/Reasoning): ~{int(estimated_total_cost):,} tokens")
    
    if estimated_total_cost < 50000:
        print("🟢 Status: SAFE. Extremely lightweight batch, won't trigger rate limits.")
    elif estimated_total_cost < 150000:
        print("🟡 Status: MODERATE. Safe for daily quota, good batch size.")
    else:
        print("🔴 Status: HEAVY. Consider reducing BATCH_SIZE in migrate_all.py to avoid quota exhaustion.")

if __name__ == "__main__":
    # 屏蔽 rank_plugins 里的多余 print，保持输出清爽
    import sys, io
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        estimate_batch()
    finally:
        output = sys.stdout.getvalue()
        sys.stdout = original_stdout
        # 只打印我们自己的输出
        print(output.split("🧮 Running Token Estimator")[1] if "🧮" in output else output)
