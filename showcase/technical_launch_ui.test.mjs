import assert from "node:assert/strict";
import {test} from "node:test";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
const source=readFileSync(new URL("./technical.js",import.meta.url),"utf8");
const TEST_CODE="this-is-a-synthetic-unit-test-input-only";
class Node{
  constructor(){this.children=[];this.textContent="";this.value="";this.disabled=false;this.hidden=false;this.listeners={};this.classList={toggle(){}};}
  replaceChildren(...children){this.children=children;}
  append(...children){this.children.push(...children);}
  setAttribute(){}
  addEventListener(type,fn){this.listeners[type]=fn;}
}
test("completed launch permits next run without creating an orphan poll interval",async()=>{
  const els=new Map();
  const get=id=>{if(!els.has(id))els.set(id,new Node());return els.get(id);};
  let launched=0,intervals=0;
  const fetchImpl=async(path,options={})=>{
    const wrap=x=>({ok:true,json:async()=>x});
    if(path==="/api/delivery/launch/capabilities")return wrap({liveReady:true,maxRunsPerDay:5});
    if(path==="/api/delivery/launch"){assert.equal(JSON.parse(options.body).accessCode,TEST_CODE);launched++;return wrap({id:"2ac3fd19-f652-474c-9fbb-4f8ca925d1e3"});}
    if(path.startsWith("/api/delivery/launch/session/"))return wrap({status:"completed",conclusion:"success",jobs:[],events:[]});
    throw Error("Unexpected request");
  };
  runInNewContext(source,{
    document:{documentElement:{lang:"pl"},getElementById:get,createElement:()=>new Node()},
    window:{addEventListener(){}},fetch:fetchImpl,URL,
    setInterval:()=>{intervals++;return 1;},clearInterval:()=>{}
  });
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(get("technical-start").disabled,false);
  for(let n=1;n<=2;n++){
    get("technical-access").value=TEST_CODE;
    await get("technical-start-form").listeners.submit({preventDefault(){}});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(launched,n);
    assert.equal(get("technical-start").disabled,false);
  }
  assert.equal(intervals,0);
});
