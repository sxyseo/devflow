#!/usr/bin/env python3
"""
DevFlow 错误提示改进器
让错误信息更友好、更实用
"""

import re
from typing import Dict, List, Tuple

class ErrorHelper:
    """智能错误提示助手"""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
    
    def _load_error_patterns(self) -> Dict[str, dict]:
        """加载错误模式库"""
        return {
            # 权限错误
            'permission_denied': {
                'patterns': [
                    r'Permission denied',
                    r'permission denied',
                    r'权限被拒绝',
                    r'Access denied'
                ],
                'friendly_message': '❌ 权限不足',
                'solution': '💡 解决方案:',
                'actions': [
                    'chmod +x devflow.sh',
                    'chmod +x scripts/*.sh',
                    './scripts/fix-permissions.sh  # 一键修复'
                ],
                'doc_link': 'https://github.com/sxyseo/devflow#权限问题'
            },
            
            # 文件未找到
            'file_not_found': {
                'patterns': [
                    r'No such file or directory',
                    r'File not found',
                    r'文件不存在'
                ],
                'friendly_message': '❌ 找不到文件',
                'solution': '💡 解决方案:',
                'actions': [
                    '检查文件路径是否正确',
                    '运行: ls -la 查看当前目录',
                    '确认你是否在正确的目录'
                ]
            },
            
            # Python依赖缺失
            'python_module_not_found': {
                'patterns': [
                    r"ModuleNotFoundError: No module named '(\w+)'",
                    r"ImportError: No module named '(\w+)'"
                ],
                'friendly_message': '❌ Python包未安装',
                'solution': '💡 解决方案:',
                'actions': [
                    'pip3 install {module}',
                    'pip3 install -r requirements.txt  # 安装所有依赖'
                ],
                'extract': 'module'  # 提取模块名
            },
            
            # Git错误
            'git_not_repo': {
                'patterns': [
                    r'fatal: not a git repository',
                    r'不是git仓库'
                ],
                'friendly_message': '❌ 不是Git仓库',
                'solution': '💡 解决方案:',
                'actions': [
                    'git init',
                    '或者克隆一个仓库: git clone <url>'
                ]
            },
            
            # 网络错误
            'network_error': {
                'patterns': [
                    r'Connection refused',
                    r'Network is unreachable',
                    r'网络错误'
                ],
                'friendly_message': '❌ 网络连接失败',
                'solution': '💡 解决方案:',
                'actions': [
                    '检查网络连接',
                    'ping github.com',
                    '检查防火墙设置'
                ]
            },
            
            # API错误
            'api_error': {
                'patterns': [
                    r'API key',
                    r'authentication failed',
                    r'401 Unauthorized'
                ],
                'friendly_message': '❌ API认证失败',
                'solution': '💡 解决方案:',
                'actions': [
                    '检查API密钥是否正确',
                    '确认密钥未过期',
                    '查看配置: cat .env'
                ]
            },
            
            # 超时错误
            'timeout': {
                'patterns': [
                    r'Timeout',
                    r'timed out',
                    r'超时'
                ],
                'friendly_message': '❌ 执行超时',
                'solution': '💡 解决方案:',
                'actions': [
                    '增加超时时间',
                    '检查网络速度',
                    '尝试拆分任务'
                ]
            },
            
            # 内存错误
            'memory_error': {
                'patterns': [
                    r'MemoryError',
                    r'out of memory',
                    r'内存不足'
                ],
                'friendly_message': '❌ 内存不足',
                'solution': '💡 解决方案:',
                'actions': [
                    '关闭其他程序释放内存',
                    '减少并发数量',
                    '增加系统交换空间'
                ]
            }
        }
    
    def analyze_error(self, error_message: str) -> dict:
        """分析错误信息，返回友好提示"""
        
        for error_type, config in self.error_patterns.items():
            for pattern in config['patterns']:
                match = re.search(pattern, error_message, re.IGNORECASE)
                if match:
                    result = {
                        'type': error_type,
                        'friendly_message': config['friendly_message'],
                        'solution': config['solution'],
                        'actions': [],
                        'original_error': error_message
                    }
                    
                    # 提取动态内容
                    if 'extract' in config:
                        extracted = match.group(1) if match.lastindex else ''
                        for action in config['actions']:
                            result['actions'].append(action.format(module=extracted))
                    else:
                        result['actions'] = config['actions']
                    
                    # 添加文档链接
                    if 'doc_link' in config:
                        result['doc_link'] = config['doc_link']
                    
                    return result
        
        # 未知错误，返回通用建议
        return {
            'type': 'unknown',
            'friendly_message': '❌ 发生了未知错误',
            'solution': '💡 建议操作:',
            'actions': [
                '查看详细日志: tail -f .devflow/logs/iteration.log',
                '提交Issue: https://github.com/sxyseo/devflow/issues',
                '查看文档: cat VERIFICATION.md'
            ],
            'original_error': error_message
        }
    
    def format_friendly_error(self, error_message: str) -> str:
        """格式化友好的错误提示"""
        result = self.analyze_error(error_message)
        
        output = []
        output.append(result['friendly_message'])
        output.append('')
        output.append(result['solution'])
        
        for i, action in enumerate(result['actions'], 1):
            output.append(f'  {i}. {action}')
        
        if 'doc_link' in result:
            output.append('')
            output.append(f'📖 详细文档: {result["doc_link"]}')
        
        output.append('')
        output.append('─' * 50)
        output.append('原始错误:')
        output.append(error_message)
        
        return '\n'.join(output)
    
    def suggest_fix(self, error_type: str) -> List[str]:
        """根据错误类型建议修复方案"""
        if error_type in self.error_patterns:
            return self.error_patterns[error_type]['actions']
        return []

# 全局错误处理器
def handle_error(error: Exception, context: str = '') -> str:
    """处理异常，返回友好提示"""
    helper = ErrorHelper()
    
    error_msg = str(error)
    friendly = helper.format_friendly_error(error_msg)
    
    if context:
        return f"📍 上下文: {context}\n\n{friendly}"
    
    return friendly

# 自动修复脚本生成器
def generate_fix_script(error_type: str) -> str:
    """生成自动修复脚本"""
    scripts = {
        'permission_denied': '''#!/bin/bash
# 一键修复权限问题

echo "🔧 修复权限..."

chmod +x devflow.sh
chmod +x scripts/*.sh
chmod +x agents/*.py

echo "✅ 权限已修复！"
''',
        
        'python_module_not_found': '''#!/bin/bash
# 一键安装Python依赖

echo "📦 安装Python依赖..."

pip3 install -r requirements.txt

echo "✅ 依赖已安装！"
''',
        
        'git_not_repo': '''#!/bin/bash
# 初始化Git仓库

echo "📁 初始化Git仓库..."

git init
git add .
git commit -m "feat: 初始化项目"

echo "✅ Git仓库已初始化！"
'''
    }
    
    return scripts.get(error_type, '# 暂无自动修复脚本')

if __name__ == '__main__':
    # 测试错误提示
    print("🧪 测试错误提示改进器\n")
    
    test_errors = [
        "Permission denied: devflow.sh",
        "ModuleNotFoundError: No module named 'requests'",
        "fatal: not a git repository",
        "Connection refused",
        "Unknown error: something went wrong"
    ]
    
    helper = ErrorHelper()
    
    for error in test_errors:
        print("━" * 60)
        print(f"原始错误: {error}")
        print("━" * 60)
        print(helper.format_friendly_error(error))
        print("\n")
