import assert from "node:assert/strict";
import test from "node:test";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";

const source=readFileSync(new URL("./delivery_status.js",import.meta.url),"utf8");

class FakeElement {
  constructor(){this.children=[];this.textContent="";this.attributes={};this.className="";}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=[...children];}
  setAttribute(k,v){this.attributes[k]=v;}
  removeAttribute(k){delete this.attributes[k];}
}
async function caseStudy({publication,status="completed",conclusion="success",lang="pl"}){
  const elements=new Map();
  const document={
    documentElement:{lang},
    getElementById(id){if(!elements.has(id))elements.set(id,new FakeElement());return elements.get(id);},
    createElement(){return new FakeElement();}
  };
  const latest={
    available:true,
    run:{id:44501856719,status,conclusion,
      url:"https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44501856719"},
    phases:[],
    publication
  };
  runInNewContext(source,{
    document,
    window:{addEventListener(){}},
    URL,
    setInterval(){},
    fetch:async()=>({ok:true,json:async()=>latest})
  });
  await new Promise(resolve=>setImmediate(resolve));
  const header=elements.get("delivery-live-state");
  assert.ok(header.children.length>0,"Failed to render current run");
  return header.children[0].children[1].textContent;
}
test("green GitHub Actions with skipped P4 is NOT presented as verified delivery",async()=>{
  const result=await caseStudy({publication:{status:"not_yet_verified"}});
  assert.match(result,/NIEPOTWIERDZONY/);
  assert.doesNotMatch(result,/ZWERYFIKOWANO/);
});
test("Only full matching draft PR with independent CI reports verified",async()=>{
  const result=await caseStudy({publication:{status:"verified_draft_awaiting_human"}});
  assert.match(result,/ZWERYFIKOWANO/);
});
test("separate later exact-SHA CI pending is stated explicitly",async()=>{
  const result=await caseStudy({publication:{status:"draft_ci_not_confirmed"}});
  assert.match(result,/niepotwierdzone/);
});
test("English recruiter sees explicit nonverified verdict",async()=>{
  const result=await caseStudy({publication:{status:"not_yet_verified"},lang:"en"});
  assert.match(result,/NOT VERIFIED/);
});
