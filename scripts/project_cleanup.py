#!/usr/bin/env python3
"""
AI-CodeReview-GitLab 项目文件清理和结构优化脚本
清理冗余文件，优化项目结构，提升可维护性
"""

import os
import shutil
from pathlib import Path
import json

class ProjectCleaner:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.deleted_files = []
        self.moved_files = []
        self.merged_files = []
        self.errors = []
    
    def analyze_project_structure(self):
        """分析项目结构，识别需要清理的文件"""
        print("🔍 分析项目结构...")
        
        # 识别重复和冗余文件
        duplicates = self.find_duplicates()
        redundant_reports = self.find_redundant_reports()
        
        print(f"📊 发现 {len(duplicates)} 个重复文件")
        print(f"📊 发现 {len(redundant_reports)} 个冗余报告文件")
        
        return duplicates, redundant_reports
    
    def find_duplicates(self):
        """查找重复文件"""
        duplicates = []
        
        # 检查重复的文档目录
        docs_dir = self.project_root / "docs"
        doc_dir = self.project_root / "doc"
        
        if docs_dir.exists() and doc_dir.exists():
            # 检查相同名称的文件
            for docs_file in docs_dir.glob("*.md"):
                doc_file = doc_dir / docs_file.name
                if doc_file.exists():
                    duplicates.append({
                        'primary': docs_file,
                        'duplicate': doc_file,
                        'type': 'documentation'
                    })
        
        return duplicates
    
    def find_redundant_reports(self):
        """查找冗余的报告文件"""
        redundant_reports = []
        
        # 查找根目录下的状态报告文件
        report_patterns = [
            "*_REPORT.md",
            "*_SUMMARY.md", 
            "*_COMPLETE.md",
            "*_STATUS.md",
            "*_GUIDE.md"
        ]
        
        for pattern in report_patterns:
            for file in self.project_root.glob(pattern):
                # 排除重要的文件
                if file.name not in ['README.md', 'PROJECT_STATUS.md']:
                    redundant_reports.append(file)
        
        return redundant_reports
    
    def clean_duplicate_documentation(self):
        """清理重复的文档文件"""
        print("\n📚 清理重复文档...")
        
        docs_dir = self.project_root / "docs"
        doc_dir = self.project_root / "doc"
        
        if not docs_dir.exists() or not doc_dir.exists():
            print("✅ 未发现重复文档目录")
            return
        
        # 合并 doc/ 到 docs/
        for doc_file in doc_dir.rglob("*"):
            if doc_file.is_file():
                relative_path = doc_file.relative_to(doc_dir)
                target_path = docs_dir / relative_path
                
                # 创建目标目录
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 检查是否已存在
                if target_path.exists():
                    # 比较文件内容，保留更完整的版本
                    if self.compare_and_merge_files(doc_file, target_path):
                        print(f"📝 合并文档: {relative_path}")
                        self.merged_files.append(str(relative_path))
                else:
                    # 直接移动
                    shutil.move(str(doc_file), str(target_path))
                    print(f"📦 移动文档: {relative_path}")
                    self.moved_files.append(f"{doc_file} -> {target_path}")
        
        # 删除空的 doc/ 目录
        if doc_dir.exists() and not any(doc_dir.iterdir()):
            shutil.rmtree(doc_dir)
            print(f"🗑️ 删除空目录: doc/")
            self.deleted_files.append("doc/")
    
    def compare_and_merge_files(self, file1, file2):
        """比较并合并两个文件，保留更完整的版本"""
        try:
            with open(file1, 'r', encoding='utf-8') as f1:
                content1 = f1.read()
            with open(file2, 'r', encoding='utf-8') as f2:
                content2 = f2.read()
            
            # 如果内容相同，无需操作
            if content1 == content2:
                return False
            
            # 如果其中一个文件更长，保留更长的
            if len(content1) > len(content2):
                shutil.copy2(file1, file2)
                return True
            elif len(content2) > len(content1):
                return False
            
            # 长度相同，保留修改时间更新的
            if file1.stat().st_mtime > file2.stat().st_mtime:
                shutil.copy2(file1, file2)
                return True
            
            return False
        except Exception as e:
            self.errors.append(f"比较文件失败: {file1} vs {file2} - {e}")
            return False
    
    def clean_redundant_reports(self):
        """清理冗余的报告文件"""
        print("\n📋 清理冗余报告文件...")
        
        # 要保留的重要文件
        keep_files = {
            'README.md',
            'PROJECT_STATUS.md',
            'CHANGELOG.md',
            'LICENSE'
        }
        
        # 要清理的报告文件模式
        cleanup_patterns = [
            "*_REPORT.md",
            "*_SUMMARY.md",
            "*_COMPLETE.md",
            "*_GUIDE.md",
            "PYTHON_UPGRADE*.md",
            "YAML_SYNTAX_FIX.md",
            "FIX_*.md",
            "CONFIG_*.md"
        ]
        
        cleaned_count = 0
        for pattern in cleanup_patterns:
            for file in self.project_root.glob(pattern):
                if file.name not in keep_files:
                    try:
                        file.unlink()
                        print(f"🗑️ 删除报告文件: {file.name}")
                        self.deleted_files.append(file.name)
                        cleaned_count += 1
                    except Exception as e:
                        self.errors.append(f"删除文件失败: {file.name} - {e}")
        
        print(f"✅ 清理了 {cleaned_count} 个冗余报告文件")
    
    def clean_docker_compose_files(self):
        """清理多余的 Docker Compose 文件"""
        print("\n🐳 清理 Docker Compose 文件...")
        
        # 检查是否有多个 docker-compose 文件
        compose_files = list(self.project_root.glob("docker-compose*.yml"))
        
        if len(compose_files) <= 2:
            print("✅ Docker Compose 文件数量合理")
            return
        
        # 保留主要的两个文件
        keep_files = {
            'docker-compose.yml',
            'docker-compose.dockerhub.yml'
        }
        
        for compose_file in compose_files:
            if compose_file.name not in keep_files:
                try:
                    compose_file.unlink()
                    print(f"🗑️ 删除多余的 Compose 文件: {compose_file.name}")
                    self.deleted_files.append(compose_file.name)
                except Exception as e:
                    self.errors.append(f"删除 Compose 文件失败: {compose_file.name} - {e}")
    
    def optimize_scripts_directory(self):
        """优化 scripts 目录结构"""
        print("\n🔧 优化 scripts 目录...")
        
        scripts_dir = self.project_root / "scripts"
        if not scripts_dir.exists():
            return
        
        # 检查脚本功能重复
        verify_scripts = list(scripts_dir.glob("verify_build_config*.py"))
        
        if len(verify_scripts) > 1:
            # 保留功能更完整的版本
            main_script = None
            for script in verify_scripts:
                if "simple" not in script.name:
                    main_script = script
                    break
            
            if main_script:
                for script in verify_scripts:
                    if script != main_script:
                        try:
                            script.unlink()
                            print(f"🗑️ 删除重复验证脚本: {script.name}")
                            self.deleted_files.append(script.name)
                        except Exception as e:
                            self.errors.append(f"删除脚本失败: {script.name} - {e}")
    
    def clean_empty_directories(self):
        """清理空目录"""
        print("\n📁 清理空目录...")
        
        empty_dirs = []
        for root, dirs, files in os.walk(self.project_root):
            if not dirs and not files:
                empty_dirs.append(Path(root))
        
        for empty_dir in empty_dirs:
            try:
                empty_dir.rmdir()
                print(f"🗑️ 删除空目录: {empty_dir.relative_to(self.project_root)}")
                self.deleted_files.append(str(empty_dir.relative_to(self.project_root)))
            except Exception as e:
                self.errors.append(f"删除空目录失败: {empty_dir} - {e}")
    
    def create_cleanup_summary(self):
        """创建清理总结报告"""
        print("\n📊 生成清理总结...")
        
        summary = {
            "cleanup_date": "2025-06-23",
            "deleted_files": self.deleted_files,
            "moved_files": self.moved_files,
            "merged_files": self.merged_files,
            "errors": self.errors,
            "statistics": {
                "deleted_count": len(self.deleted_files),
                "moved_count": len(self.moved_files), 
                "merged_count": len(self.merged_files),
                "error_count": len(self.errors)
            }
        }
        
        # 创建清理报告
        report_content = f"""# 🧹 项目文件清理报告

## 📅 清理时间
**执行日期:** 2025-06-23  
**清理状态:** {'✅ 完成' if not self.errors else '⚠️ 部分完成'}  

## 📊 清理统计

- **删除文件:** {len(self.deleted_files)} 个
- **移动文件:** {len(self.moved_files)} 个  
- **合并文件:** {len(self.merged_files)} 个
- **错误数量:** {len(self.errors)} 个

## 🗑️ 已删除的文件

{chr(10).join([f"- {f}" for f in self.deleted_files]) if self.deleted_files else "无删除文件"}

## 📦 已移动的文件

{chr(10).join([f"- {f}" for f in self.moved_files]) if self.moved_files else "无移动文件"}

## 📝 已合并的文件

{chr(10).join([f"- {f}" for f in self.merged_files]) if self.merged_files else "无合并文件"}

{'## ❌ 处理错误' + chr(10) + chr(10).join([f"- {e}" for e in self.errors]) if self.errors else ''}

## 🎯 优化效果

### 项目结构更清晰
- 移除冗余的状态报告文件
- 合并重复的文档目录
- 清理多余的配置文件

### 维护性提升
- 减少文件冗余
- 统一文档结构
- 简化项目导航

## 📁 优化后的项目结构

```
AI-Codereview-Gitlab/
├── 📂 核心文件
│   ├── api.py              # Flask API 服务
│   ├── ui.py               # Streamlit Web 界面
│   ├── quick_start.py      # 快速启动脚本
│   └── requirements.txt    # 依赖配置
│
├── 📂 Docker 配置
│   ├── Dockerfile                    # 容器构建
│   ├── docker-compose.yml           # 默认部署
│   └── docker-compose.dockerhub.yml # Docker Hub 部署
│
├── 📂 业务逻辑
│   └── biz/                # 核心业务模块
│
├── 📂 配置文件
│   └── conf/               # 应用配置
│
├── 📂 脚本工具
│   └── scripts/            # 管理和部署脚本
│
├── 📂 测试文件
│   └── tests/              # 测试代码
│
├── 📂 文档资料
│   └── docs/               # 统一的文档目录
│
├── 📂 数据和日志
│   ├── data/               # 数据存储
│   └── log/                # 日志文件
│
└── 📄 项目说明
    ├── README.md           # 项目主文档
    ├── PROJECT_STATUS.md   # 项目状态
    └── CHANGELOG.md        # 更新记录
```

---

*🎉 项目清理完成！结构更清晰，维护更容易。*
"""
        
        # 写入报告文件
        report_file = self.project_root / "PROJECT_CLEANUP_FINAL.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return summary
    
    def run_cleanup(self):
        """执行完整的清理流程"""
        print("🧹 开始 AI-CodeReview-GitLab 项目文件清理")
        print("=" * 60)
        
        try:
            # 分析项目结构
            self.analyze_project_structure()
            
            # 执行清理操作
            self.clean_duplicate_documentation()
            self.clean_redundant_reports() 
            self.clean_docker_compose_files()
            self.optimize_scripts_directory()
            self.clean_empty_directories()
            
            # 生成清理报告
            summary = self.create_cleanup_summary()
            
            print("\n" + "=" * 60)
            print("🎉 项目清理完成!")
            print(f"📊 删除文件: {len(self.deleted_files)} 个")
            print(f"📦 移动文件: {len(self.moved_files)} 个")
            print(f"📝 合并文件: {len(self.merged_files)} 个")
            
            if self.errors:
                print(f"⚠️ 遇到错误: {len(self.errors)} 个")
                for error in self.errors:
                    print(f"   • {error}")
            else:
                print("✅ 清理过程无错误")
            
            print("\n📋 详细报告已保存到: PROJECT_CLEANUP_FINAL.md")
            
            return True
            
        except Exception as e:
            print(f"\n💥 清理过程中出现严重错误: {e}")
            return False

def main():
    """主函数"""
    cleaner = ProjectCleaner()
    success = cleaner.run_cleanup()
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
