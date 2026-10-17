import {test} from "node:test";
import assert from "node:assert/strict";
import {partition,retryable,send} from "../queue.js";
test("queue is isolated by tenant/factory/user and ordered",()=>{
  assert.deepEqual(partition([{owner:"a",created:2},{owner:"b",created:0},{owner:"a",created:1}],"a").map(x=>x.created),[1,2]);
});
test("permanent conflicts do not loop",()=>{
  for(const s of [400,401,403,404,409,422]) assert.equal(retryable(s),false);
  for(const s of [0,408,429,500,503]) assert.equal(retryable(s),true);
});
test("partial send retries stable incident and action identifiers",async()=>{
  const item={incident:{id:"i"},action:{id:"a"}}, calls=[];
  await assert.rejects(send(item,async(path,body)=>{calls.push([path,body]);if(path.endsWith("actions"))throw Error("offline");}));
  await send(item,async(path,body)=>calls.push([path,body]));
  assert.equal(calls[0][1].body,calls[2][1].body);
  assert.equal(calls[1][1].body,calls[3][1].body);
});
