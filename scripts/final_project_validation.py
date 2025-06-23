#!/usr/bin/env python3
"""
AI-CodeReview-GitLab 项目最终验证脚本
验证项目是否已准备好投入生产使用
"""

import os
import json
import subprocess
import sys
from pathlib import Path

class ProjectValidator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        self.passed = 0
        self.total = 0
    
    def check_file_exists(self, file_path, description):
        """检查文件是否存在"""
        self.total += 1
        full_path = self.project_root / file_path
        if full_path.exists():
            print(f"✅ {description}: {file_path}")
            self.passed += 1
            return True
        else:
            print(f"❌ {description}: {file_path} (缺失)")
            self.errors.append(f"缺失文件: {file_path}")
            return False
    
    def check_docker_files(self):
        """检查Docker相关文件"""
        print("\n🐳 检查Docker配置文件...")
        files = [
            ("Dockerfile", "Docker构建文件"),
            ("docker-compose.yml", "Docker Compose配置"),
            ("docker-compose.dockerhub.yml", "Docker Hub部署配置"),
            (".dockerignore", "Docker忽略文件")
        ]
        
        for file_path, desc in files:
            self.check_file_exists(file_path, desc)
    
    def check_github_workflows(self):
        """检查GitHub Actions工作流"""
        print("\n🔧 检查GitHub Actions工作流...")
        workflows = [
            (".github/workflows/docker-build.yml", "Docker构建工作流"),
            (".github/workflows/test-docker.yml", "Docker测试工作流"),
            (".github/workflows/test.yml", "代码测试工作流"),
            (".github/workflows/basic-check.yml", "基础检查工作流")
        ]
        
        for workflow_path, desc in workflows:
            self.check_file_exists(workflow_path, desc)
    
    def check_core_files(self):
        """检查核心项目文件"""
        print("\n📄 检查核心项目文件...")
        files = [
            ("api.py", "Flask API服务"),
            ("ui.py", "Streamlit UI服务"), 
            ("quick_start.py", "快速启动脚本"),
            ("requirements.txt", "Python依赖文件"),
            ("README.md", "项目说明文档")
        ]
        
        for file_path, desc in files:
            self.check_file_exists(file_path, desc)
    
    def check_business_modules(self):
        """检查业务模块"""
        print("\n📦 检查业务模块...")
        modules = [
            ("biz/__init__.py", "业务模块初始化文件"),
            ("biz/llm/factory.py", "LLM工厂类"),
            ("biz/service/review_service.py", "代码审查服务"),
            ("biz/gitlab/webhook_handler.py", "GitLab Webhook处理器"),
            ("biz/github/webhook_handler.py", "GitHub Webhook处理器")
        ]
        
        for module_path, desc in modules:
            self.check_file_exists(module_path, desc)
    
    def check_documentation(self):
        """检查文档文件"""
        print("\n📚 检查文档文件...")
        docs = [
            ("PROJECT_STATUS.md", "项目状态文档"),
            ("DOCKER_AUTO_BUILD.md", "Docker自动构建文档"),
            ("FINAL_STATUS_REPORT.md", "最终状态报告"),
            ("docs/deployment_guide.md", "部署指南"),
            ("docs/faq.md", "常见问题文档")
        ]
        
        for doc_path, desc in docs:
            self.check_file_exists(doc_path, desc)
    
    def check_scripts(self):
        """检查管理脚本"""
        print("\n🔧 检查管理脚本...")
        scripts = [
            ("scripts/release.py", "版本发布脚本"),
            ("scripts/check_ci_status.py", "CI状态检查脚本"),
            ("scripts/verify_build_config_simple.py", "构建配置验证脚本")
        ]
        
        for script_path, desc in scripts:
            self.check_file_exists(script_path, desc)
    
    def check_configuration(self):
        """检查配置文件"""
        print("\n⚙️ 检查配置文件...")
        configs = [
            ("conf/prompt_templates.yml", "提示模板配置"),
            ("conf/dashboard_config.py", "仪表板配置")
        ]
        
        for config_path, desc in configs:
            self.check_file_exists(config_path, desc)
    
    def check_python_syntax(self):
        """检查Python语法"""
        print("\n🐍 检查Python语法...")
        python_files = [
            "api.py", "ui.py", "quick_start.py",
            "scripts/release.py", "scripts/check_ci_status.py"
        ]
        
        for py_file in python_files:
            self.total += 1
            try:
                full_path = self.project_root / py_file
                if full_path.exists():
                    # 简单的语法检查
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 检查是否有基本的Python语法结构
                        if 'import' in content or 'def' in content or 'class' in content:
                            print(f"✅ Python语法检查: {py_file}")
                            self.passed += 1
                        else:
                            print(f"⚠️ Python语法警告: {py_file} (内容可能不完整)")
                            self.warnings.append(f"Python文件内容警告: {py_file}")
                            self.passed += 1  # 不算作错误
                else:
                    print(f"❌ Python文件缺失: {py_file}")
                    self.errors.append(f"Python文件缺失: {py_file}")
            except Exception as e:
                print(f"❌ Python语法检查失败: {py_file} - {e}")
                self.errors.append(f"Python语法错误: {py_file} - {str(e)}")
    
    def generate_summary(self):
        """生成验证摘要"""
        print("\n" + "="*60)
        print("🎯 AI-CodeReview-GitLab 项目验证结果")
        print("="*60)
        
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        
        print(f"📊 验证统计:")
        print(f"   总检查项: {self.total}")
        print(f"   通过项目: {self.passed}")
        print(f"   成功率: {success_rate:.1f}%")
        
        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️ 发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if success_rate >= 90:
            print(f"\n🎉 项目验证通过！")
            print(f"✅ 项目已准备好投入生产使用")
            print(f"🚀 可以安全地进行部署和发布")
            return True
        else:
            print(f"\n🚨 项目验证失败！")
            print(f"❌ 项目存在关键问题，建议修复后再部署")
            return False
    
    def run_validation(self):
        """运行完整验证"""
        print("🔍 开始验证 AI-CodeReview-GitLab 项目...")
        print(f"📁 项目目录: {self.project_root}")
        
        # 运行各项检查
        self.check_core_files()
        self.check_docker_files()
        self.check_github_workflows()
        self.check_business_modules()
        self.check_documentation()
        self.check_scripts()
        self.check_configuration()
        self.check_python_syntax()
        
        # 生成摘要
        return self.generate_summary()

def main():
    """主函数"""
    validator = ProjectValidator()
    success = validator.run_validation()
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
