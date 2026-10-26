import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const themeCss = readFileSync(new URL('../src/theme.css', import.meta.url), 'utf8');

function declarations(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const block = themeCss.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))?.[1];
  assert.ok(block, `missing CSS rule: ${selector}`);
  return Object.fromEntries(
    [...block.matchAll(/(--[\w-]+|color-scheme)\s*:\s*([^;]+)\s*;/g)]
      .map(([, name, value]) => [name, value.trim()]),
  );
}

const study = declarations(':root');
const ask = declarations(':root[data-theme="ask"]');

function resolveColor(value, theme, seen = new Set()) {
  const variable = value.match(/^var\((--[\w-]+)\)$/)?.[1];
  if (variable) {
    assert.ok(!seen.has(variable), `cyclic CSS variable: ${variable}`);
    const next = theme[variable] ?? study[variable];
    assert.ok(next, `missing CSS variable: ${variable}`);
    return resolveColor(next, theme, new Set([...seen, variable]));
  }
  const hex = value.match(/^#([\da-f]{3}|[\da-f]{6})$/i)?.[1];
  assert.ok(hex, `expected a hex color or variable reference, got: ${value}`);
  const fullHex = hex.length === 3 ? [...hex].map((digit) => digit + digit).join('') : hex;
  return [0, 2, 4].map((offset) => Number.parseInt(fullHex.slice(offset, offset + 2), 16) / 255);
}

function luminance(rgb) {
  const linear = rgb.map((channel) => channel <= 0.04045
    ? channel / 12.92
    : ((channel + 0.055) / 1.055) ** 2.4);
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrast(first, second) {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

test('study and ask declare their intended native color schemes and distinct brightness', () => {
  assert.equal(study['color-scheme'], 'light');
  assert.equal(ask['color-scheme'], 'dark');

  const studyBackground = luminance(resolveColor(study['--workspace-bg'], study));
  const askBackground = luminance(resolveColor(ask['--workspace-bg'], ask));
  assert.ok(askBackground < studyBackground * 0.15,
    `ask workspace should be substantially darker (study=${studyBackground}, ask=${askBackground})`);
});

test('study and ask text and primary buttons keep readable contrast on their surfaces', () => {
  for (const [name, theme] of [['study', study], ['ask', ask]]) {
    const surface = resolveColor(theme['--surface'], theme);
    for (const token of ['--text-body', '--text-muted', '--accent']) {
      const color = resolveColor(theme[token], theme);
      assert.ok(contrast(color, surface) >= 4.5,
        `${name} ${token} contrast on --surface must be at least 4.5:1`);
    }

    const primaryBackground = resolveColor(theme['--primary-bg'], theme);
    const primaryForeground = resolveColor(theme['--on-primary'], theme);
    assert.ok(contrast(primaryForeground, primaryBackground) >= 4.5,
      `${name} primary button contrast must be at least 4.5:1`);
  }
});
