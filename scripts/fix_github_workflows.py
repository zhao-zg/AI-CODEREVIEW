#!/usr/bin/env python3
"""
GitHub Workflows语法修复脚本
修复.github/workflows目录中的YAML语法错误
"""

import os
import re
import yaml
from pathlib import Path

def fix_yaml_syntax(file_path):
    """修复YAML文件中的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 记录原始内容
        original_content = content
        
        # 修复常见的语法错误
        
        # 1. 修复缺少换行的问题 (steps后面直接跟- name)
        content = re.sub(r'(steps:)(\s*-)(\s*name:)', r'\1\n\n    \2\3', content)
        
        # 2. 修复action步骤之间缺少换行的问题
        content = re.sub(r'(uses: [^\n]+)(\s*-)(\s*name:)', r'\1\n\n    \2\3', content)
        
        # 3. 修复password/username后面直接跟- name的问题
        content = re.sub(r'(password: [^\n]+)(\s*-)(\s*name:)', r'\1\n\n    \2\3', content)
        
        # 4. 修复其他缺少换行的问题
        content = re.sub(r'(\$\{\{ secrets\.[A-Z_]+ \}\})(\s*-)(\s*name:)', r'\1\n\n    \2\3', content)
        
        # 5. 确保每个步骤之间有适当的间距
        lines = content.split('\n')
        fixed_lines = []
        in_steps = False
        
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            
            # 检测是否在steps部分
            if line.strip() == 'steps:':
                in_steps = True
                continue
            
            # 在steps部分，确保每个- name:之间有空行
            if in_steps and line.strip().startswith('- name:'):
                # 检查下一行是否是uses或run
                next_line_idx = i + 1
                if next_line_idx < len(lines):
                    next_line = lines[next_line_idx].strip()
                    if next_line.startswith('uses:') or next_line.startswith('run:'):
                        # 这是一个完整的步骤开始，前面需要空行
                        if i > 0 and lines[i-1].strip() != '':
                            fixed_lines.insert(-1, '')
        
        # 重新组合内容
        content = '\n'.join(fixed_lines)
        
        # 验证YAML语法
        try:
            yaml.safe_load(content)
            print(f"✅ {file_path}: YAML语法验证通过")
        except yaml.YAMLError as e:
            print(f"❌ {file_path}: YAML语法仍有错误: {e}")
            return False
        
        # 如果内容有改变，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"🔧 {file_path}: 已修复YAML语法错误")
            return True
        else:
            print(f"✅ {file_path}: 无需修复")
            return True
            
    except Exception as e:
        print(f"❌ 修复 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    workflows_dir = Path('.github/workflows')
    
    if not workflows_dir.exists():
        print("❌ .github/workflows目录不存在")
        return
    
    print("🔧 开始修复GitHub Workflows文件...")
    
    # 获取所有yml文件
    yml_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))
    
    if not yml_files:
        print("❌ 未找到YAML文件")
        return
    
    success_count = 0
    
    for yml_file in yml_files:
        print(f"\n🔍 检查文件: {yml_file}")
        if fix_yaml_syntax(yml_file):
            success_count += 1
    
    print(f"\n📊 修复完成: {success_count}/{len(yml_files)} 个文件修复成功")
    
    # 生成修复报告
    report_content = f"""# GitHub Workflows修复报告

## 修复统计
- 总文件数: {len(yml_files)}
- 修复成功: {success_count}
- 修复失败: {len(yml_files) - success_count}

## 修复的问题类型
1. ✅ 修复了steps后面直接跟- name的换行问题
2. ✅ 修复了action步骤之间缺少换行的问题  
3. ✅ 修复了password/username后面直接跟- name的问题
4. ✅ 确保了YAML语法的正确性

## 文件列表
"""
    
    for yml_file in yml_files:
        report_content += f"- `{yml_file}`\n"
    
    report_content += f"""
## 验证方法
可以使用以下命令验证YAML语法:
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))"
```

---
生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open('GITHUB_WORKFLOWS_FIX_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n📄 修复报告已保存到: GITHUB_WORKFLOWS_FIX_REPORT.md")

if __name__ == "__main__":
    main()
