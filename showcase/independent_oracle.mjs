/* Independent deterministic Data Engineering oracle for the public reviewer demo.
   Recomputes original raw CSV with fixed-cent BigInt; never imports candidate code.
   Mirror of agentic/p3_oracle.py's deliberately strict data policy, independent JS.
*/
const COLUMNS=["Order ID","Region","Product","Quantity ","Unit Price","Discount","Order Date"];
const REGIONS=["Central","East","North","South","West"];
const AMOUNT=/^\d+(?:[.,]\d{1,2})?$/;
const QUANTITY=/^-?\d+(?: \d{3})*$/;

export class SourceValidationError extends Error{}

export function parseCsv(raw){
  if(typeof raw!=="string"||raw.length>300_000)throw new SourceValidationError("Invalid CSV input size");
  const txt=raw.replace(/^\uFEFF/,"");
  const rows=[];let row=[],field="",inside=false;
  for(let i=0;i<txt.length;i++){
    const c=txt[i];
    if(c==='"'){
      if(inside&&txt[i+1]==='"'){field+='"';i++;}
      else if(!inside&&field===""){inside=true;}
      else if(inside){inside=false;}
      else throw new SourceValidationError("Malformed quoted CSV value");
    }else if(c===","&&!inside){row.push(field);field="";}
    else if((c==="\n"||c==="\r")&&!inside){
      if(c==="\r"&&txt[i+1]==="\n")i++;
      row.push(field);if(row.some(x=>x!==""))rows.push(row);
      row=[];field="";
    }else{field+=c;}
  }
  if(inside)throw new SourceValidationError("Unterminated quoted CSV field");
  if(row.length||field!==""){row.push(field);rows.push(row);}
  return rows;
}
function cents(v,{blankZero=false}={}){
  if(v===""&&blankZero)return 0n;
  if(typeof v!=="string"||!AMOUNT.test(v))throw new SourceValidationError("Malformed original monetary amount");
  const [whole,fraction=""]=v.replace(",",".").split(".");
  return BigInt(whole)*100n+BigInt((fraction+"00").slice(0,2));
}
function qty(v){
  if(typeof v!=="string"||!QUANTITY.test(v))throw new SourceValidationError("Malformed source quantity");
  return BigInt(v.replace(/ /g,""));
}
function format(raw){
  const negative=raw<0n;const value=negative?-raw:raw;
  return (negative?"-":"")+(value/100n).toString()+"."+(value%100n).toString().padStart(2,"0");
}
function rowsAsObjects(raw,header){
  const rows=parseCsv(raw);
  if(JSON.stringify(rows[0])!==JSON.stringify(header))throw new SourceValidationError("Original CSV header changed");
  if(rows.some((x,i)=>i>0&&x.length!==header.length))throw new SourceValidationError("Invalid CSV row width");
  return rows.slice(1).map(values=>Object.fromEntries(header.map((x,i)=>[x,values[i]])));
}
export function independentRecalculation(source,output){
  const rows=rowsAsObjects(source,COLUMNS);
  const headers=rows.filter(x=>x["Order ID"]==="Order ID");
  const controls=rows.filter(x=>x["Order ID"]==="TOTAL");
  const tx=rows.filter(x=>/^SO-\d{5}$/.test(x["Order ID"]));
  if(headers.length!==1||controls.length!==1||tx.length+2!==rows.length)throw new SourceValidationError("Source rows or controls changed");
  const control=controls[0];
  const rawQuantity=tx.reduce((a,x)=>a+qty(x["Quantity "]),0n);
  const rawDiscount=tx.reduce((a,x)=>a+cents(x["Discount"],{blankZero:true}),0n);
  if(rawQuantity!==qty(control["Quantity "])||rawDiscount!==cents(control["Discount"])){
    throw new SourceValidationError("Original TOTAL does not reconcile");
  }
  const seen=new Set(),unique=[];
  for(const x of tx){
    const key=JSON.stringify(COLUMNS.map(col=>x[col]));
    if(!seen.has(key)){seen.add(key);unique.push(x);}
  }
  const prices=new Map();
  for(const x of unique){
    if(x["Unit Price"]!==""){
      const product=x["Product"];
      if(!prices.has(product))prices.set(product,new Set());
      prices.get(product).add(cents(x["Unit Price"]).toString());
    }
  }
  const totals=new Map(REGIONS.map(x=>[x,0n]));
  const observed=new Set();
  for(const x of unique){
    const rawRegion=x["Region"].trim().toLowerCase();
    const region=rawRegion.charAt(0).toUpperCase()+rawRegion.slice(1);
    if(!totals.has(region))throw new SourceValidationError("Invalid source region");
    const options=prices.get(x["Product"])||new Set();
    if(x["Unit Price"]===""&&options.size!==1)throw new SourceValidationError("Ambiguous missing product price");
    const price=x["Unit Price"]!==""?cents(x["Unit Price"]):BigInt([...options][0]);
    const revenue=qty(x["Quantity "])*price-cents(x["Discount"],{blankZero:true});
    totals.set(region,totals.get(region)+revenue);
    observed.add(region);
  }
  if(observed.size!==5)throw new SourceValidationError("Expected five regions");
  const outputRows=rowsAsObjects(output,["region","revenue"]);
  if(outputRows.length!==5||outputRows.some((x,i)=>x.region!==REGIONS[i]||! /^-?\d+\.\d{2}$/.test(x.revenue))){
    throw new SourceValidationError("Candidate output schema, order or values changed");
  }
  for(const item of outputRows){
    if(format(totals.get(item.region))!==item.revenue)throw new SourceValidationError("Independent regional reconciliation failed: "+item.region);
  }
  return {
    status:"PASSED",
    regions:Object.fromEntries(REGIONS.map(x=>[x,format(totals.get(x))])),
    netRevenue:format([...totals.values()].reduce((a,b)=>a+b,0n)),
    sourceCounts:{
      rawRows:rows.length,rawTransactions:tx.length,
      uniqueTransactions:unique.length,duplicateExtras:tx.length-unique.length,
    },
    controlQuantity:rawQuantity.toString(),
    controlDiscount:format(rawDiscount),
    method:"independent_bigint_oracle_no_candidate_execution"
  };
}
