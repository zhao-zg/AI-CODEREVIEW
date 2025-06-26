#!/usr/bin/env python3
"""
临时测试服务器 - 验证中文 JSON 输出
"""
from flask import Flask, Response
import json

app = Flask(__name__)

# 配置 Flask 应用以支持中文输出
app.config['JSON_AS_ASCII'] = False

@app.route('/svn/check', methods=['GET', 'POST'])
def test_svn_check():
    """测试 SVN 检查接口中文输出"""
    message = 'SVN检查已启动，将异步处理最近 24 小时的提交。'
    
    # 方法 1: 使用 Flask 配置
    # return jsonify({'message': message})
    
    # 方法 2: 手动构建 JSON 响应
    response_data = {'message': message}
    json_str = json.dumps(response_data, ensure_ascii=False, indent=2)
    return Response(json_str, content_type='application/json; charset=utf-8')

@app.route('/test/config')
def test_config():
    """测试配置"""
    return {
        'JSON_AS_ASCII': app.config.get('JSON_AS_ASCII'),
        'message': '测试中文输出：这是一条包含中文的消息'
    }

if __name__ == '__main__':
    print("🚀 启动临时测试服务器...")
    print("📋 测试地址: http://127.0.0.1:5002/svn/check")
    app.run(host='127.0.0.1', port=5002, debug=True)
