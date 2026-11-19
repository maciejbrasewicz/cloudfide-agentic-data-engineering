/* Static evidence site server. Node 22+, dependency-free, no API or private data. */
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { createLiveGateway } from "./live_gateway.mjs";
import { createDeliveryGateway } from "./delivery_gateway.mjs";
import { createRecalculationGateway } from "./recalculation_gateway.mjs";
import { createFullDeliveryLauncher } from "./delivery_launch.mjs";

const ROOT = dirname(fileURLToPath(import.meta.url));
const MEDIA = new Map([
  [".html","text/html; charset=utf-8"],
  [".js","text/javascript; charset=utf-8"],
  [".css","text/css; charset=utf-8"],
  [".json","application/json; charset=utf-8"],
  [".svg","image/svg+xml"],
  [".txt","text/plain; charset=utf-8"]
]);
const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
  "form-action 'none'",
  "upgrade-insecure-requests"
].join("; ");
const HEADERS = Object.freeze({
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Content-Security-Policy": CSP,
  "Cross-Origin-Resource-Policy": "same-origin"
});

export function createAppServer({
  gateway=createLiveGateway({env:{}}),
  deliveryGateway=createDeliveryGateway(),
  recalculationGateway=createRecalculationGateway(),
  fullDeliveryLauncher=createFullDeliveryLauncher()
}={}){
  return createServer(async(req,res)=>{
    const target=new URL(req.url||"/","http://localhost");
    if(await gateway.handle(req,res,target))return;
    if(await deliveryGateway.handle(req,res,target))return;
    if(await recalculationGateway.handle(req,res,target))return;
    if(await fullDeliveryLauncher.handle(req,res,target))return;
    const method = req.method;
    if(method!=="GET" && method!=="HEAD"){
      res.writeHead(405,{"Allow":"GET, HEAD",...HEADERS}); res.end(); return;
    }
    let location;
    try{
      const uri=new URL(req.url||"/","http://localhost");
      if(uri.pathname.includes("%00")) throw Error("Null byte");
      const decoded=decodeURIComponent(uri.pathname);
      if(decoded.includes("\\") || decoded.includes("\0")) throw Error("Malformed path");
      location=decoded==="/"?"/index.html":decoded;
    }catch{
      res.writeHead(400,HEADERS);res.end();return;
    }
    // Existing Engineering Lab bookmarks resolve to the same unified portal.
    if(location==="/engineering.html"){
      const requested=new URL(req.url||"/","http://localhost").searchParams.get("lang");
      const language=requested==="en"?"en":"pl";
      res.writeHead(302,{...HEADERS,"Cache-Control":"no-store","Location":"/?lang="+language+"#technical"});
      res.end();return;
    }
    // Only explicit public assets; block dotfiles, source files and directory traversal.
    const allowed = new Set(["/index.html","/styles.css","/technical.css","/app.js","/technical.js","/delivery_status.js","/reviewer_console.js","/favicon.svg","/data/autonomous_run.json","/data/latest_autonomous_run.json","/data/evidence.json","/data/agent_trace.json","/data/foundry_reports.json"]);
    if(!allowed.has(location)){
      res.writeHead(404,HEADERS);res.end();return;
    }
    const file=resolve(ROOT,"."+location);
    if(file!==ROOT && !file.startsWith(ROOT+sep)){
      res.writeHead(404,HEADERS);res.end();return;
    }
    try{
      const info=await stat(file);
      if(!info.isFile())throw Error("Not a file");
      const payload=await readFile(file);
      const type=MEDIA.get(extname(file))||"application/octet-stream";
      res.writeHead(200,{
        ...HEADERS,
        "Content-Type":type,
        "Content-Length":String(payload.byteLength),
        "Cache-Control":location.endsWith(".json")?"no-store":"public, max-age=300"
      });
      if(method==="HEAD")res.end();else res.end(payload);
    }catch{
      res.writeHead(404,HEADERS);res.end();
    }
  });
}

if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const raw=Number(process.env.PORT||4173);
  const port=Number.isInteger(raw)&&raw>0&&raw<65536?raw:4173;
  const host=process.env.HOST||"0.0.0.0";
  createAppServer().listen(port,host,()=>console.log("Engineering Intelligence listening on "+host+":"+port));
}
