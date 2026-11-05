import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { McpServer } from '@modelcontextprotocol/server';
import { StdioServerTransport } from '@modelcontextprotocol/server/stdio';
import { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE } from '@modelcontextprotocol/ext-apps/server';
import { z } from 'zod';

export const RESOURCE_URI = 'ui://inline-micro-form/main';

// Only the local, asset-free USWDS rules needed by this inline view. Full USWDS
// CSS references external fonts and icons that cannot load from a ui:// resource.
const USWDS_SELECTORS = [
  '.usa-textarea, .usa-range__value, .usa-range, .usa-radio__label, .usa-input-group, .usa-hint, .usa-combo-box__input, .usa-combo-box__list, .usa-select, .usa-checkbox__label, .usa-fieldset, .usa-input',
  '.usa-textarea, .usa-range, .usa-input-group, .usa-combo-box__input, .usa-select, .usa-input',
  '.usa-button',
  '.usa-button:hover, .usa-button.usa-button--hover',
  '.usa-button:active, .usa-button.usa-button--active',
  '.usa-button:not([disabled]):focus, .usa-button:not([disabled]).usa-focus',
  '.usa-button--outline',
  '.usa-button--outline:hover, .usa-button--outline.usa-button--hover',
  '.usa-button--outline:active, .usa-button--outline.usa-button--active',
  '.usa-label',
  'input:not([disabled]):focus,\nselect:not([disabled]):focus,\ntextarea:not([disabled]):focus,\nbutton:not([disabled]):focus',
];

function selectUswdsStyles(css) {
  return USWDS_SELECTORS.map((selector) => {
    const position = css.indexOf(`\n${selector}{`);
    if (position < 0) throw new Error(`Missing USWDS style: ${selector}`);
    const start = position + 1;
    const end = css.indexOf('}', start);
    if (end < 0) throw new Error(`Incomplete USWDS style: ${selector}`);
    const rule = css.slice(start, end + 1);
    if (/url\s*\(/i.test(rule)) throw new Error(`USWDS style requires an external asset: ${selector}`);
    return rule;
  }).join('\n');
}

async function renderView() {
  const [template, css] = await Promise.all([
    readFile(new URL('./view.html', import.meta.url), 'utf8'),
    readFile(new URL(import.meta.resolve('@uswds/uswds/css/uswds.css')), 'utf8'),
  ]);
  const marker = '/* USWDS_COMPONENT_STYLES: populated from the pinned local package by server.js. */';
  if (!template.includes(marker)) throw new Error('Missing USWDS view style marker');
  return template.replace(marker, selectUswdsStyles(css));
}

export function createServer() {
  const server = new McpServer({ name: 'inline-micro-form', version: '0.1.0' });

  registerAppTool(server, 'show_micro_form', {
    title: 'Show micro form',
    description: 'Display a small interactive form inline in the chat. Use when asked to show or test the micro form.',
    inputSchema: z.object({}),
    _meta: { ui: { resourceUri: RESOURCE_URI } },
  }, async () => ({
    content: [{ type: 'text', text: 'Micro form: enter a task name and choose Low, Medium, or High priority. If the inline form is not visible, this chat client may not support MCP Apps.' }],
    // Goose Desktop also discovers the view from tool-result metadata.
    _meta: { ui: { resourceUri: RESOURCE_URI } },
  }));

  registerAppResource(server, RESOURCE_URI, RESOURCE_URI,
    { mimeType: RESOURCE_MIME_TYPE }, async () => ({
      contents: [{
        uri: RESOURCE_URI,
        mimeType: RESOURCE_MIME_TYPE,
         text: await renderView(),
        _meta: { ui: { csp: { connectDomains: [], resourceDomains: [], frameDomains: [], baseUriDomains: [] }, prefersBorder: true } },
      }],
    }));
  return server;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  createServer().connect(new StdioServerTransport()).catch((error) => {
    console.error('MCP server failed to start:', error);
    process.exitCode = 1;
  });
}
