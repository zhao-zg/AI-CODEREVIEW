#!/usr/bin/env python3
"""
Prompt模板配置功能演示脚本
展示新增的Prompt模板UI配置功能的完整特性
"""

import os
import yaml
from datetime import datetime

def demo_prompt_templates_features():
    """演示Prompt模板配置功能"""
    
    print("🎨 Prompt模板配置功能演示")
    print("=" * 60)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    demo_info = f"""
# 📝 Prompt模板配置功能演示

**演示时间**: {timestamp}
**功能**: AI-CodeReview 系统 Prompt模板UI配置

## 🎯 新增功能概览

### 1. 📝 Prompt模板配置界面
在 "⚙️ 配置管理" -> "📝 Prompt模板配置" 中新增了专门的配置界面：

- **系统Prompt模板编辑器**: 400像素高度的文本编辑器，支持自定义AI代码审查员的角色、目标、评分原则
- **用户Prompt模板编辑器**: 150像素高度的文本编辑器，用于定义代码diff和提交信息的输入格式
- **Jinja2模板语法支持**: 完整支持Jinja2模板语法，包括变量替换和条件语句

### 2. 🔍 模板变量说明
详细的变量说明帮助用户正确使用模板：

**系统Prompt可用变量：**
- `{{{{ style }}}}`: 审查风格 (professional/sarcastic/gentle/humorous)
- 支持条件语句: `{{% if style == 'professional' %}}`

**用户Prompt可用变量：**
- `{{{{ style }}}}`: 审查风格
- `{{diffs_text}}`: 结构化diff JSON内容
- `{{commits_text}}`: 提交历史信息

### 3. 👁️ 模板预览功能
- **风格选择器**: 可选择不同的审查风格进行预览
- **实时渲染**: 点击预览按钮即可看到模板的实际渲染效果
- **模板验证**: 自动验证Jinja2模板语法的正确性

### 4. 💾 配置保存机制
- **YAML格式保存**: 配置自动保存到 `conf/prompt_templates.yml` 文件
- **格式验证**: 保存前进行YAML格式验证
- **错误处理**: 完善的错误提示和处理机制

### 5. 📊 配置总览显示
在 "📋 配置总览" 标签页中新增了Prompt模板状态显示：
- **模板文件状态**: 显示文件是否存在
- **系统Prompt状态**: 显示字符数和配置状态
- **用户Prompt状态**: 显示字符数和配置状态

## 🎨 界面特性

### 📱 响应式设计
- **折叠式界面**: 使用可展开区域，节省界面空间
- **两列布局**: 变量说明和预览功能使用两列布局
- **友好提示**: 丰富的帮助信息和操作指导

### 🎯 用户体验
- **所见即所得**: 实时预览功能让用户直观看到模板效果
- **智能提示**: 详细的字段说明和示例
- **状态反馈**: 清晰的保存状态和错误提示

## 🔧 技术实现

### 文件结构
```
ui_components/pages.py    # 主UI配置文件（新增Prompt配置区域）
conf/prompt_templates.yml # Prompt模板配置文件
```

### 配置格式
```yaml
code_review_prompt:
  system_prompt: |
    # 系统Prompt内容（支持Jinja2语法）
  user_prompt: |
    # 用户Prompt内容（支持Jinja2语法）
```

### 核心功能
1. **模板编辑**: 使用 `st.text_area` 组件实现大文本编辑
2. **模板预览**: 使用 Jinja2 Template 进行实时渲染
3. **配置保存**: 使用 PyYAML 进行配置文件读写
4. **状态显示**: 在配置总览中展示模板配置状态

## 🚀 使用指南

### 1. 访问配置界面
1. 打开 AI-CodeReview 系统UI界面
2. 进入 "⚙️ 配置管理" 页面
3. 展开 "📝 Prompt模板配置" 区域

### 2. 编辑Prompt模板
1. 在 "系统Prompt模板" 文本框中编辑系统Prompt
2. 在 "用户Prompt模板" 文本框中编辑用户Prompt
3. 参考变量说明使用正确的模板语法

### 3. 预览模板效果
1. 选择想要预览的审查风格
2. 点击 "🔍 预览模板渲染效果" 按钮
3. 查看渲染后的模板内容

### 4. 保存配置
1. 点击 "💾 保存系统配置" 按钮
2. 等待保存成功提示
3. 在配置总览中验证保存状态

## 💡 使用建议

1. **备份原配置**: 修改前建议备份原有的 `conf/prompt_templates.yml` 文件
2. **逐步调试**: 使用预览功能逐步调试模板语法
3. **风格测试**: 针对不同审查风格测试模板的渲染效果
4. **版本管理**: 将Prompt模板纳入版本控制管理

---

**功能状态**: ✅ 已完成并测试通过
**集成状态**: ✅ 已集成到主配置界面
**测试覆盖**: ✅ 包含完整的自动化测试
"""
    
    return demo_info

def show_current_prompt_config():
    """显示当前的Prompt配置"""
    
    print("\n📄 当前Prompt模板配置")
    print("=" * 60)
    
    prompt_file = "conf/prompt_templates.yml"
    
    if os.path.exists(prompt_file):
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print("✅ 配置文件读取成功")
            
            if 'code_review_prompt' in config:
                code_review = config['code_review_prompt']
                
                system_prompt = code_review.get('system_prompt', '')
                user_prompt = code_review.get('user_prompt', '')
                
                print(f"📝 系统Prompt长度: {len(system_prompt)} 字符")
                print(f"👤 用户Prompt长度: {len(user_prompt)} 字符")
                
                # 显示部分内容
                if system_prompt:
                    print(f"\n📝 系统Prompt预览（前200字符）:")
                    print(f"```\n{system_prompt[:200]}...\n```")
                
                if user_prompt:
                    print(f"\n👤 用户Prompt预览:")
                    print(f"```\n{user_prompt}\n```")
                    
            else:
                print("⚠️ 配置文件中缺少 code_review_prompt 部分")
                
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
    else:
        print("⚠️ Prompt模板配置文件不存在")

def main():
    """主函数"""
    # 显示演示信息
    demo_info = demo_prompt_templates_features()
    
    # 保存演示文档
    demo_file = "PROMPT_TEMPLATES_UI_DEMO.md"
    with open(demo_file, 'w', encoding='utf-8') as f:
        f.write(demo_info)
    
    print(f"📋 演示文档已生成: {demo_file}")
    
    # 显示当前配置
    show_current_prompt_config()
    
    print(f"\n🎉 Prompt模板配置功能演示完成！")
    print(f"💡 访问 http://localhost:5002 查看实际界面效果")

if __name__ == "__main__":
    main()
