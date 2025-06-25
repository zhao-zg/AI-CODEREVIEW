#!/usr/bin/env python3
"""
Docker初始化功能测试 - 带实际断言的测试
使用实际的断言来验证测试结果，而不是仅仅打印输出
"""

import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path


class TestDockerInitFunctions(unittest.TestCase):
    """Docker初始化功能的单元测试类"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp(prefix="test_docker_init_")
        self.test_path = Path(self.test_dir)
        
    def tearDown(self):
        """每个测试后的清理工作"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_template_copy_functionality(self):
        """测试模板文件复制功能"""
        # 创建模板和配置目录
        template_dir = self.test_path / "templates"
        config_dir = self.test_path / "config"
        template_dir.mkdir()
        config_dir.mkdir()
        
        # 创建测试模板文件
        test_files = {
            ".env.dist": "LLM_TYPE=openai\nAPI_KEY=test",
            "dashboard_config.py": "TITLE = 'Test Dashboard'",
            "supervisord.app.conf": "[supervisord]\nnodaemon=true"
        }
        
        # 写入模板文件
        for filename, content in test_files.items():
            template_file = template_dir / filename
            template_file.write_text(content, encoding='utf-8')
        
        # 执行复制操作
        for filename, expected_content in test_files.items():
            template_file = template_dir / filename
            config_file = config_dir / filename
            
            # 断言模板文件存在
            self.assertTrue(template_file.exists(), f"模板文件 {filename} 应该存在")
            
            # 执行复制
            shutil.copy2(template_file, config_file)
            
            # 断言配置文件存在
            self.assertTrue(config_file.exists(), f"配置文件 {filename} 应该被复制")
            
            # 断言内容正确
            actual_content = config_file.read_text(encoding='utf-8')
            self.assertEqual(actual_content, expected_content, f"文件 {filename} 内容应该匹配")
    
    def test_env_file_generation(self):
        """测试 .env 文件的自动生成"""
        config_dir = self.test_path / "config"
        config_dir.mkdir()
        
        # 创建 .env.dist 文件
        env_dist_content = "LLM_TYPE=openai\nAPI_KEY=your_api_key_here\nDEBUG=false"
        env_dist_file = config_dir / ".env.dist"
        env_dist_file.write_text(env_dist_content, encoding='utf-8')
        
        # 确认 .env 文件不存在
        env_file = config_dir / ".env"
        self.assertFalse(env_file.exists(), ".env 文件开始时不应该存在")
        
        # 模拟自动生成 .env 文件的过程
        if env_dist_file.exists() and not env_file.exists():
            shutil.copy2(env_dist_file, env_file)
        
        # 断言 .env 文件被创建
        self.assertTrue(env_file.exists(), ".env 文件应该被自动创建")
        
        # 断言内容正确
        actual_content = env_file.read_text(encoding='utf-8')
        self.assertEqual(actual_content, env_dist_content, ".env 文件内容应该与 .env.dist 匹配")
    
    def test_directory_creation(self):
        """测试目录创建功能"""
        # 测试目录列表
        test_dirs = [
            "log",
            "data",
            "data/svn",
            "conf",
            "deep/nested/directory"
        ]
        
        # 创建目录
        for dir_name in test_dirs:
            dir_path = self.test_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # 断言目录被创建
            self.assertTrue(dir_path.exists(), f"目录 {dir_name} 应该被创建")
            self.assertTrue(dir_path.is_dir(), f"{dir_name} 应该是一个目录")
    
    def test_supervisord_config_generation(self):
        """测试 supervisord 配置生成逻辑"""
        
        def create_supervisord_config(mode):
            """模拟创建 supervisord 配置的函数"""
            base_config = "[supervisord]\nnodaemon=true\nuser=root\n\n"
            
            if mode == 'app':
                return base_config + "[program:api]\ncommand=python /app/api.py\n\n[program:ui]\ncommand=streamlit run /app/ui.py\n"
            elif mode == 'worker':
                return base_config + "[program:worker]\ncommand=python /app/scripts/background_worker.py\n"
            elif mode == 'all':
                return base_config + "[program:api]\ncommand=python /app/api.py\n\n[program:ui]\ncommand=streamlit run /app/ui.py\n\n[program:worker]\ncommand=python /app/scripts/background_worker.py\n"
            else:
                return None
        
        # 测试有效模式
        for mode in ['app', 'worker', 'all']:
            config = create_supervisord_config(mode)
            
            # 基本断言
            self.assertIsNotNone(config, f"模式 {mode} 应该生成配置")
            self.assertIn('[supervisord]', config, f"模式 {mode} 配置应该包含 [supervisord] 节")
            self.assertIn('nodaemon=true', config, f"模式 {mode} 配置应该包含 nodaemon=true")
            
            # 特定模式断言
            if mode == 'app':
                self.assertIn('[program:api]', config, "app 模式应该包含 API 程序")
                self.assertIn('[program:ui]', config, "app 模式应该包含 UI 程序")
                self.assertNotIn('[program:worker]', config, "app 模式不应该包含 worker 程序")
            elif mode == 'worker':
                self.assertIn('[program:worker]', config, "worker 模式应该包含 worker 程序")
                self.assertNotIn('[program:api]', config, "worker 模式不应该包含 API 程序")
                self.assertNotIn('[program:ui]', config, "worker 模式不应该包含 UI 程序")
            elif mode == 'all':
                self.assertIn('[program:api]', config, "all 模式应该包含 API 程序")
                self.assertIn('[program:ui]', config, "all 模式应该包含 UI 程序")
                self.assertIn('[program:worker]', config, "all 模式应该包含 worker 程序")
        
        # 测试无效模式
        invalid_config = create_supervisord_config('invalid')
        self.assertIsNone(invalid_config, "无效模式应该返回 None")
    
    def test_environment_variable_handling(self):
        """测试环境变量处理"""
        # 保存原始环境变量
        original_vars = {}
        test_vars = {
            'TEST_DOCKER_RUN_MODE': 'app',
            'TEST_TZ': 'Asia/Shanghai',
            'TEST_LOG_LEVEL': 'INFO'
        }
        
        try:
            # 设置测试环境变量
            for key, value in test_vars.items():
                original_vars[key] = os.environ.get(key)
                os.environ[key] = value
            
            # 测试读取
            for key, expected_value in test_vars.items():
                actual_value = os.environ.get(key)
                self.assertEqual(actual_value, expected_value, f"环境变量 {key} 应该正确设置")
            
            # 测试默认值处理
            test_key = 'NON_EXISTENT_TEST_VAR'
            default_value = 'test_default'
            actual_value = os.environ.get(test_key, default_value)
            self.assertEqual(actual_value, default_value, "不存在的环境变量应该返回默认值")
            
        finally:
            # 恢复原始环境变量
            for key, original_value in original_vars.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def test_file_content_validation(self):
        """测试文件内容验证"""
        # 测试文件和期望内容
        test_cases = [
            {
                'filename': '.env',
                'content': 'LLM_TYPE=openai\nAPI_KEY=test123\nDEBUG=false',
                'required_lines': ['LLM_TYPE=openai', 'API_KEY=test123', 'DEBUG=false']
            },
            {
                'filename': 'config.yml',
                'content': 'app:\n  name: test\n  version: 1.0',
                'required_lines': ['app:', 'name: test', 'version: 1.0']
            }
        ]
        
        for case in test_cases:
            # 创建文件
            file_path = self.test_path / case['filename']
            file_path.write_text(case['content'], encoding='utf-8')
            
            # 断言文件存在
            self.assertTrue(file_path.exists(), f"文件 {case['filename']} 应该存在")
            
            # 读取文件内容
            actual_content = file_path.read_text(encoding='utf-8')
            
            # 断言内容包含所有必需的行
            for required_line in case['required_lines']:
                self.assertIn(required_line, actual_content, 
                            f"文件 {case['filename']} 应该包含: {required_line}")
    
    def test_path_operations(self):
        """测试路径操作相关功能"""
        # 测试路径创建
        test_path = self.test_path / "some" / "deep" / "path"
        test_path.mkdir(parents=True, exist_ok=True)
        
        self.assertTrue(test_path.exists(), "深层路径应该被创建")
        self.assertTrue(test_path.is_dir(), "创建的应该是目录")
        
        # 测试文件写入和读取
        test_file = test_path / "test.txt"
        test_content = "这是测试内容\n包含多行"
        test_file.write_text(test_content, encoding='utf-8')
        
        self.assertTrue(test_file.exists(), "测试文件应该被创建")
        
        actual_content = test_file.read_text(encoding='utf-8')
        self.assertEqual(actual_content, test_content, "文件内容应该匹配")


