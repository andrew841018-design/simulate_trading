// Frontend contract checks; no server, database, or external requests.
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');
const { randomUUID } = require('node:crypto');
const { test } = require('node:test');
const html = readFileSync(resolve(__dirname, '../app/static/index.html'), 'utf8');
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];

class Element {
  constructor() { this.value = ''; this.textContent = ''; this.disabled = false; this.children = []; this.listeners = {}; }
  addEventListener(event, fn) { this.listeners[event] = fn; }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  focus() {}
}

function boot(fetch, storage = new Map(), writeFails = false, options = {}) {
  const elements = new Map();
  for (const match of html.matchAll(/<[^>]+\bid="([^"]+)"[^>]*>/g)) {
    const el = new Element();
    el.disabled = /\sdisabled(?:\s|>)/.test(match[0]);
    el.value = match[0].match(/\bvalue="([^"]*)"/)?.[1] ?? '';
    elements.set(match[1], el);
  }
  const context = {
    document: { getElementById: id => elements.get(id), createElement: () => new Element() },
    sessionStorage: {
      getItem: key => { if (options.readFails) throw new Error('Unavailable storage'); return storage.get(key) ?? null; },
      setItem: (key, value) => { if (writeFails) throw new Error('Storage blocked'); storage.set(key, value); },
      removeItem: key => { if (options.removeFails) throw new Error('Cannot clear storage'); storage.delete(key); },
    },
    crypto: { randomUUID }, fetch, AbortController,
    setTimeout: (fn, ms) => setTimeout(fn, options.fastTimerMs ?? ms), clearTimeout,
    TypeError, SyntaxError, console,
  };
  vm.runInNewContext(source, context);
  return {
    el: id => elements.get(id), storage,
    click: id => { const el = elements.get(id); if (!el.disabled) return el.listeners.click(); },
    fill: (id, value) => { const el = elements.get(id); el.value = value; el.listeners.input?.(); },
  };
}

function backend(options = {}) {
  const calls = [], orders = new Map();
  let lost = false;
  const account = () => ({ account_id: 'SIM-001', total_cash: 100000, reserved_cash: 30000 + orders.size * 1000,
    available_cash: orders.size ? 69000 : 70000 });
  const reply = (status, data) => ({ status, ok: status >= 200 && status < 300, json: async () => data });
  return { calls, orders, options, fetch: async (url, init = {}) => {
    calls.push({ url, method: init.method ?? 'GET', ...init });
    if (url === '/v1/orders' && init.method === 'POST') {
      if (options.gate) await options.gate;
      const payload = JSON.parse(init.body);
      const key = init.headers['Idempotency-Key'];
      assert.deepEqual(Object.keys(payload).sort(), ['account_id', 'action', 'order_type', 'price', 'quantity', 'symbol']);
      assert.match(key, /^[0-9a-f-]{36}$/i);
      assert.equal(typeof payload.price, 'string');
      if (options.reject) return reply(409, { detail: 'Insufficient cash' });
      if (!orders.has(key)) orders.set(key, { ...payload, order_id: `ORDER-${orders.size + 1}` });
      if (options.loseResponse && !lost) { lost = true; throw new TypeError('Lost response after commit'); }
      return reply(201, orders.get(key));
    }
    if (url.startsWith('/v1/accounts/')) return reply(200, account());
    if (url.startsWith('/v1/orders/')) {
      if (options.failOrderGet) return reply(500, { detail: 'Temporary GET error' });
      return reply(200, { order_id: decodeURIComponent(url.split('/').pop()), status: 'PARTIAL_FILLED', fill_quantity: 2, account: account() });
    }
    throw new Error(`Unexpected request: ${url}`);
  }};
}

async function ready(app) {
  await app.click('load-account');
  app.fill('symbol', 'AAPL'); app.fill('quantity', '10'); app.fill('price', '100.00');
}
const posts = api => api.calls.filter(c => c.method === 'POST');

