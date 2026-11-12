#!/usr/bin/env python3
"""Generate a portable, offline installation guide and before/after gallery."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    looks = json.loads((ROOT / "research/bake-manifest.json").read_text())["looks"]
    sources = json.loads((ROOT / "research/example-sources.json").read_text())["images"]
    data = {"looks": [{k: x[k] for k in ["id", "name", "filename", "cube", "pf3"]} for x in looks],
            "sources": [{"id": x["id"], "name": x["name"],
                         "file": "examples/source/" + x["id"] + (".png" if x["id"] == "g7x-iii-canon-neutral" else ".jpg")}
                        for x in sources]}
    rows = "".join(f'<tr><td>{x["name"]}</td><td><a href="{x["pf3"]}">{x["filename"]}</a></td><td><a href="{x["cube"]}">Desktop LUT</a></td></tr>' for x in looks)
    html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>G7X Film Lab — start here</title><style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#242521;background:#f4f1eb;line-height:1.6;font-size:16px}*{box-sizing:border-box}body{margin:0}main{max-width:1100px;margin:auto;padding:42px 24px 64px}a{color:#405b42;text-underline-offset:3px}.eyebrow{font-size:12px;letter-spacing:.15em;font-weight:700;text-transform:uppercase;color:#66695d}h1{font-family:Georgia,serif;font-weight:400;font-size:clamp(2.5rem,7vw,4.8rem);line-height:1.06;letter-spacing:-.045em;max-width:760px;margin:18px 0}h2{font:400 32px Georgia,serif;margin:36px 0 16px}.lead{font-size:19px;color:#595b51;max-width:730px}.status{border-left:3px solid #9d885d;padding:8px 15px;color:#5d594e;max-width:800px;font-size:14px}.steps{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}.card{padding:22px;background:#fffdfa;border:1px solid #dedbd3;border-radius:10px}.stepno{font-size:12px;letter-spacing:.08em;color:#737767}.card h3{font-size:20px;margin:6px 0 8px}.card p{margin:8px 0}.button{display:inline-block;padding:9px 14px;margin:5px 6px 3px 0;border:1px solid #405b42;border-radius:6px;text-decoration:none;color:#405b42}.button.primary{background:#405b42;color:white}table{border-collapse:collapse;width:100%;background:#fffdfa}td,th{text-align:left;padding:12px 14px;border-bottom:1px solid #dedbd3}th{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:#6a6e5f}.controls{display:flex;gap:14px;flex-wrap:wrap;margin:20px 0}label{font-size:13px;color:#555b4d;flex:1;min-width:220px}select{display:block;padding:12px;width:100%;margin-top:5px;background:#fffdfa;border:1px solid #aaa998;border-radius:5px;font:inherit;color:#242521}.comparison{position:relative;width:100%;overflow:hidden;border-radius:8px;background:#dedbd3;--split:50%}.comparison>img{display:block;width:100%;height:auto}.before{position:absolute;inset:0;clip-path:inset(0 calc(100% - var(--split)) 0 0)}.before img{width:100%;height:100%;object-fit:contain}.rule{position:absolute;top:0;bottom:0;left:var(--split);width:2px;background:white;box-shadow:0 0 5px #0006}.image-label{position:absolute;top:14px;padding:4px 10px;background:#181a17b8;color:white;font-size:12px;border-radius:4px;pointer-events:none}.left-label{left:14px}.right-label{right:14px}.range{width:100%;margin:18px 0 0;accent-color:#405b42}.caption{font-size:13px;color:#64665c}.links{display:flex;gap:18px;flex-wrap:wrap;margin-top:24px}code{font:13px ui-monospace,monospace;background:#e8e5dc;padding:2px 5px;border-radius:3px}footer{font-size:13px;color:#66695d;border-top:1px solid #d5d2c8;margin-top:42px;padding-top:20px}@media(max-width:650px){main{padding:24px 16px}.steps{grid-template-columns:1fr}td,th{padding:10px 7px;font-size:13px}}
</style></head><body><main>
<div class="eyebrow">G7X Film Lab · version 0.1.0 · five film-inspired looks</div>
<h1>A little film character.<br>Your everyday camera.</h1>
<p class="lead">Portra 400, Gold 200, Ektar 100, Pro 400H and Tri-X 400. Ready-made Canon Picture Styles, desktop LUTs, and examples you can compare.</p>
<p class="status">The files pass Canon’s native parser and G7 X III model compiler offline. Physical USB registration and camera JPEG output have not been tested. These are film-inspired renderings, not a measured match to a particular film scan.</p>
<h2>Install on your G7 X Mark III</h2>
<div class="steps">
<section class="card"><div class="stepno">01 / ONE-TIME SETUP</div><h3>Get Canon’s registration tool</h3><p>Install Picture Style File Registration Tool from Canon. The profiles in this folder are already built.</p><a class="button primary" href="https://sg.canon/en/support/0200746802">Mac download</a><a class="button" href="https://sg.canon/en/support/0200746702">Windows download</a><p class="caption">Mac 1.1.0 lists macOS 13–15; USB registration on macOS 26 is unverified. Windows 10/11 is listed.</p></section>
<section class="card"><div class="stepno">02 / CONNECT</div><h3>Plug in the camera</h3><p>Use a USB-C data cable, turn the camera on, and select <strong>P</strong> mode. Open Canon’s registration tool and select the G7 X Mark III.</p><p class="caption">On Mac: Applications → Canon Utilities → Picture Style File Registration Tool. Close another Canon connection app if it blocks detection.</p></section>
<section class="card"><div class="stepno">03 / CHOOSE A SLOT</div><h3>Register a profile</h3><p>Choose <strong>Register Picture Style File</strong>, select a <strong>User Def.</strong> slot, use its folder button to choose a file from <code>profiles</code>, then click <strong>Register</strong>.</p><p class="caption">The camera has three slots. A useful starting set is Portra 400, Gold 200 and Tri-X 400. Replace a slot later to try the other looks. Exact labels above are verified for the Windows tool.</p></section>
<section class="card"><div class="stepno">04 / SHOOT</div><h3>Select the look on camera</h3><p>After registration completes, disconnect USB. Open the camera’s <strong>Picture Style</strong> control and select the User Def. slot. Try <strong>RAW + JPEG</strong> with fixed white balance for the first comparison.</p><p class="caption">Keep the supplied extra contrast/saturation controls initially. The stock’s ISO number is a name, not a camera ISO setting.</p></section>
</div>
<p><a href="docs/INSTALL.md">Detailed installation and troubleshooting</a></p>
<table><thead><tr><th>Look</th><th>Camera file</th><th>Photo / video editor</th></tr></thead><tbody>@@ROWS@@</tbody></table>
<p class="caption">Desktop LUTs expect finished SDR sRGB, range 0–1. Convert RAW/log/HDR into that space first, and apply a look once. Grain and halation are outside a 3D LUT.</p>
<h2>Find your look</h2>
<p>Compare the same photo before and after. Every after-image below was rendered through the exact desktop LUT in this download, with no extra grade.</p>
<div class="controls"><label>Film-inspired look<select id="look"></select></label><label>Photograph<select id="photo"></select></label></div>
<div class="comparison" id="comparison"><img id="after" src="examples/rendered/portra400/skin-portrait.jpg" alt="Selected film-inspired LUT preview"><div class="before"><img id="before" src="examples/source/skin-portrait.jpg" alt="Original source photograph"></div><div class="rule"></div><div class="image-label left-label">Original</div><div class="image-label right-label" id="lookLabel">Portra 400</div></div>
<label class="caption" for="split">Before / after split</label><input id="split" class="range" type="range" min="0" max="100" value="50" aria-label="Move the original and film-preview comparison split">
<p class="caption" id="sourceCaption"></p>
<div class="links"><a href="previews/overview.jpg">All five on one photo</a><a href="examples/source/CREDITS.md">Photograph credits</a><a href="docs/VALIDATION.md">Canon software previews and checks</a><a href="docs/FILM_MODELS.md">How the looks were made</a></div>
<footer>Independent of Canon, Kodak and Fujifilm. Film modeling uses Fotufilm data, © 2026 MUAStudio Inc., <a href="https://fotufilm.com">fotufilm.com</a>. Look data is <a href="DATA-LICENSE.md">CC BY-SA 4.0</a>; project code is MIT. This guide and gallery work offline; Canon download links require internet.</footer>
</main><script>
const data=@@DATA@@;
const look=document.getElementById('look'),photo=document.getElementById('photo');
for(const item of data.looks){const o=document.createElement('option');o.value=item.id;o.textContent=item.name;look.append(o)}
for(const item of data.sources){const o=document.createElement('option');o.value=item.id;o.textContent=item.name;photo.append(o)}
photo.value='skin-portrait';
function update(){const l=data.looks.find(x=>x.id===look.value),p=data.sources.find(x=>x.id===photo.value);document.getElementById('before').src=p.file;document.getElementById('after').src=`examples/rendered/${l.id}/${p.id}.jpg`;document.getElementById('lookLabel').textContent=l.name;document.getElementById('sourceCaption').textContent=p.name+' · Digital LUT preview. The G7 X III sample is a Canon software RAW render, not an out-of-camera styled JPEG.'}
look.addEventListener('change',update);photo.addEventListener('change',update);document.getElementById('split').addEventListener('input',e=>document.getElementById('comparison').style.setProperty('--split',e.target.value+'%'));update();
</script></body></html>'''
    (ROOT / "START-HERE.html").write_text(html.replace("@@ROWS@@", rows).replace("@@DATA@@", json.dumps(data)), encoding="utf-8")


if __name__ == "__main__": main()
