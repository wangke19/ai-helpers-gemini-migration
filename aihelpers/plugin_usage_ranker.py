
import os

def rank_plugins(plugin_root):

    plugins = []

    for name in os.listdir(plugin_root):

        path = os.path.join(plugin_root, name)

        if not os.path.isdir(path):
            continue

        score = 0

        command_file = os.path.join(path, "command.md")

        if os.path.exists(command_file):
            score += 2

        plugin_json = os.path.join(path, "plugin.json")

        if os.path.exists(plugin_json):
            score += 3

        plugins.append((name, score))

    plugins.sort(key=lambda x: x[1], reverse=True)

    print("Plugin ranking:")
    for p in plugins:
        print(p[0], "score:", p[1])

    return [p[0] for p in plugins]