test('BUY sends exact contract and displays GET values, not an invented OPEN state', async () => {
  const api = backend(), app = boot(api.fetch);
  assert.equal(app.el('submit-buy').disabled, true);
  await ready(app); await app.click('submit-buy');
  assert.equal(posts(api).length, 1);
  assert.equal(app.el('reserved-cash').textContent, '31000.00');
  assert.equal(app.el('available-cash').textContent, '69000.00');
  assert.equal(app.el('order-status').textContent, 'PARTIAL_FILLED');
  assert.equal(app.el('fill-quantity').textContent, '2');
  assert.equal(app.el('order-list').children.length, 1);
  assert.equal(app.storage.size, 0);
  assert.equal(app.el('submit-buy').disabled, false);
  assert.equal(app.el('query-order').disabled, false);
});

test('double click while pending sends one POST and freezes request inputs', async () => {
  let release;
  const api = backend({ gate: new Promise(resolve => { release = resolve; }) }), app = boot(api.fetch);
  await ready(app);
  const pending = app.click('submit-buy');
  assert.equal(app.el('account-id').disabled, true);
  assert.equal(app.el('price').disabled, true);
  await app.click('submit-buy');
  release(); await pending;
  assert.equal(posts(api).length, 1);
});

test('invalid decimal scale does not send POST', async () => {
  const api = backend(), app = boot(api.fetch);
  await ready(app); app.fill('price', '100.001'); await app.click('submit-buy');
  assert.equal(posts(api).length, 0);
  assert.equal(app.storage.size, 0);
});

test('POST success survives failed GET; refresh button retries only reads', async () => {
  const api = backend({ failOrderGet: true }), app = boot(api.fetch);
  await ready(app); await app.click('submit-buy');
  assert.match(app.el('buy-message').textContent, /下單成功.*部分資料更新失敗/);
  assert.equal(app.el('result-order-id').textContent, 'ORDER-1');
  api.options.failOrderGet = false;
  await app.click('refresh-buy-result');
  assert.equal(posts(api).length, 1);
  assert.equal(app.el('order-status').textContent, 'PARTIAL_FILLED');
});

test('lost POST response survives reload and confirms with the original key/payload', async () => {
  const api = backend({ loseResponse: true }), first = boot(api.fetch);
  await ready(first); await first.click('submit-buy');
  assert.equal(first.storage.size, 1);
  assert.equal(first.el('submit-buy').disabled, true);
  const reloaded = boot(api.fetch, first.storage);
  assert.equal(reloaded.el('submit-buy').disabled, true);
  await reloaded.click('confirm-request');
  const sent = posts(api);
  assert.equal(sent.length, 2);
  assert.equal(sent[0].headers['Idempotency-Key'], sent[1].headers['Idempotency-Key']);
  assert.equal(sent[0].body, sent[1].body);
  assert.equal(api.orders.size, 1);
  assert.equal(reloaded.storage.size, 0);
});

test('storage failure prevents POST', async () => {
  const api = backend(), app = boot(api.fetch, new Map(), true);
  await ready(app); await app.click('submit-buy');
  assert.equal(posts(api).length, 0);
  assert.match(app.el('buy-message').textContent, /尚未送出/);
});

test('known rejection preserves inputs and does not claim a successful order', async () => {
  const api = backend({ reject: true }), app = boot(api.fetch);
  await ready(app); await app.click('submit-buy');
  assert.equal(api.orders.size, 0);
  assert.equal(app.storage.size, 0);
  assert.equal(app.el('price').value, '100.00');
  assert.match(app.el('buy-message').textContent, /可用現金不足/);
});

test('new intentional BUY after success gets a new key', async () => {
  const api = backend(), app = boot(api.fetch);
  await ready(app); await app.click('submit-buy'); await app.click('submit-buy');
  assert.equal(api.orders.size, 2);
  assert.notEqual(posts(api)[0].headers['Idempotency-Key'], posts(api)[1].headers['Idempotency-Key']);
});

