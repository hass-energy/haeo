import os

root_dir = "."
old_str = "haeo_core.model"
new_str = "haeo_core.model"

for subdir, dirs, files in os.walk(root_dir):
    if ".git" in subdir or "haeo_core.egg-info" in subdir:
        continue
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(subdir, file)
            try:
                with open(filepath, "r") as f:
                    content = f.read()
                if old_str in content:
                    new_content = content.replace(old_str, new_str)
                    with open(filepath, "w") as f:
                        f.write(new_content)
                    print(f"Updated {filepath}")
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
