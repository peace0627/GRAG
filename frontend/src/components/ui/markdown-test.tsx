'use client';

import { Markdown } from './markdown';

export function MarkdownTest() {
  const testContent = `# Markdown 測試

這是一個 **粗體文字** 和 *斜體文字* 的測試。

## 程式碼測試

行內程式碼： \`const x = 42;\`

程式碼區塊：
\`\`\`python
def hello_world():
    print("Hello, World!")
    return True
\`\`\`

## 清單測試

### 無序清單
- 項目1
- 項目2
  - 子項目2.1
  - 子項目2.2

### 有序清單
1. 第一項
2. 第二項
3. 第三項

## 表格測試

| 欄位1 | 欄位2 | 欄位3 |
|-------|-------|-------|
| 數據1 | 數據2 | 數據3 |
| 數據4 | 數據5 | 數據6 |

## 其他格式

> 這是一個引用區塊，用於突出重要資訊。

[這是一個連結](https://example.com)

---

水平線測試
`;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Markdown 渲染測試</h1>
      <Markdown content={testContent} />
    </div>
  );
}
