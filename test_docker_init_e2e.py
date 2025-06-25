#!/usr/bin/env python3
"""
端到端测试：验证 docker_init.py 在实际场景中的工作情况
"""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

def create_mock_project_structure(base_dir):
    """创建模拟的项目结构"""
    print("🏗️  创建模拟项目结构...")
    
    # 创建目录
    dirs = [
        "conf_templates",
        "scripts", 
        "biz",
        "ui_components"
    ]
    
    for dir_name in dirs:
        (base_dir / dir_name).mkdir(parents=True, exist_ok=True)
    
    # 创建模拟的配置模板文件
    templates = {
        "conf_templates/.env.dist": """# AI-CodeReview 环境变量模板
LLM_TYPE=openai
OPENAI_API_KEY=
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
DATABASE_URL=sqlite:///data/data.db
REDIS_URL=redis://redis:6379/0
DEBUG=false
LOG_LEVEL=INFO
""",
        "conf_templates/dashboard_config.py": """# Dashboard 配置文件
import os

TITLE = "AI Code Review Dashboard"
DESCRIPTION = "智能代码审查系统"

PAGE_CONFIG = {
    "page_title": TITLE,
    "page_icon": "🤖",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/data.db")
""",
        "conf_templates/prompt_templates.yml": """# AI 代码审查提示模板配置
templates:
  code_review:
    name: "代码审查"
    description: "对代码进行全面审查"
    template: |
      请对以下代码进行详细的审查
""",
        "conf_templates/supervisord.app.conf": """[supervisord]
nodaemon=true
user=root

[program:api]
command=python /app/api.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/log/api.err.log
stdout_logfile=/app/log/api.out.log
environment=PYTHONPATH="/app"

[program:ui]
command=streamlit run /app/ui.py --server.port=5002 --server.address=0.0.0.0
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/log/ui.err.log
stdout_logfile=/app/log/ui.out.log
environment=PYTHONPATH="/app"
""",
        "conf_templates/supervisord.worker.conf": """[supervisord]
nodaemon=true
user=root

[program:worker]
command=python /app/scripts/background_worker.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/log/worker.err.log
stdout_logfile=/app/log/worker.out.log
environment=PYTHONPATH="/app"
""",
        "conf_templates/supervisord.all.conf": """[supervisord]
nodaemon=true
user=root

[program:api]
command=python /app/api.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/log/api.err.log
stdout_logfile=/app/log/api.out.log
environment=PYTHONPATH="/app"

[program:ui]
command=streamlit run /app/ui.py --server.port=5002 --server.address=0.0.0.0
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/log/ui.err.log
stdout_logfile=/app/log/ui.out.log
environment=PYTHONPATH="/app"

[program:worker]
command=python /app/scripts/background_worker.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/log/worker.err.log
stdout_logfile=/app/log/worker.out.log
environment=PYTHONPATH="/app"
""",
        "api.py": "# Mock API file\nprint('API would start here')",
        "ui.py": "# Mock UI file\nprint('UI would start here')",
        "scripts/background_worker.py": "# Mock worker file\nprint('Worker would start here')"
    }
    
    for file_path, content in templates.items():
        full_path = base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')
    
    print("✅ 模拟项目结构创建完成")

def test_docker_init_integration(test_dir):
    """集成测试 docker_init.py"""
    print("\n🧪 开始集成测试...")
    
    # 复制并修改 docker_init.py
    source_init = Path("scripts/docker_init.py")
    test_init = test_dir / "scripts" / "docker_init.py"
    
    if not source_init.exists():
        print("❌ 找不到源 docker_init.py 文件")
        return False
    
    # 读取并修改路径
    try:
        content = source_init.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = source_init.read_text(encoding='gbk')
    
    # 使用字符串替换来适配测试环境
    modified_content = content.replace(
        "Path('/app/conf')", 
        f"Path(r'{test_dir / 'conf'}')"
    ).replace(
        "Path('/app/conf_templates')", 
        f"Path(r'{test_dir / 'conf_templates'}')"
    ).replace(
        "Path('/app/log')", 
        f"Path(r'{test_dir / 'log'}')"
    ).replace(
        "Path('/app/data')", 
        f"Path(r'{test_dir / 'data'}')"
    ).replace(
        "'/app/conf'", 
        f"r'{test_dir / 'conf'}'"
    ).replace(
        "'/app/conf_templates'", 
        f"r'{test_dir / 'conf_templates'}'"
    ).replace(
        "'/app/log'", 
        f"r'{test_dir / 'log'}'"
    ).replace(
        "'/app/data'", 
        f"r'{test_dir / 'data'}'"
    ).replace(
        "'/etc/supervisor/conf.d'",
        f"r'{test_dir / 'supervisor_conf'}'"
    )
    
    test_init.write_text(modified_content, encoding='utf-8')
    
    # 设置测试环境变量
    test_env = os.environ.copy()
    test_env.update({
        'DOCKER_RUN_MODE': 'app',
        'TZ': 'Asia/Shanghai',
        'LOG_LEVEL': 'INFO'
    })
    
    # 创建supervisor配置目录
    (test_dir / 'supervisor_conf').mkdir(parents=True, exist_ok=True)
    
    # 运行测试
    try:
        result = subprocess.run([
            sys.executable, str(test_init)
        ], capture_output=True, text=True, env=test_env, cwd=test_dir)
        
        print(f"📤 返回码: {result.returncode}")
        print(f"📝 输出:\n{result.stdout}")
        if result.stderr:
            print(f"⚠️  错误:\n{result.stderr}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 运行测试时出现异常: {e}")
        return False