const reply = (status, data) => ({ status, ok: status >= 200 && status < 300, json: async () => data });
const order = (id, accountId = 'OTHER-ACCOUNT') => ({ order_id: id, status: 'OPEN', fill_quantity: 0,
  account: { account_id: accountId, total_cash: 9000, reserved_cash: 1000, available_cash: 8000 } });

test('manual lookup and list viewing use encoded GET, deduplicate, and keep BUY account', async () => {
  const api = backend();
  const reads = [];
  const app = boot((url, init) => {
    if (url.startsWith('/v1/orders/')) { reads.push(url); return reply(200, order(decodeURIComponent(url.split('/').pop()))); }
    return api.fetch(url, init);
  });
  await ready(app);
  app.fill('order-id', 'ORDER /?#'); await app.click('query-order');
  assert.equal(reads[0], '/v1/orders/ORDER%20%2F%3F%23');
  assert.equal(app.el('order-account-id').textContent, 'OTHER-ACCOUNT');
  assert.equal(app.el('selected-account').textContent, 'SIM-001');
  assert.equal(app.el('available-cash').textContent, '70000.00');
  await app.el('order-list').children[0].children[3].children[0].listeners.click();
  assert.equal(reads.length, 2);
  assert.equal(app.el('order-list').children.length, 1);
  assert.equal(posts(api).length, 0);
});

test('blank, missing and malformed order results clear previous detail and never invent orders', async () => {
  let status = 200, data = order('KNOWN'), calls = 0;
  const app = boot(async () => { calls++; return reply(status, data); });
  app.fill('order-id', 'KNOWN'); await app.click('query-order');
  app.fill('order-id', '   '); await app.click('query-order');
  assert.equal(calls, 1);
  assert.equal(app.el('result-order-id').textContent, '—');
  status = 404; data = { detail: 'Order not found' };
  app.fill('order-id', 'MISSING'); await app.click('query-order');
  assert.match(app.el('order-message').textContent, /找不到此訂單/);
  assert.equal(app.el('order-status').textContent, '—');
  status = 200; data = { ...order('MALFORMED'), status: 'INVENTED' };
  app.fill('order-id', 'MALFORMED'); await app.click('query-order');
  assert.match(app.el('order-message').textContent, /格式不正確/);
  assert.equal(app.el('order-list').children.length, 1);
});

test('slower old order response cannot overwrite a newer query or changed input', async () => {
  let release;
  const app = boot(url => url.endsWith('OLD') ? new Promise(resolve => { release = resolve; }) : reply(200, order('NEW')));
  app.fill('order-id', 'OLD'); const old = app.click('query-order');
  app.fill('order-id', 'NEW'); await app.click('query-order');
  release(reply(200, order('OLD'))); await old;
  assert.equal(app.el('result-order-id').textContent, 'NEW');
  assert.equal(app.el('order-list').children.length, 1);
  app.fill('order-id', 'OLD'); const another = app.click('query-order');
  app.fill('order-id', 'NOT-YET-QUERIED');
  release(reply(200, order('OLD'))); await another;
  assert.equal(app.el('result-order-id').textContent, '—');
  assert.match(app.el('order-message').textContent, /ID 已變更/);
});

test('order network failure and 500 can recover with a later GET', async () => {
  let state = 'network';
  const app = boot(() => {
    if (state === 'network') throw new TypeError('offline');
    return state === 'server' ? reply(500, {}) : reply(200, order('O'));
  });
  app.fill('order-id', 'O'); await app.click('query-order');
  assert.match(app.el('order-message').textContent, /無法連線/);
  state = 'server'; await app.click('query-order');
  assert.match(app.el('order-message').textContent, /HTTP 500/);
  state = 'ok'; await app.click('query-order');
  assert.equal(app.el('result-order-id').textContent, 'O');
});

