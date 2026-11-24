const fs=require('fs'),assert=require('assert/strict'),path=require('path');
const root=path.resolve(__dirname,'..');
const model=require(path.join(root,'assets/qblade_model.js'));
const ref=JSON.parse(fs.readFileSync(path.join(root,'data/qblade_v80_reference.json')));
const fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'html_model_fixtures.json')));
const scale={aero:1000,electric:1000,moment:1000};let count=0;
for(const c of fixtures){const got=model.evaluate(ref,c.id,c.params);for(const[k,expected]of Object.entries(c.expected)){if(k==='aep'){assert.ok(Math.abs(got.aep-expected)<1e-8*Math.max(1,Math.abs(expected)),k);continue}expected.forEach((v,j)=>assert.ok(Math.abs(got[k][j]*(scale[k]||1)-v)<1e-9*Math.max(1,Math.abs(v)),c.id+' '+k+' '+j+' got '+got[k][j]+' expected '+v));count+=expected.length;}}
console.log('PASS',fixtures.length,'cases,',count,'numeric values: HTML and Python engines agree');
