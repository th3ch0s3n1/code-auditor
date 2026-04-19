"""HTML reporter — self-contained, interactive single-page report."""

from __future__ import annotations

import json
from pathlib import Path

from ..core.schema import ScanResult

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Audit Report — {scan_id}</title>
<style>
:root {{
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #c9d1d9; --muted: #8b949e;
  --critical: #ff4d4f; --high: #ff7a45; --medium: #ffa940;
  --low: #40a9ff; --info: #69b1ff;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; padding: 1.5rem; }}
h1 {{ font-size: 1.4rem; margin-bottom: 0.5rem; }}
.meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 1.5rem; }}
.summary {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
.stat {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1.25rem; min-width: 100px; text-align: center; }}
.stat .value {{ font-size: 1.8rem; font-weight: 700; }}
.stat .label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; }}
.controls {{ display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1rem; }}
select, input {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 0.4rem 0.75rem; border-radius: 6px; font-size: 0.875rem; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
th {{ background: var(--surface); text-align: left; padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); cursor: pointer; user-select: none; white-space: nowrap; }}
th:hover {{ color: #fff; }}
td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: top; word-break: break-word; }}
tr:hover td {{ background: #1c2129; }}
.badge {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
.sev-critical {{ color: var(--critical); }}
.sev-high    {{ color: var(--high); }}
.sev-medium  {{ color: var(--medium); }}
.sev-low     {{ color: var(--low); }}
.sev-info    {{ color: var(--info); }}
.risk-bar {{ height: 6px; border-radius: 3px; background: var(--border); width: 80px; }}
.risk-fill {{ height: 100%; border-radius: 3px; background: linear-gradient(90deg, #40a9ff, #ff4d4f); }}
.snippet {{ font-family: monospace; background: #1c2129; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; white-space: pre-wrap; }}
.suggestion {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.25rem; }}
.empty {{ text-align: center; padding: 3rem; color: var(--muted); }}
#count {{ color: var(--muted); font-size: 0.85rem; }}
button.btn {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 0.4rem 0.9rem; border-radius: 6px; font-size: 0.875rem; cursor: pointer; white-space: nowrap; }}
button.btn:hover {{ border-color: #58a6ff; color: #58a6ff; }}
button.btn.copied {{ border-color: #3fb950; color: #3fb950; }}
</style>
</head>
<body>
<h1>Code Audit Report</h1>
<div class="meta">
  Scan <strong>{scan_id}</strong> &bull;
  {target_path} &bull;
  {total} issues &bull;
  {duration}s &bull;
  {project_types}
</div>

<div class="summary">
  <div class="stat"><div class="value sev-critical">{critical}</div><div class="label">Critical</div></div>
  <div class="stat"><div class="value sev-high">{high}</div><div class="label">High</div></div>
  <div class="stat"><div class="value sev-medium">{medium}</div><div class="label">Medium</div></div>
  <div class="stat"><div class="value sev-low">{low}</div><div class="label">Low</div></div>
  <div class="stat"><div class="value sev-info">{info}</div><div class="label">Info</div></div>
  <div class="stat"><div class="value">{files_scanned}</div><div class="label">Files</div></div>
</div>

<div class="controls">
  <select id="sevFilter" onchange="applyFilters()">
    <option value="">All severities</option>
    <option value="critical">Critical</option>
    <option value="high">High</option>
    <option value="medium">Medium</option>
    <option value="low">Low</option>
    <option value="info">Info</option>
  </select>
  <select id="catFilter" onchange="applyFilters()">
    <option value="">All categories</option>
    <option value="security">Security</option>
    <option value="correctness">Correctness</option>
    <option value="maintainability">Maintainability</option>
    <option value="performance">Performance</option>
    <option value="dependency">Dependency</option>
  </select>
  <select id="toolFilter" onchange="applyFilters()">
    <option value="">All tools</option>
    {tool_options}
  </select>
  <input id="search" type="search" placeholder="Search message / file / rule…" oninput="applyFilters()">
  <span id="count"></span>
  <button class="btn" id="copyMdBtn" onclick="copyMarkdown()">Copy as Markdown</button>
</div>

<table id="issueTable">
<thead>
  <tr>
    <th onclick="sortBy(0)">Severity ⇅</th>
    <th onclick="sortBy(1)">File ⇅</th>
    <th onclick="sortBy(2)">Line ⇅</th>
    <th onclick="sortBy(3)">Tool ⇅</th>
    <th onclick="sortBy(4)">Rule ⇅</th>
    <th>Message / Snippet</th>
    <th onclick="sortBy(6)">Risk ⇅</th>
  </tr>
</thead>
<tbody id="tableBody"></tbody>
</table>

<script>
const DATA = {data_json};
let sortCol = 6, sortDir = -1;

function sev(s){{
  const m={{'critical':5,'high':4,'medium':3,'low':2,'info':1}};
  return m[s]||0;
}}
function renderRow(i){{
  const snippet = i.code_snippet ? `<div class="snippet">${{escHtml(i.code_snippet)}}</div>` : '';
  const suggestion = i.suggestion ? `<div class="suggestion">💡 ${{escHtml(i.suggestion)}}</div>` : '';
  const pct = i.risk_score;
  return `<tr data-sev="${{i.severity}}" data-cat="${{i.category}}" data-tool="${{i.tool}}">
    <td><span class="sev-${{i.severity}}">${{i.severity.toUpperCase()}}</span></td>
    <td>${{escHtml(i.file)}}</td>
    <td>${{i.line||'—'}}</td>
    <td>${{escHtml(i.tool)}}</td>
    <td><code>${{escHtml(i.rule_id)}}</code></td>
    <td>${{escHtml(i.message)}}${{snippet}}${{suggestion}}</td>
    <td><div class="risk-bar"><div class="risk-fill" style="width:${{pct}}%"></div></div><span style="font-size:0.75rem">${{pct}}</span></td>
  </tr>`;
}}
function escHtml(s){{
  if(!s)return'';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
function applyFilters(){{
  const sev=document.getElementById('sevFilter').value;
  const cat=document.getElementById('catFilter').value;
  const tool=document.getElementById('toolFilter').value;
  const q=document.getElementById('search').value.toLowerCase();
  let filtered=DATA.filter(i=>
    (!sev||i.severity===sev)&&
    (!cat||i.category===cat)&&
    (!tool||i.tool===tool)&&
    (!q||(i.message+i.file+i.rule_id).toLowerCase().includes(q))
  );
  filtered=sortIssues(filtered);
  document.getElementById('tableBody').innerHTML=filtered.map(renderRow).join('');
  document.getElementById('count').textContent=filtered.length+' of '+DATA.length+' shown';
}}
function sortIssues(arr){{
  return arr.slice().sort((a,b)=>{{
    let va,vb;
    if(sortCol===0){{va=sev(a.severity);vb=sev(b.severity);}}
    else if(sortCol===1){{va=a.file;vb=b.file;}}
    else if(sortCol===2){{va=a.line||0;vb=b.line||0;}}
    else if(sortCol===3){{va=a.tool;vb=b.tool;}}
    else if(sortCol===4){{va=a.rule_id;vb=b.rule_id;}}
    else{{va=a.risk_score;vb=b.risk_score;}}
    if(va<vb)return sortDir;
    if(va>vb)return -sortDir;
    return 0;
  }});
}}
function sortBy(col){{
  if(sortCol===col)sortDir*=-1;
  else{{sortCol=col;sortDir=-1;}}
  applyFilters();
}}
applyFilters();

function copyMarkdown(){{
  const sev=document.getElementById('sevFilter').value;
  const cat=document.getElementById('catFilter').value;
  const tool=document.getElementById('toolFilter').value;
  const q=document.getElementById('search').value.toLowerCase();
  let filtered=DATA.filter(i=>
    (!sev||i.severity===sev)&&
    (!cat||i.category===cat)&&
    (!tool||i.tool===tool)&&
    (!q||(i.message+i.file+i.rule_id).toLowerCase().includes(q))
  );
  filtered=sortIssues(filtered);

  const meta=`# Code Audit Report\n\n` +
    `**Scan:** {scan_id}  \n` +
    `**Target:** {target_path}  \n` +
    `**Project types:** {project_types}  \n` +
    `**Files scanned:** {files_scanned} | **Duration:** {duration}s  \n\n` +
    `## Summary\n\n` +
    `| Critical | High | Medium | Low | Info | Total |\n` +
    `|----------|------|--------|-----|------|-------|\n` +
    `| {critical} | {high} | {medium} | {low} | {info} | {total} |\n\n`;

  const header=`## Issues (${{filtered.length}} shown)\n\n` +
    `| # | Severity | File | Line | Tool | Rule | Message | Risk |\n` +
    `|---|----------|------|------|------|------|---------|------|\n`;

  const rows=filtered.map((i,idx)=>{{
    const file=i.file.replace(/\|/g,'\\|');
    const msg=i.message.replace(/\|/g,'\\|').replace(/\\n/g,' ');
    const rule=i.rule_id.replace(/\|/g,'\\|');
    return `| ${{idx+1}} | ${{i.severity.toUpperCase()}} | ${{file}} | ${{i.line||'—'}} | ${{i.tool}} | ${{rule}} | ${{msg}} | ${{i.risk_score}} |`;
  }}).join('\\n');

  const details=filtered.map((i,idx)=>{{
    let block=`### ${{idx+1}}. ${{i.severity.toUpperCase()}} — ${{i.rule_id}}\n\n` +
      `**File:** \`${{i.file}}\`  \n` +
      `**Line:** ${{i.line||'N/A'}} | **Tool:** ${{i.tool}} | **Category:** ${{i.category}} | **Risk score:** ${{i.risk_score}}  \n` +
      `**Message:** ${{i.message}}`;
    if(i.suggestion) block+=`  \n**Suggestion:** ${{i.suggestion}}`;
    if(i.code_snippet) block+=`\n\n\`\`\`\n${{i.code_snippet}}\n\`\`\``;
    return block;
  }}).join('\\n\\n---\\n\\n');

  const md=meta+header+rows+`\n\n## Details\n\n`+details;

  navigator.clipboard.writeText(md).then(()=>{{
    const btn=document.getElementById('copyMdBtn');
    btn.textContent='Copied!';
    btn.classList.add('copied');
    setTimeout(()=>{{btn.textContent='Copy as Markdown';btn.classList.remove('copied');}},2000);
  }}).catch(()=>{{
    const ta=document.createElement('textarea');
    ta.value=md;ta.style.position='fixed';ta.style.opacity='0';
    document.body.appendChild(ta);ta.select();document.execCommand('copy');
    document.body.removeChild(ta);
  }});
}}
</script>
</body>
</html>
"""


def render(result: ScanResult, path: Path | None = None) -> str:
    """Render *result* as a self-contained HTML page.  Optionally write to *path*."""
    s = result.summary
    tools = sorted({i.tool for i in result.issues})
    tool_options = "\n    ".join(f'<option value="{t}">{t}</option>' for t in tools)

    html = _TEMPLATE.format(
        scan_id=result.scan_id,
        target_path=result.target_path,
        total=s.total,
        critical=s.critical,
        high=s.high,
        medium=s.medium,
        low=s.low,
        info=s.info,
        files_scanned=s.files_scanned,
        duration=s.duration_seconds,
        project_types=", ".join(result.project_types) or "unknown",
        tool_options=tool_options,
        data_json=json.dumps(
            [i.model_dump(mode="json") for i in result.issues],
            ensure_ascii=False,
        ).replace("</", "<\\/"),  # prevent </script> from breaking the HTML parser
    )

    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    return html