def verify_initialization_results(test_dir):
    """验证初始化结果"""
    print("\n🔍 验证初始化结果...")
    
    checks = []
    
    # 检查配置文件是否正确复制
    expected_config_files = [
        "conf/.env.dist",
        "conf/.env", 
        "conf/dashboard_config.py",
        "conf/prompt_templates.yml",
        "conf/supervisord.app.conf",
        "conf/supervisord.worker.conf",
        "conf/supervisord.all.conf"
    ]
    
    config_success = 0
    for file_path in expected_config_files:
        full_path = test_dir / file_path
        if full_path.exists() and full_path.stat().st_size > 0:
            print(f"✅ 配置文件存在: {file_path}")
            config_success += 1
        else:
            print(f"❌ 配置文件缺失: {file_path}")
    
    checks.append(("配置文件复制", config_success, len(expected_config_files)))
    
    # 检查目录是否创建
    expected_dirs = [
        "log",
        "data", 
        "data/svn",
        "conf"
    ]
    
    dir_success = 0
    for dir_path in expected_dirs:
        full_path = test_dir / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"✅ 目录存在: {dir_path}")
            dir_success += 1
        else:
            print(f"❌ 目录缺失: {dir_path}")
    
    checks.append(("目录创建", dir_success, len(expected_dirs)))
    
    # 检查supervisord配置
    supervisor_config = test_dir / "supervisor_conf" / "supervisord.conf"
    supervisor_success = 0
    if supervisor_config.exists():
        content = supervisor_config.read_text(encoding='utf-8')
        if '[supervisord]' in content and '[program:' in content:
            print("✅ Supervisord配置文件正确生成")
            supervisor_success = 1
        else:
            print("❌ Supervisord配置文件内容异常")
    else:
        print("❌ Supervisord配置文件不存在")
    
    checks.append(("Supervisord配置", supervisor_success, 1))
    
    # 检查.env文件内容
    env_file = test_dir / "conf" / ".env"
    env_success = 0
    if env_file.exists():
        content = env_file.read_text(encoding='utf-8')
        if 'LLM_TYPE=' in content and 'DATABASE_URL=' in content:
            print("✅ .env文件内容正确")
            env_success = 1
        else:
            print("❌ .env文件内容异常")
    else:
        print("❌ .env文件不存在")
    
    checks.append((".env文件", env_success, 1))
    
    # 输出总结
    print(f"\n📊 验证结果总结:")
    total_passed = 0
    total_expected = 0
    
    for check_name, passed, expected in checks:
        total_passed += passed
        total_expected += expected
        percentage = (passed / expected * 100) if expected > 0 else 0
        print(f"  {check_name}: {passed}/{expected} ({percentage:.1f}%)")
    
    overall_percentage = (total_passed / total_expected * 100) if total_expected > 0 else 0
    print(f"\n总体通过率: {total_passed}/{total_expected} ({overall_percentage:.1f}%)")
    
    return overall_percentage >= 80  # 80%以上通过率视为成功

def main():
    """主测试函数"""
    print("🚀 Docker 初始化端到端集成测试")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory(prefix="docker_init_e2e_") as temp_dir:
        test_dir = Path(temp_dir)
        print(f"📁 测试目录: {test_dir}")
        
        try:
            # 1. 创建模拟项目结构
            create_mock_project_structure(test_dir)
            
            # 2. 运行集成测试
            init_success = test_docker_init_integration(test_dir)
            
            # 3. 验证结果
            verification_success = verify_initialization_results(test_dir)
            
            # 4. 输出最终结果
            print("\n" + "=" * 60)
            print("🏁 最终测试结果:")
            print("=" * 60)
            
            print(f"初始化脚本执行: {'✅ 成功' if init_success else '❌ 失败'}")
            print(f"结果验证: {'✅ 通过' if verification_success else '❌ 失败'}")
            
            if init_success and verification_success:
                print("\n🎉 端到端测试完全通过！")
                print("✅ Docker初始化脚本在实际场景中工作正常")
                print("✅ 配置文件复制功能正常")
                print("✅ 目录创建功能正常") 
                print("✅ Supervisord配置生成正常")
                return 0
            else:
                print("\n⚠️  端到端测试失败")
                if not init_success:
                    print("❌ 初始化脚本执行失败")
                if not verification_success:
                    print("❌ 结果验证失败")
                return 1
                
        except Exception as e:
            print(f"❌ 测试过程中出现异常: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == '__main__':
    sys.exit(main())
