/**
 * chart_lift.js — the one place a study borrows a function from the chart.
 *
 * `pmaxSeries` and `atrSeries` are DEFINED in chart_dashboard.html, because that
 * is what draws them. A study that reimplemented either would be measuring its
 * own copy, and the copy would drift — so studies slice the real source by
 * brace-matching from the function header and eval it. A rename or an edit in
 * the chart surfaces here as a loud failure instead of a silent divergence
 * between what the chart draws and what the desk measured.
 *
 * Extracted from psar_overlap.js (B-59) on 2026-09-12, when B-74 needed the same
 * lift: two copies of "how to borrow from the chart" is the drift this guards
 * against, one level up.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const HERE = __dirname;

function liftFunction(src, name) {
  const start = src.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`chart_dashboard.html no longer defines ${name}()`);
  let depth = 0, i = src.indexOf('{', start);
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) break; }
  }
  if (depth !== 0) throw new Error(`unbalanced braces lifting ${name}()`);
  return src.slice(start, i + 1);
}

const html = fs.readFileSync(path.join(HERE, 'chart_dashboard.html'), 'utf-8');

const chartFns = new Function(
  `${liftFunction(html, 'atrSeries')}\n${liftFunction(html, 'pmaxSeries')}\n` +
  'return {atrSeries, pmaxSeries};'
)();

module.exports = { liftFunction, chartFns, CACHE: path.join(HERE, 'cache', 'cardinality') };
