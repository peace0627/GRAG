#!/usr/bin/env python3
"""
更新專案以支援 Pydantic v2

將舊的 Pydantic v1 Config 語法轉換為 Pydantic v2 model_config 語法
"""

import os
import re
import glob

def update_pydantic_config(file_path):
    """更新單個檔案中的 Pydantic Config 語法"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 檢查是否已經更新過
    if 'model_config' in content:
        print(f"⏭️  檔案 {file_path} 已經更新過，跳過")
        return False

    # 替換 Config 類為 model_config 字典
    config_pattern = r'class Config:\s*\n((?:\s+.*\n)*)'
    replacement = 'model_config = {\n'

    def config_replacer(match):
        config_content = match.group(1)
        # 解析 Config 內容並轉換為字典格式
        lines = config_content.strip().split('\n')
        dict_items = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 移除縮進和結尾逗號
                line = line.replace('    ', '').rstrip(',')
                if '=' in line:
                    dict_items.append(f'    {line}')

        if dict_items:
            replacement = 'model_config = {\n' + ',\n'.join(dict_items) + '\n}'
        else:
            replacement = 'model_config = {}'

        return replacement

    new_content = re.sub(config_pattern, config_replacer, content, flags=re.MULTILINE | re.DOTALL)

    # 如果內容有變化，寫回檔案
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ 已更新 {file_path}")
        return True
    else:
        print(f"⏭️  檔案 {file_path} 不需要更新")
        return False

def main():
    """主函數"""
    print("🚀 開始更新專案以支援 Pydantic v2\n")

    # 找到所有 Python 檔案
    project_dir = 'project'
    python_files = []

    for root, dirs, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"📁 找到 {len(python_files)} 個 Python 檔案\n")

    updated_count = 0
    for file_path in python_files:
        if update_pydantic_config(file_path):
            updated_count += 1

    print(f"\n🎉 更新完成！共更新了 {updated_count} 個檔案")

    if updated_count > 0:
        print("\n📋 更新的主要變更:")
        print("  • Config 類 → model_config 字典")
        print("  • use_enum_values → 移除了（在新版本中預設行為）")

        print("\n🧪 建議測試更新後的程式碼:")
        print("  cd project && python test_schema.py")

if __name__ == "__main__":
    main()
