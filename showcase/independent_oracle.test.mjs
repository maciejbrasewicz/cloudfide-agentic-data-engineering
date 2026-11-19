import assert from "node:assert/strict";
import {test} from "node:test";
import {readFile} from "node:fs/promises";
import {independentRecalculation,parseCsv,SourceValidationError} from "./independent_oracle.mjs";

const root=new URL("../",import.meta.url);
const sales=await readFile(new URL("./sales.csv",root),"utf8");
const output=await readFile(new URL("./revenue_by_region.csv",root),"utf8");

test("independent BigInt oracle reconciles 1507 raw rows and all five regions",()=>{
  const actual=independentRecalculation(sales,output);
  assert.equal(actual.status,"PASSED");
  assert.equal(actual.netRevenue,"2570247.03");
  assert.equal(actual.sourceCounts.rawRows,1507);
  assert.equal(actual.sourceCounts.rawTransactions,1505);
  assert.equal(actual.sourceCounts.uniqueTransactions,1500);
  assert.equal(actual.sourceCounts.duplicateExtras,5);
  assert.equal(actual.controlQuantity,"37150");
  assert.equal(actual.controlDiscount,"65924.67");
  assert.deepEqual(actual.regions,{
    Central:"515824.67",East:"442219.91",North:"665897.52",
    South:"504036.04",West:"442268.89",
  });
});

test("public recomputation rejects even a one-cent candidate tampering",()=>{
  const hacked=output.replace("515824.67","515824.68");
  assert.throws(()=>independentRecalculation(sales,hacked),/reconciliation failed/);
});

test("public recomputation refuses altered raw control",()=>{
  const hacked=sales.replace("37150,,65924.67","37151,,65924.67");
  assert.throws(()=>independentRecalculation(hacked,output),/TOTAL does not reconcile/);
});

test("public recomputation refuses unexpected source or output fields",()=>{
  assert.throws(()=>independentRecalculation(sales.replace("Order ID,Region","Order ID,Place"),output),/header changed/);
  assert.throws(()=>independentRecalculation(sales,output.replace("region,revenue","revenue,region")),/header changed/);
});

test("parser supports quoted commas without silently truncating columns",()=>{
  assert.deepEqual(parseCsv('a,b\n"test, source","x""y"\n'),[["a","b"],["test, source",'x"y']]);
  assert.throws(()=>parseCsv('a,b\n"unterminated,value\n'),SourceValidationError);
});
