const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const ui = fs.readFileSync(path.join(root, 'app/static/js/ui-navigation.js'), 'utf8');

test('assistant uses the authenticated chat API and renders agent and source metadata', async () => {
  const elements = new Map();
  class Element {
    constructor(tag, text = '') { this.tagName = tag; this.children = []; this._text = text; this._html = ''; this.value = ''; this.disabled = false; }
    appendChild(child) { child.parent = this; this.children.push(child); return child; }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(item => item !== this); }
    focus() {}
    set textContent(value) { this._text = String(value); }
    set innerHTML(value) { this._html = String(value); }
    get textContent() { return [this._text || this._html.replace(/<[^>]*>/g, ' '), ...this.children.map(child => child.textContent)].join(' '); }
    get childElementCount() { return this.children.length; }
    get scrollHeight() { return this.children.length; }
  }
  elements.set('ai-chat-input', new Element('textarea'));
  elements.get('ai-chat-input').value = 'Analyse GPS et risque';
  elements.set('ai-chat-messages', new Element('div'));
  let request;
  const context = {
    document: {
      addEventListener() {},
      getElementById(id) { return elements.get(id) || null; },
      createElement(tag) { return new Element(tag); },
      createTextNode(value) { return new Element('#text', value); },
    },
    window: { addEventListener() {}, location: { origin: 'http://argos.test' } },
    secureApiFetch: async (url, options) => {
      request = { url, options };
      return { ok: true, status: 200, json: async () => ({
        reply: 'Synthèse testée.', trace_id: 'trace-ui-test',
        agents_consulted: ['iot_monitor', 'gps_route', 'risk_assessor'],
        agent_results: [{ agent_id: 'risk_assessor', status: 'success', data: { consumed_results: [{ agent_id: 'iot_monitor' }, { agent_id: 'gps_route' }] } }],
        sources: [{ source: 'sensor_readings' }, { source: 'positions', timestamp: '2026-10-27T10:00:00Z' }],
      }) };
    },
  };
  vm.runInNewContext(ui, context, { filename: 'ui-navigation.js' });
  await context.sendAIMessage();

  assert.equal(request.url, '/api/ai/chat');
  assert.deepEqual(JSON.parse(request.options.body), { message: 'Analyse GPS et risque', black_box_ids: [] });
  const rendered = elements.get('ai-chat-messages').children.map(message => message.textContent).join(' ');
  for (const expected of ['Synthèse testée.', 'iot_monitor', 'gps_route', 'risk_assessor', 'Résultats inter-agents consommés', 'sensor_readings', 'positions', 'trace-ui-test']) {
    assert.ok(rendered.includes(expected), `metadata manquante: ${expected}`);
  }
});

test('assistant asks first, then sends only the containers explicitly selected by the user', async () => {
  const elements = new Map();
  class Element {
    constructor() { this.children = []; this.value = ''; this.disabled = false; this._html = ''; this._text = ''; }
    appendChild(child) { child.parent = this; this.children.push(child); return child; }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(item => item !== this); }
    focus() {}
    set innerHTML(value) { this._html = String(value); }
    get innerHTML() { return this._html; }
    set textContent(value) { this._text = String(value); }
    get textContent() { return this._text || this._html.replace(/<[^>]*>/g, ' '); }
    get childElementCount() { return this.children.length; }
    get scrollHeight() { return this.children.length; }
  }
  elements.set('ai-chat-input', new Element());
  elements.get('ai-chat-input').value = 'Compare les conteneurs.';
  elements.set('ai-chat-messages', new Element());
  const requests = [];
  const context = {
    document: { addEventListener() {}, getElementById: id => elements.get(id) || null, createElement: () => new Element() },
    secureApiFetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      requests.push(body);
      if (requests.length === 1) {
        return { ok: true, status: 200, json: async () => ({
          status: 'needs_container_selection', reply: 'Choisissez les conteneurs.',
          available_containers: [{ black_box_id: '17', label: 'CONT-17' }, { black_box_id: '18', label: 'CONT-18' }],
        }) };
      }
      return { ok: true, status: 200, json: async () => ({
        status: 'success', reply: 'Comparaison terminée.', agents_consulted: ['iot_monitor', 'gps_route'],
        agent_results: [], sources: [],
      }) };
    },
  };
  vm.runInNewContext(ui, context, { filename: 'ui-navigation.js' });
  await context.sendAIMessage();
  const form = { querySelectorAll: selector => selector.includes(':checked')
    ? [{ value: '17' }, { value: '18' }]
    : [{ disabled: false }, { disabled: false }] };
  await context.submitAIContainerSelection(form);

  assert.deepEqual(requests.map(request => request.black_box_ids), [[], ['17', '18']]);
  assert.equal(requests[1].message, 'Compare les conteneurs.');
  assert.ok(elements.get('ai-chat-messages').children.length >= 3);
});

test('assistant presents its multi-agent identity and container selection UI', () => {
  const css = fs.readFileSync(path.join(root, 'app/static/css/ai-assistant.css'), 'utf8');
  assert.match(ui, /const AI_CHAT_ENDPOINT = '\/api\/ai\/chat'/);
  assert.match(ui, /function mountGlobalAIAssistant\(/);
  assert.match(ui, /function renderAIContainerSelection\(containers\)/);
  assert.match(ui, /Analyser les conteneurs sélectionnés/);
  assert.match(ui, /argos-ai-hero-mark/);
  assert.match(css, /\.argos-ai-hero-mark svg/);
  assert.match(css, /\.argos-ai-toggle\s*\{/);
});
