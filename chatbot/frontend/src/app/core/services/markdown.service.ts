import { Injectable, inject } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';
import hljs from 'highlight.js/lib/core';
import sql from 'highlight.js/lib/languages/sql';
import json from 'highlight.js/lib/languages/json';
import python from 'highlight.js/lib/languages/python';
import typescript from 'highlight.js/lib/languages/typescript';
import bash from 'highlight.js/lib/languages/bash';
import xml from 'highlight.js/lib/languages/xml';
import { renderToString as katexRender } from 'katex';
import DOMPurify from 'dompurify';

hljs.registerLanguage('sql', sql);
hljs.registerLanguage('json', json);
hljs.registerLanguage('python', python);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('javascript', typescript);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('sh', bash);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('html', xml);

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.nodeName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

marked.use({
  gfm: true,
  breaks: false,
  renderer: {
    code({ text, lang }: { text: string; lang?: string }): string {
      const language = lang && hljs.getLanguage(lang) ? lang : undefined;
      const highlighted = language
        ? hljs.highlight(text, { language }).value
        : hljs.highlightAuto(text).value;
      return `<pre><code class="hljs language-${language ?? 'plaintext'}">${highlighted}</code></pre>`;
    },
  },
});

// KaTeX: allow its generated span/style/aria-hidden in DOMPurify.
// Styles are safe — KaTeX generates layout CSS, not user-controlled values.
const ALLOWED_TAGS = [
  'p', 'br', 'strong', 'b', 'em', 'i', 'del', 's',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li',
  'blockquote', 'pre', 'code',
  'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
  'a', 'img', 'hr', 'span', 'div',
];

const ALLOWED_ATTR = [
  'href', 'src', 'alt', 'class', 'target', 'rel', 'title', 'width', 'height',
  'style', 'aria-hidden',
];

// $$...$$ — display-mode math only (avoids conflict with SQL $1/$2 params).
const BLOCK_MATH_RE = /\$\$([\s\S]*?)\$\$/g;

@Injectable({ providedIn: 'root' })
export class MarkdownService {
  private readonly sanitizer = inject(DomSanitizer);

  private lastInput = '';
  private lastOutput: SafeHtml | undefined;

  render(content: string): SafeHtml {
    if (content === this.lastInput && this.lastOutput !== undefined) {
      return this.lastOutput;
    }

    // marked preserves $$ as plain text; we replace after parsing
    const rawHtml = marked.parse(content) as string;
    const withMath = rawHtml.replace(BLOCK_MATH_RE, (_match, math: string) => {
      try {
        return katexRender(math.trim(), { displayMode: true, throwOnError: false, output: 'html' });
      } catch {
        return `<code class="math-error">$$${math}$$</code>`;
      }
    });

    const clean = DOMPurify.sanitize(withMath, { ALLOWED_TAGS, ALLOWED_ATTR });
    this.lastInput = content;
    this.lastOutput = this.sanitizer.bypassSecurityTrustHtml(clean);
    return this.lastOutput;
  }
}
