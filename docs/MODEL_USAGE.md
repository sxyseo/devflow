# 🤖 多模型支持指南 - Multi-Model Usage Guide

> **灵活配置多个AI模型，智能选择最优方案**

DevFlow支持多个AI提供商（Anthropic、OpenAI、本地模型），并根据任务类型自动选择最合适的模型，平衡成本、速度和质量。

## 📋 目录

- [快速开始](#快速开始)
- [配置模型](#配置模型)
- [任务类型映射](#任务类型映射)
- [选择策略](#选择策略)
- [故障转移](#故障转移)
- [性能监控](#性能监控)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装Anthropic SDK
pip install anthropic

# 安装OpenAI SDK
pip install openai

# 安装本地模型依赖（可选）
pip install requests
```

### 2. 配置API密钥

```bash
# Anthropic API密钥
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# OpenAI API密钥
export OPENAI_API_KEY="sk-xxxxx"
```

### 3. 启用模型

编辑 `devflow/config/model_config.json`，设置 `enabled: true` 启用需要的提供商：

```json
{
  "providers": {
    "anthropic": {
      "enabled": true,
      "api_key_env": "ANTHROPIC_API_KEY"
    },
    "openai": {
      "enabled": true,
      "api_key_env": "OPENAI_API_KEY"
    }
  }
}
```

## ⚙️ 配置模型

### 模型配置结构

每个模型包含以下配置项：

```json
{
  "model_id": "claude-3-5-sonnet-20241022",
  "name": "Claude 3.5 Sonnet",
  "type": "chat",
  "max_tokens": 200000,
  "input_cost_per_1k": 0.003,
  "output_cost_per_1k": 0.015,
  "capabilities": ["code_generation", "code_review", "architecture"],
  "priority": 1,
  "available": true
}
```

### 配置项说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `model_id` | string | 模型唯一标识符 |
| `name` | string | 模型显示名称 |
| `type` | string | 模型类型（chat, completion等） |
| `max_tokens` | int | 最大支持token数 |
| `input_cost_per_1k` | float | 输入成本（每1K token, USD） |
| `output_cost_per_1k` | float | 输出成本（每1K token, USD） |
| `capabilities` | array | 模型能力列表 |
| `priority` | int | 优先级（1=最高，数字越大优先级越低） |
| `available` | bool | 是否可用 |

### 添加新模型

在 `model_config.json` 中添加新模型：

```json
{
  "providers": {
    "anthropic": {
      "models": {
        "claude-3-6-sonnet-20250101": {
          "name": "Claude 3.6 Sonnet",
          "type": "chat",
          "max_tokens": 200000,
          "input_cost_per_1k": 0.003,
          "output_cost_per_1k": 0.015,
          "capabilities": ["code_generation", "analysis"],
          "priority": 1,
          "available": true
        }
      }
    }
  }
}
```

## 🎯 任务类型映射

### 支持的任务类型

系统根据任务类型自动选择最合适的模型：

| 任务类型 | 推荐模型 | 适用场景 |
|----------|----------|----------|
| `code_generation` | Claude 3.5 Sonnet, GPT-4 Turbo | 代码编写、功能实现 |
| `code_review` | Claude 3.5 Sonnet, GPT-4 Turbo | 代码审查、质量检查 |
| `architecture` | Claude 3.5 Sonnet, Claude 3 Opus | 架构设计、系统规划 |
| `analysis` | Claude 3.5 Sonnet, GPT-4 Turbo | 数据分析、问题诊断 |
| `writing` | Claude 3.5 Sonnet, GPT-4 Turbo | 文档编写、内容创作 |
| `simple_tasks` | Claude 3 Haiku, GPT-3.5 Turbo | 简单任务、快速响应 |
| `quick_response` | Claude 3 Haiku, GPT-3.5 Turbo | 实时响应、轻量处理 |

### 配置任务映射

在 `model_config.json` 中自定义任务映射：

```json
{
  "task_mappings": {
    "code_generation": {
      "preferred_models": [
        "anthropic/claude-3-5-sonnet-20241022",
        "openai/gpt-4-turbo"
      ],
      "fallback_models": [
        "openai/gpt-4",
        "anthropic/claude-3-opus-20240229"
      ],
      "min_capability": "code_generation"
    }
  }
}
```

### Agent映射

不同的Agent角色可以配置不同的任务类型：

```json
{
  "agent_mappings": {
    "dev-story": {
      "task_type": "code_generation",
      "model_override": null
    },
    "code-review": {
      "task_type": "code_review",
      "model_override": null
    },
    "architect": {
      "task_type": "architecture",
      "model_override": null
    }
  }
}
```

## 🎲 选择策略

### 策略类型

系统提供四种选择策略：

| 策略 | 说明 | 权重分配 |
|------|------|----------|
| `balanced` | 平衡成本、速度和质量 | 成本30% / 速度30% / 质量40% |
| `cost_optimized` | 优先考虑成本 | 成本70% / 速度20% / 质量10% |
| `quality_optimized` | 优先考虑质量 | 成本10% / 速度20% / 质量70% |
| `speed_optimized` | 优先考虑速度 | 成本20% / 速度70% / 质量10% |

### 配置策略

```json
{
  "selection_strategy": {
    "default": "balanced",
    "strategies": {
      "balanced": {
        "description": "Balance between cost, speed, and quality",
        "weights": {
          "cost": 0.3,
          "speed": 0.3,
          "quality": 0.4
        }
      },
      "cost_optimized": {
        "description": "Prefer cheaper models",
        "weights": {
          "cost": 0.7,
          "speed": 0.2,
          "quality": 0.1
        }
      }
    }
  }
}
```

### 使用策略

在代码中指定策略：

```python
from devflow.core.model_selector import ModelSelector, SelectionCriteria

# 创建选择条件
criteria = SelectionCriteria(
    task_type="code_generation",
    strategy=SelectionStrategy.COST_OPTIMIZED
)

# 选择模型
selector = ModelSelector(model_manager)
result = selector.select_model(criteria)
```

## 🔄 故障转移

### 自动故障转移

当模型请求失败时，系统会自动切换到备用模型：

```json
{
  "fallback_config": {
    "enabled": true,
    "max_attempts": 3,
    "retry_delay_seconds": 1,
    "fallback_on": [
      "rate_limit_error",
      "api_error",
      "timeout_error",
      "authentication_error"
    ]
  }
}
```

### 故障转移流程

1. **首选模型失败** → 自动切换到第一个备用模型
2. **备用模型失败** → 尝试下一个备用模型
3. **所有模型失败** → 记录错误并返回失败状态

### 手动触发故障转移

```python
from devflow.core.model_selector import ModelSelector, SelectionCriteria

selector = ModelSelector(model_manager)
criteria = SelectionCriteria(task_type="code_generation")

# 获取备用模型
fallback = selector.get_fallback_model(
    current_model_id="claude-3-5-sonnet-20241022",
    criteria=criteria
)
```

## 📊 性能监控

### 启用监控

```json
{
  "performance_tracking": {
    "enabled": true,
    "track_latency": true,
    "track_success_rate": true,
    "track_token_usage": true,
    "metrics_window_hours": 24,
    "min_samples_for_metrics": 10
  }
}
```

### 监控指标

系统会追踪以下指标：

| 指标 | 说明 |
|------|------|
| `latency_ms` | 请求延迟（毫秒） |
| `cost_usd` | 请求成本（美元） |
| `success_rate` | 成功率（百分比） |
| `token_usage` | Token使用量 |
| `p50/p95/p99_latency` | 延迟百分位数 |

### 查看指标

```python
from devflow.core.model_metrics import ModelMetrics

# 创建metrics实例
metrics = ModelMetrics()

# 获取模型统计
stats = metrics.get_model_statistics("claude-3-5-sonnet-20241022")
print(f"平均延迟: {stats.avg_latency_ms}ms")
print(f"成功率: {stats.success_rate * 100}%")
print(f"平均成本: ${stats.avg_cost_usd}")

# 获取总体摘要
summary = metrics.get_summary()
print(f"总请求数: {summary.total_requests}")
print(f"总成本: ${summary.total_cost_usd}")

# 导出指标
metrics.export_metrics(Path("metrics.json"))
```

### 按维度查看

```python
# 按任务类型查看
code_gen_stats = metrics.get_metrics_by_task_type("code_generation")

# 按Agent类型查看
agent_stats = metrics.get_metrics_by_agent_type("dev-story")

# 获取成本按提供商
provider_costs = metrics.get_cost_by_provider()
```

## 💡 最佳实践

### 1. 成本优化

```json
{
  "cost_optimization": {
    "enabled": true,
    "max_cost_per_task": 0.5,
    "prefer_cheaper_for_simple_tasks": true,
    "track_costs": true
  }
}
```

**建议：**
- 简单任务使用Haiku或GPT-3.5 Turbo
- 复杂任务使用Sonnet或GPT-4 Turbo
- 设置每任务最大成本限制

### 2. 质量保障

```json
{
  "task_mappings": {
    "architecture": {
      "preferred_models": [
        "anthropic/claude-3-5-sonnet-20241022",
        "anthropic/claude-3-opus-20240229"
      ],
      "fallback_models": ["openai/gpt-4"]
    }
  }
}
```

**建议：**
- 关键任务使用高质量模型
- 配置多个备用模型
- 启用性能监控追踪质量

### 3. 速度优化

```json
{
  "task_mappings": {
    "quick_response": {
      "preferred_models": [
        "anthropic/claude-3-haiku-20240307",
        "openai/gpt-3.5-turbo"
      ]
    }
  }
}
```

**建议：**
- 实时任务使用快速模型
- 批量任务可以使用较慢但更准确的模型
- 考虑使用本地模型减少网络延迟

### 4. 本地模型配置

使用Ollama运行本地模型：

```bash
# 安装Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型
ollama pull llama3:70b
ollama pull codellama:34b

# 启动服务
ollama serve
```

配置本地提供商：

```json
{
  "providers": {
    "local": {
      "enabled": true,
      "base_url": "http://localhost:11434",
      "models": {
        "llama3-70b": {
          "name": "Llama 3 70B",
          "type": "chat",
          "max_tokens": 8192,
          "input_cost_per_1k": 0.0,
          "output_cost_per_1k": 0.0,
          "capabilities": ["code_generation", "analysis"],
          "priority": 2,
          "available": true
        }
      }
    }
  }
}
```

## ❓ 常见问题

### Q: 如何选择合适的模型？

**A:** 根据任务复杂度选择：
- **简单任务**：Haiku、GPT-3.5 Turbo（成本低、速度快）
- **中等任务**：Sonnet、GPT-4 Turbo（平衡性能）
- **复杂任务**：Opus、GPT-4（高质量）

### Q: 如何降低API成本？

**A:** 多种策略：
1. 启用 `cost_optimized` 策略
2. 对简单任务使用便宜模型
3. 设置 `max_cost_per_task` 限制
4. 使用本地模型（零成本）

### Q: 模型失败时如何处理？

**A:** 系统会自动：
1. 检测失败类型（rate_limit、timeout等）
2. 切换到备用模型
3. 重试请求（最多3次）
4. 记录失败用于后续优化

### Q: 如何追踪模型使用情况？

**A:** 使用ModelMetrics：
```python
# 获取所有统计
stats = metrics.get_all_statistics()

# 导出详细报告
metrics.export_metrics(Path("report.json"))

# 查看最近错误
errors = metrics.get_recent_errors(limit=10)
```

### Q: 可否为特定Agent强制使用某个模型？

**A:** 可以，使用model_override：
```json
{
  "agent_mappings": {
    "architect": {
      "task_type": "architecture",
      "model_override": "anthropic/claude-3-opus-20240229"
    }
  }
}
```

### Q: 本地模型性能如何？

**A:** 取决于硬件：
- **优势**：零API成本、数据隐私、无网络延迟
- **劣势**：需要GPU、质量可能低于GPT-4/Claude
- **适用场景**：敏感代码、离线环境、成本敏感项目

## 🔗 相关文档

- [配置参考](../README.md) - 项目总体配置
- [Agent管理](./AGENT_GUIDE.md) - Agent配置和使用
- [性能优化](./PERFORMANCE.md) - 系统性能优化指南

## 📝 更新日志

- **2026-03-07**: 初始版本，支持Anthropic、OpenAI、本地模型
- 未来计划：支持更多提供商、自动A/B测试、模型性能预测
