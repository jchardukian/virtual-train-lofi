// lofitrain-control: private mailbox between the agent and the stream server, plus read access to the archive.
// Every request must carry the shared key in X-Key. Nothing here is public.
//   GET  /obj/<key>            read an archive object (masters, music, tunnel clips)
//   PUT  /obj/control/<...>    write under control/ only (status, logs, command results)
//   PUT  /obj/stream/<...>     write under stream/ only (prepared stream pieces)
//   GET  /cmd                  the current command for the server (control/cmd.json)
export default {
  async fetch(req, env) {
    const key = req.headers.get("X-Key") || "";
    if (!env.CONTROL_KEY || key.length !== env.CONTROL_KEY.length || !timingSafe(key, env.CONTROL_KEY))
      return new Response("forbidden", { status: 403 });
    const url = new URL(req.url);
    const p = decodeURIComponent(url.pathname);
    if (p === "/cmd" && req.method === "GET") return get(env, "control/cmd.json");
    if (p.startsWith("/obj/")) {
      const k = p.slice(5);
      if (!k || k.includes("..")) return new Response("bad key", { status: 400 });
      if (req.method === "GET") return get(env, k, req.headers.get("Range"));
      if (req.method === "PUT") {
        if (!(k.startsWith("control/") || k.startsWith("stream/"))) return new Response("read-only", { status: 403 });
        await env.ARCHIVE.put(k, req.body, { httpMetadata: { contentType: req.headers.get("Content-Type") || "application/octet-stream" } });
        return new Response("ok");
      }
    }
    return new Response("not found", { status: 404 });
  },
};

async function get(env, k, range) {
  const opts = {};
  if (range) {
    const m = /bytes=(\d+)-(\d*)/.exec(range);
    if (m) opts.range = m[2] ? { offset: +m[1], length: +m[2] - +m[1] + 1 } : { offset: +m[1] };
  }
  const o = await env.ARCHIVE.get(k, opts);
  if (!o) return new Response("not found", { status: 404 });
  const h = new Headers();
  o.writeHttpMetadata(h);
  h.set("ETag", o.httpEtag);
  const len = opts.range ? (opts.range.length ?? (o.size - opts.range.offset)) : o.size;
  h.set("Content-Length", String(len));
  if (opts.range) h.set("Content-Range", `bytes ${opts.range.offset}-${opts.range.offset + len - 1}/${o.size}`);
  return new Response(o.body, { status: opts.range ? 206 : 200, headers: h });
}

function timingSafe(a, b) {
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