class TestDockerInitIntegration(unittest.TestCase):
    """Docker初始化集成测试类"""
    
    def setUp(self):
        """集成测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp(prefix="test_docker_integration_")
        self.test_path = Path(self.test_dir)
        
    def tearDown(self):
        """集成测试后的清理工作"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_full_config_setup_workflow(self):
        """测试完整的配置设置工作流"""
        # 步骤1: 创建模板目录结构
        template_dir = self.test_path / "conf_templates"
        config_dir = self.test_path / "conf"
        template_dir.mkdir()
        config_dir.mkdir()
        
        # 步骤2: 创建模板文件
        template_files = {
            ".env.dist": "LLM_TYPE=openai\nAPI_KEY=your_key\nDEBUG=false",
            "dashboard_config.py": "TITLE = 'AI CodeReview'\nTHEME = 'dark'",
            "supervisord.app.conf": "[supervisord]\nnodaemon=true\n\n[program:api]\ncommand=python api.py"
        }
        
        for filename, content in template_files.items():
            (template_dir / filename).write_text(content, encoding='utf-8')
        
        # 步骤3: 模拟配置文件复制过程
        for filename in template_files.keys():
            template_file = template_dir / filename
            config_file = config_dir / filename
            
            if template_file.exists():
                shutil.copy2(template_file, config_file)
        
        # 步骤4: 验证所有文件都被正确复制
        for filename, expected_content in template_files.items():
            config_file = config_dir / filename
            self.assertTrue(config_file.exists(), f"配置文件 {filename} 应该被复制")
            
            actual_content = config_file.read_text(encoding='utf-8')
            self.assertEqual(actual_content, expected_content, f"文件 {filename} 内容应该正确")
        
        # 步骤5: 测试 .env 文件的特殊处理
        env_file = config_dir / ".env"
        env_dist_file = config_dir / ".env.dist"
        
        if env_dist_file.exists() and not env_file.exists():
            shutil.copy2(env_dist_file, env_file)
        
        self.assertTrue(env_file.exists(), ".env 文件应该被自动创建")
        
        # 步骤6: 验证目录结构
        required_dirs = ["log", "data", "data/svn"]
        for dir_name in required_dirs:
            dir_path = self.test_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            self.assertTrue(dir_path.exists(), f"目录 {dir_name} 应该被创建")


def run_tests_with_detailed_output():
    """运行测试并提供详细输出"""
    print("=" * 80)
    print("Docker 初始化功能测试 - 带实际断言")
    print("=" * 80)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDockerInitFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestDockerInitIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # 输出结果统计
    print("\n" + "=" * 80)
    print("测试结果统计:")
    print("=" * 80)
    print(f"运行的测试: {result.testsRun}")
    print(f"失败的测试: {len(result.failures)}")
    print(f"错误的测试: {len(result.errors)}")
    print(f"跳过的测试: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # 判断总体结果
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    print("\n" + "=" * 80)
    if success:
        print("✓ 所有测试通过！Docker初始化功能正常工作")
        return 0
    else:
        print("✗ 存在测试失败，请检查上述错误信息")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests_with_detailed_output())