for (const [status, detail, message] of [
  [404, 'Account not found', /帳戶不存在/],
  [409, 'Idempotency key already exists', /請求識別衝突/],
  [422, [{ loc: ['body', 'quantity'], msg: 'invalid input' }], /需檢查：數量/],
]) {
  test(`known POST ${status} ${JSON.stringify(detail)} keeps inputs and does not automatically resend`, async () => {
    const api = backend();
    let sent = 0;
    const app = boot((url, init) => {
      if (init?.method === 'POST') { sent++; return reply(status, { detail }); }
      return api.fetch(url, init);
    });
    await ready(app); await app.click('submit-buy');
    assert.match(app.el('buy-message').textContent, message);
    assert.equal(app.el('quantity').value, '10');
    assert.equal(app.el('symbol').value, 'AAPL');
    assert.equal(app.storage.size, 0);
    assert.equal(sent, 1);
  });
}

for (const mode of ['500', 'non-json', 'invalid-success', 'timeout']) {
  test(`unknown POST ${mode} locks new orders and confirms exact original request`, async () => {
    const api = backend(); let first = true;
    const app = boot(async (url, init) => {
      if (init?.method === 'POST' && first) {
        first = false;
        await api.fetch(url, init); // effect happened before the client lost the result
        if (mode === '500') return reply(500, { detail: 'server error' });
        if (mode === 'invalid-success') return reply(201, { order_id: 'UNKNOWN' });
        if (mode === 'non-json') return { status: 201, ok: true, json: async () => { throw new SyntaxError('invalid JSON'); } };
        return new Promise((_, reject) => init.signal.addEventListener('abort', () => reject(Object.assign(new Error('timeout'), { name: 'AbortError' }))));
      }
      return api.fetch(url, init);
    }, new Map(), false, { fastTimerMs: 10 });
    await ready(app); await app.click('submit-buy');
    assert.match(app.el('buy-message').textContent, /尚未確認/);
    assert.equal(app.el('submit-buy').disabled, true);
    assert.equal(app.el('price').disabled, true);
    await app.click('confirm-request');
    assert.equal(api.orders.size, 1);
    assert.equal(posts(api).length, 2);
    assert.equal(posts(api)[0].body, posts(api)[1].body);
    assert.equal(posts(api)[0].headers['Idempotency-Key'], posts(api)[1].headers['Idempotency-Key']);
    assert.equal(app.storage.size, 0);
  });
}

test('corrupt or unreadable pending storage fails closed while GET lookup remains available', async () => {
  for (const [storage, options] of [
    [new Map([['simulate-trading.pending-buy.v1', 'not json']]), {}],
    [new Map(), { readFails: true }],
  ]) {
    const api = backend(), app = boot(api.fetch, storage, false, options);
    assert.equal(app.el('submit-buy').disabled, true);
    assert.equal(app.el('query-order').disabled, false);
    assert.match(app.el('buy-message').textContent, /無法讀取原請求暫存/);
    assert.equal(posts(api).length, 0);
  }
});

test('failure to clear pending after known success never allows a fresh POST', async () => {
  const api = backend(), app = boot(api.fetch, new Map(), false, { removeFails: true });
  await ready(app); await app.click('submit-buy');
  assert.match(app.el('buy-message').textContent, /下單成功.*暫存無法清除/);
  assert.equal(app.el('submit-buy').disabled, true);
  await app.click('submit-buy');
  assert.equal(posts(api).length, 1);
});

test('order timeout clears detail and allows a successful retry', async () => {
  let hanging = true;
  const app = boot((url, init) => hanging
    ? new Promise((_, reject) => init.signal.addEventListener('abort', () => reject(Object.assign(new Error('timeout'), { name: 'AbortError' }))))
    : reply(200, order('O')), new Map(), false, { fastTimerMs: 10 });
  app.fill('order-id', 'O'); await app.click('query-order');
  assert.match(app.el('order-message').textContent, /逾時/);
  assert.equal(app.el('result-order-id').textContent, '—');
  hanging = false; await app.click('query-order');
  assert.equal(app.el('result-order-id').textContent, 'O');
});
