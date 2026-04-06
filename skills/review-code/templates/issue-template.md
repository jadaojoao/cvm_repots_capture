# Issue Template

问题记录模板。

## Single Issue Template

````markdown
#### {{severity_emoji}} [{{id}}] {{category}}

- **严重程度**: {{severity}}
- **维度**: {{dimension}}
- **文件**: `{{file}}`{{#if line}}:{{line}}{{/if}}
- **描述**: {{description}}

{{#if code_snippet}}
**问题代码**:
```{{language}}
{{code_snippet}}
```
{{/if}}

**建议**: {{recommendation}}

{{#if fix_example}}
**修复示例**:
```{{language}}
{{fix_example}}
```
{{/if}}

{{#if references}}
**参考资料**:
{{#each references}}
- {{this}}
{{/each}}
{{/if}}
````

## Issue Object Schema

```typescript
interface Issue {
  id: string;           // e.g., "SEC-001"
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  dimension: string;    // e.g., "security"
  category: string;     // e.g., "xss-risk"
  file: string;         // e.g., "src/utils/render.ts"
  line?: number;        // e.g., 42
  column?: number;      // e.g., 15
  code_snippet?: string;
  description: string;
  recommendation: string;
  fix_example?: string;
  references?: string[];
}
```

## ID Generation

```javascript
function generateIssueId(dimension, counter) {
  const prefixes = {
    correctness: 'CORR',
    readability: 'READ',
    performance: 'PERF',
    security: 'SEC',
    testing: 'TEST',
    architecture: 'ARCH'
  };
  
  const prefix = prefixes[dimension] || 'MISC';
  const number = String(counter).padStart(3, '0');
  
  return `${prefix}-${number}`;
}
```

## Severity Emojis

```javascript
const SEVERITY_EMOJI = {
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '🔵',
  info: '⚪'
};
```

## Issue Categories by Dimension

### Correctness
- `null-check` - 缺少空值检查
- `boundary` - 边界条件未处理
- `error-handling` - 错误处理不当
- `type-safety` - 类型安全问题
- `logic-error` - 逻辑错误
- `resource-leak` - 资源泄漏

### Security
- `injection` - 注入风险
- `xss` - 跨站脚本
- `hardcoded-secret` - 硬编码密钥
- `auth` - 认证授权
- `sensitive-data` - 敏感数据

### Performance
- `complexity` - 复杂度问题
- `n+1-query` - N+1 查询
- `memory-leak` - 内存泄漏
- `blocking-io` - 阻塞 I/O
- `inefficient-algorithm` - 低效算法

### Readability
- `naming` - 命名问题
- `function-length` - 函数过长
- `nesting-depth` - 嵌套过深
- `comments` - 注释问题
- `duplication` - 代码重复

### Testing
- `coverage` - 覆盖不足
- `boundary-test` - 缺少边界测试
- `test-isolation` - 测试不独立
- `flaky-test` - 不稳定测试

### Architecture
- `layer-violation` - 层次违规
- `circular-dependency` - 循环依赖
- `coupling` - 耦合过紧
- `srp-violation` - 单一职责违规

## Example Issues

### Critical Security Issue

```json
{
  "id": "SEC-001",
  "severity": "critical",
  "dimension": "security",
  "category": "xss",
  "file": "src/components/Comment.tsx",
  "line": 25,
  "code_snippet": "element.innerHTML = userComment;",
  "description": "直接使用 innerHTML 插入用户输入，存在 XSS 攻击风险",
  "recommendation": "使用 textContent 或对用户输入进行 HTML 转义",
  "fix_example": "element.textContent = userComment;\n// 或\nelement.innerHTML = DOMPurify.sanitize(userComment);",
  "references": [
    "https://owasp.org/www-community/xss-filter-evasion-cheatsheet"
  ]
}
```

### High Correctness Issue

```json
{
  "id": "CORR-003",
  "severity": "high",
  "dimension": "correctness",
  "category": "error-handling",
  "file": "src/services/api.ts",
  "line": 42,
  "code_snippet": "try {\n  await fetchData();\n} catch (e) {}",
  "description": "空的 catch 块会静默吞掉错误，导致问题难以发现和调试",
  "recommendation": "记录错误日志或重新抛出异常",
  "fix_example": "try {\n  await fetchData();\n} catch (e) {\n  console.error('Failed to fetch data:', e);\n  throw e;\n}"
}
```

### Medium Readability Issue

```json
{
  "id": "READ-007",
  "severity": "medium",
  "dimension": "readability",
  "category": "function-length",
  "file": "src/utils/processor.ts",
  "line": 15,
  "description": "函数 processData 有 150 行，超过推荐的 50 行限制，难以理解和维护",
  "recommendation": "将函数拆分为多个小函数，每个函数负责单一职责",
  "fix_example": "// 拆分为:\nfunction validateInput(data) { ... }\nfunction transformData(data) { ... }\nfunction saveData(data) { ... }"
}
```
