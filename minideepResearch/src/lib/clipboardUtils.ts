import { marked } from "marked";
import katex from "katex";

// ==========================================
// 1. Word HTML 模板
// ==========================================
const WORD_HTML_TEMPLATE = (content: string) => `
<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office" 
      xmlns:w="urn:schemas-microsoft-com:office:word" 
      xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
<head>
<meta charset="utf-8">
<style>
  body { font-family: 'Calibri', sans-serif; font-size: 11pt; color: #333; line-height: 1.6; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; border: 1px solid #000; }
  td, th { border: 1px solid #999; padding: 8px; text-align: left; }
  th { background-color: #f3f4f6; font-weight: bold; }
  pre { background: #f5f5f5; padding: 10px; border-radius: 4px; }
  li { margin-bottom: 4px; }
</style>
</head>
<body>
${content}
</body>
</html>
`;

// ==========================================
// 2. 针对 Token 对象的自定义渲染器
// ==========================================
const renderer = new marked.Renderer();

/**
 * 标题 (Heading)
 * Log结构: { type: 'heading', depth: 3, text: '...' }
 */
// @ts-ignore
renderer.heading = function (token) {
  // 兼容性处理：如果传入的是 text, level (旧版行为)，则 token 为 text
  if (typeof token === 'string') {
    return `<h${arguments[1]} style="font-size: 16px; font-weight: bold; margin: 16px 0 8px;">${token}</h${arguments[1]}>`;
  }

  const level = token.depth;
  const fontSize = level === 1 ? "24px" : level === 2 ? "20px" : "16px";
  // 使用 this.parser.parseInline 解析标题内部的 Markdown (如 **加粗**)
  // @ts-ignore
  const text = this.parser.parseInline(token.tokens);

  return `<h${level} style="font-size: ${fontSize}; font-weight: bold; color: #111827; margin-top: 16px; margin-bottom: 8px;">${text}</h${level}>`;
};

/**
 * 列表 (List)
 * Log结构: { type: 'list', ordered: false, items: [...] }
 */
// @ts-ignore
renderer.list = function (token) {
  if (typeof token === 'string') return `<ul>${token}</ul>`; // 旧版兼容

  const tag = token.ordered ? "ol" : "ul";

  // 必须手动渲染 items
  let body = "";
  if (token.items && token.items.length > 0) {
    // @ts-ignore
    body = token.items.map(item => {
      // 递归解析列表项内容
      // @ts-ignore
      const itemContent = this.parser.parse(item.tokens);
      return `<li style="margin-bottom: 4px;">${itemContent}</li>`;
    }).join("");
  }

  return `<${tag} style="padding-left: 30px; margin: 8px 0;">${body}</${tag}>`;
};

/**
 * 代码块 (Code)
 * Log结构: { type: 'code', text: '...', lang: '...' }
 */
// @ts-ignore
renderer.code = function (token) {
  if (typeof token === 'string') return `<pre>${token}</pre>`; // 旧版兼容

  const codeText = token.text || "";
  const safeCode = codeText.replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // 使用 Table 模拟代码背景 (Word 兼容性最佳方案)
  return `
    <table width="100%" style="border: 1px solid #e5e7eb; background-color: #f9fafb; margin: 10px 0;">
      <tr>
        <td style="padding: 12px; font-family: Consolas, monospace; font-size: 10pt; color: #1f2937; border: none;">
          <pre style="margin: 0; white-space: pre-wrap;">${safeCode}</pre>
        </td>
      </tr>
    </table>
  `;
};

/**
 * 表格 (Table) - 之前报错的根源之一
 * Log结构: { type: 'table', header: [...], rows: [...] }
 */
// @ts-ignore
renderer.table = function (token) {
  if (typeof token === 'string') return `<table>${token}</table>`; // 旧版兼容

  let headerHtml = "";
  let bodyHtml = "";

  // 1. 渲染表头
  if (token.header) {
    // @ts-ignore
    const cellHtml = token.header.map(cell => {
      // @ts-ignore
      const content = this.parser.parseInline(cell.tokens);
      return `<th style="border: 1px solid #999; padding: 8px; background-color: #f3f4f6; font-weight: bold; text-align: left;">${content}</th>`;
    }).join("");
    headerHtml = `<thead><tr>${cellHtml}</tr></thead>`;
  }

  // 2. 渲染表体
  if (token.rows) {
    // @ts-ignore
    bodyHtml = token.rows.map(row => {
      // @ts-ignore
      const rowHtml = row.map(cell => {
        // @ts-ignore
        const content = this.parser.parseInline(cell.tokens);
        return `<td style="border: 1px solid #999; padding: 8px;">${content}</td>`;
      }).join("");
      return `<tr>${rowHtml}</tr>`;
    }).join("");
    bodyHtml = `<tbody>${bodyHtml}</tbody>`;
  }

  return `<table style="border-collapse: collapse; width: 100%; border: 1px solid #000; margin: 10px 0;">${headerHtml}${bodyHtml}</table>`;
};

/**
 * 链接 (Link)
 */
// @ts-ignore
renderer.link = function (token) {
    // 如果是旧版: href, title, text
    if (typeof token === 'string') {
         return `<a href="${token}" style="color: #2563EB; text-decoration: underline;">${arguments[2]}</a>`;
    }
    // 新版 Token: { href, title, text, tokens }
    const href = token.href;
    const text = token.text;
    return `<a href="${href}" style="color: #2563EB; text-decoration: underline;">${text}</a>`;
}

/**
 * 加粗 (Strong)
 */
// @ts-ignore
renderer.strong = function (token) {
    if (typeof token === 'string') return `<span style="font-weight: bold;">${token}</span>`;
    const text = token.text;
    return `<span style="font-weight: bold; color: #000000;">${text}</span>`;
}

marked.use({ renderer });

// ==========================================
// 3. 数学公式预处理 (LaTeX -> MathML)
// ==========================================
const processMath = (markdown: string): string => {
  if (!markdown) return "";

  // 1. 替换块级公式 $$...$$
  let processed = markdown.replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => {
    try {
      return katex.renderToString(tex, {
        output: "mathml",
        throwOnError: false,
        displayMode: true
      });
    } catch (e) {
      return tex;
    }
  });

  // 2. 替换行内公式 $...$
  processed = processed.replace(/\$([^\$\n]+?)\$/g, (_, tex) => {
    try {
      return katex.renderToString(tex, {
        output: "mathml",
        throwOnError: false,
        displayMode: false
      });
    } catch (e) {
      return tex;
    }
  });

  return processed;
};

// ==========================================
// 4. 导出双模复制函数
// ==========================================
export const copyDualFormat = async (markdown: string) => {
  try {
    console.log("✂️ 执行智能复制 (Token Mode)...");

    // 1. 预处理公式
    const contentWithMath = processMath(markdown);

    // 2. 转换为 HTML (这里 await 是为了兼容未来版本)
    const rawHtml = await marked.parse(contentWithMath);

    // 3. 包装 Word 模板
    const finalHtml = WORD_HTML_TEMPLATE(rawHtml);

    // 4. 构建 ClipboardItem
    const textBlob = new Blob([markdown], { type: "text/plain" });
    const htmlBlob = new Blob([finalHtml], { type: "text/html" });

    const clipboardItem = new ClipboardItem({
      "text/plain": textBlob,
      "text/html": htmlBlob,
    });

    await navigator.clipboard.write([clipboardItem]);
    console.log("✅ 复制成功");
    return true;

  } catch (error) {
    console.error("❌ 智能复制失败:", error);
    await navigator.clipboard.writeText(markdown); // 降级
    return false;
  }
};