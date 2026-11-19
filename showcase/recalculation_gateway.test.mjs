import assert from "node:assert/strict";
import {test} from "node:test";
import {readFile} from "node:fs/promises";
import {createRecalculationGateway} from "./recalculation_gateway.mjs";

const source=await readFile(new URL("../sales.csv",import.meta.url));
const output=await readFile(new URL("../revenue_by_region.csv",import.meta.url));

function responder(){
  return {
    status:null,body:"",
    writeHead(status){this.status=status;},
    end(content){this.body=content||"";}
  };
}
async function invoke(gateway,{origin,host="local.test",ip="127.0.0.1",method="POST",body=""}={}){
  const request={
    method,headers:{"host":host,...(origin?{origin}:{})},
    socket:{remoteAddress:ip},
    async *[Symbol.asyncIterator](){yield Buffer.from(body);}
  };
  const response=responder();
  assert.equal(await gateway.handle(request,response,new URL("https://local.test/api/review/recalculate")),true);
  return {status:response.status,body:JSON.parse(response.body)};
}
function fixtureFetch(s=source,o=output){
  let count=0;
  const fetchImpl=async url=>{
    count++;
    const bytes=url.includes("sales.csv")?s:o;
    return {
      ok:true,status:200,headers:new Headers({"content-length":String(bytes.byteLength)}),
      arrayBuffer:async()=>bytes
    };
  };
  return {fetchImpl,getCalls:()=>count};
}

test("live public button verifies immutable original source and independent five-region arithmetic",async()=>{
  const mock=fixtureFetch();
  const gateway=createRecalculationGateway({fetchImpl:mock.fetchImpl,now:()=>1_000_000});
  const real=await invoke(gateway);
  assert.equal(real.status,200);
  assert.equal(real.body.status,"PASSED");
  assert.equal(real.body.netRevenue,"2570247.03");
  assert.equal(real.body.sourceCounts.uniqueTransactions,1500);
  assert.equal(real.body.controlQuantity,"37150");
  assert.equal(real.body.agentRunExecuted,false);
  assert.equal(real.body.sourceSha256,"811573152aa287b14d5006ce6901ebd0ca17586149e16a5b79de5ae69684c1d4");
  assert.equal(mock.getCalls(),2);
  const repeated=await invoke(gateway);
  assert.equal(repeated.status,200);
  assert.equal(repeated.body.cached,true);
  assert.equal(mock.getCalls(),2);
});

test("tampered published revenue fails closed; never report fake success",async()=>{
  const tampered=Buffer.from(output.toString().replace("515824.67","515824.68"));
  const gateway=createRecalculationGateway({fetchImpl:fixtureFetch(source,tampered).fetchImpl});
  const result=await invoke(gateway);
  assert.equal(result.status,503);
  assert.equal(result.body.status,"UNAVAILABLE");
});

test("foreign-origin requests and non-POST requests cannot execute",async()=>{
  let calls=0;
  const gateway=createRecalculationGateway({fetchImpl:async()=>{calls++;throw Error("Should never fetch");}});
  assert.equal((await invoke(gateway,{method:"GET"})).status,405);
  assert.equal((await invoke(gateway,{origin:"https://evil.example"})).status,403);
  assert.equal(calls,0);
});

test("oversized request body is rejected without returning validation PASS",async()=>{
  const gateway=createRecalculationGateway({fetchImpl:fixtureFetch().fetchImpl});
  const response=await invoke(gateway,{body:"x".repeat(513)});
  assert.equal(response.status,503);
  assert.notEqual(response.body.status,"PASSED");
});
