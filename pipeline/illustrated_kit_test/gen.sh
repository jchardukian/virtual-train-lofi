#!/bin/bash
# usage: gen.sh <name> <prompt>   -- one high-quality 1536x1024 edit call with the approved plate as style reference
STYLE="Use the attached illustration ONLY as the art-style reference: match exactly its warm anime-inspired hand-painted look, clean linework, soft cel shading, rich detail, and golden-hour sunlight coming from the left with peach highlights and cool violet shadows. Do not copy its composition. "
KEY=" Everything that is not part of the described artwork must be a single flat solid pure chroma green colour (#00FF00) with clean sharp edges against it: no ground plane, no cast shadows on the green, no sky, no text, no watermark, no border."
curl -sS https://api.openai.com/v1/images/edits -H "Authorization: Bearer dummy" -F model=gpt-image-2 -F image=@../illus/scene.png -F size=1536x1024 -F quality=high --form-string "prompt=${STYLE}$2${KEY}" -o $1.json -w "$1 http %{http_code}\n"
python3 - "$1" "$2" <<'PY'
import json,base64,sys,time
n=sys.argv[1]; r=json.load(open(n+'.json'))
if 'data' in r:
    open(n+'.png','wb').write(base64.b64decode(r['data'][0]['b64_json'])); u=r['usage']
    d=u['input_tokens_details']; cost=u['output_tokens']*30e-6+d['image_tokens']*8e-6+d['text_tokens']*5e-6
    json.dump({'name':n,'model':'gpt-image-2','quality':'high','size':'1536x1024','endpoint':'images/edits','prompt':sys.argv[2],'usage':u,'est_cost_usd':round(cost,4)},open('ledger_'+n+'.json','w'),indent=1)
    print(n,'ok tokens',u['output_tokens'],'cost',round(cost,4))
else: print(n,'FAILED',str(r)[:300])
PY
