import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';
import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import { RESOURCE_URI } from './server.js';

test('publishes an MCP App tool, readable HTML resource, and text fallback', async () => {
  const client = new Client({ name: 'micro-form-test', version: '1.0.0' });
  const transport = new StdioClientTransport({ command: process.execPath, args: ['server.js'], stderr: 'pipe' });
  try {
    await client.connect(transport);
    const { tools } = await client.listTools();
    const tool = tools.find((entry) => entry.name === 'show_micro_form');
    assert.equal(tool?._meta?.ui?.resourceUri, RESOURCE_URI);

    const result = await client.callTool({ name: 'show_micro_form', arguments: {} });
    assert.equal(result._meta?.ui?.resourceUri, RESOURCE_URI);
    assert.match(result.content[0].text, /If the inline form is not visible/);

    const resource = await client.readResource({ uri: RESOURCE_URI });
    assert.equal(resource.contents[0].mimeType, 'text/html;profile=mcp-app');
    assert.match(resource.contents[0].text, /<h2>Micro form<\/h2>/);
    assert.match(resource.contents[0].text, /data-priority="High"/);
    assert.equal((resource.contents[0].text.match(/data-priority="(Low|Medium|High)"/g) ?? []).length, 3);
    assert.match(resource.contents[0].text, /class="usa-input" id="task"/);
    assert.match(resource.contents[0].text, /class="usa-label" for="task"/);
    assert.match(resource.contents[0].text, /class="usa-button" type="button" data-priority="Medium" aria-pressed="true"/);
    assert.match(resource.contents[0].text, /\.usa-button\{[\s\S]*?background-color:#005ea2/);
    assert.match(resource.contents[0].text, /\.usa-input\{[\s\S]*?border-color:#565c65/);
    assert.doesNotMatch(resource.contents[0].text, /USWDS_COMPONENT_STYLES|<link\b|url\s*\(/i);
    assert.match(resource.contents[0].text, /method: 'ui\/initialize'/);
    assert.match(resource.contents[0].text, /ui\/notifications\/size-changed/);
    assert.deepEqual(resource.contents[0]._meta.ui.csp.connectDomains, []);
  } finally {
    await client.close();
  }
});

test('selecting priority updates USWDS button styles, pressed state, and status', async () => {
  const html = await readFile(new URL('./view.html', import.meta.url), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  assert.ok(script);
  const buttons = ['Low', 'Medium', 'High'].map((priority) => {
    const classes = new Set(priority === 'Medium' ? [] : ['usa-button--outline']);
    const attributes = { 'aria-pressed': String(priority === 'Medium') };
    return {
      dataset: { priority },
      attributes,
      classes,
      addEventListener: (_type, callback) => { buttonsByPriority.set(priority, callback); },
      setAttribute: (name, value) => { attributes[name] = value; },
      classList: { toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name) },
    };
  });
  const buttonsByPriority = new Map();
  const status = { textContent: '' };
  const messages = [];
  let onMessage;
  const parent = { postMessage: (message) => messages.push(message) };
  runInNewContext(script, {
    window: {
      parent,
      addEventListener: (_type, listener) => { onMessage = listener; },
      removeEventListener() {},
    },
    document: {
      body: { scrollHeight: 250 },
      documentElement: { scrollWidth: 400 },
      querySelectorAll: () => buttons,
      querySelector: () => ({ getBoundingClientRect: () => ({ height: 270 }) }),
      getElementById: () => status,
    },
    ResizeObserver: class { observe() {} },
  });
  onMessage({ source: parent, data: { id: messages[0].id, result: {} } });
  buttonsByPriority.get('High')();
  assert.deepEqual(buttons.map((button) => button.attributes['aria-pressed']), ['false', 'false', 'true']);
  assert.deepEqual(buttons.map((button) => button.classes.has('usa-button--outline')), [true, true, false]);
  assert.equal(status.textContent, 'High selected. Inline buttons work.');
  assert.equal(messages.at(-1).method, 'ui/notifications/size-changed');
});

test('reports a comfortable height based on form content after Goose initializes', async () => {
  const html = await readFile(new URL('./view.html', import.meta.url), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  assert.ok(script, 'inline view script exists');

  const messages = [];
  const listeners = new Map();
  const parent = { postMessage: (message) => messages.push(message) };
  const buttons = ['Low', 'Medium', 'High'].map((priority) => ({
    dataset: { priority },
    addEventListener() {},
  }));
  const document = {
    body: { scrollHeight: 250 },
    documentElement: { scrollWidth: 400, scrollHeight: 110 },
    querySelectorAll: () => buttons,
    querySelector: () => ({ getBoundingClientRect: () => ({ height: 270 }) }),
    getElementById: () => ({ textContent: '' }),
  };
  const window = {
    parent,
    addEventListener: (type, listener) => listeners.set(type, listener),
    removeEventListener: (type) => listeners.delete(type),
  };

  runInNewContext(script, { window, document, ResizeObserver: class { observe() {} } });
  assert.equal(messages[0].method, 'ui/initialize');
  listeners.get('message')({ source: parent, data: { id: messages[0].id, result: {} } });
  const size = messages.find((message) => message.method === 'ui/notifications/size-changed');
  assert.equal(size.params.height, 400);
  assert.equal(size.params.width, 400);
});

test('expands the reported height when the form is taller than the minimum', async () => {
  const html = await readFile(new URL('./view.html', import.meta.url), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  assert.ok(script);
  const messages = [];
  const parent = { postMessage: (message) => messages.push(message) };
  let onMessage;
  runInNewContext(script, {
    window: {
      parent,
      addEventListener: (_type, listener) => { onMessage = listener; },
      removeEventListener() {},
    },
    document: {
      body: { scrollHeight: 510 },
      documentElement: { scrollWidth: 400 },
      querySelectorAll: () => [],
      querySelector: () => ({ getBoundingClientRect: () => ({ height: 500 }) }),
      getElementById: () => ({ textContent: '' }),
    },
    ResizeObserver: class { observe() {} },
  });
  onMessage({ source: parent, data: { id: messages[0].id, result: {} } });
  const size = messages.find((message) => message.method === 'ui/notifications/size-changed');
  assert.equal(size.params.height, 574);
});
