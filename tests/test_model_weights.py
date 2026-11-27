"""Weights stay attached to source groups and selection never changes cost scope."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = '/Users/jonathan.diaz/.nvm/versions/node/v24.18.0/bin/node'

class ModelWeightTests(unittest.TestCase):
    def test_groups_and_selection_bridge(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El {
 constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};this.style={};this.textContent='';}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=[...children];}
 setAttribute(key,value){this[key]=value;}
}
const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,new El());return nodes.get(id);};
const element=(tag,attrs={},content='')=>Object.assign(new El(tag),attrs,{textContent:content});
const scope={console,matchMedia:()=>({matches:false}),$,element,f:(x,n)=>x.toFixed(n),document:{createElement:tag=>new El(tag)}};
vm.createContext(scope);
vm.runInContext(fs.readFileSync('assets/ifc_viewer.js','utf8'),scope);
vm.runInContext(fs.readFileSync('assets/cost_preview.js','utf8'),scope);
const model=JSON.parse(fs.readFileSync('data/v80_v5_mesh.json','utf8'));
scope.model=model;
vm.runInContext(`
IFCView.data=model;
const groupsA=modelWeightGroups(model.meshes,'A'),groupsB=modelWeightGroups(model.meshes,'B');
if(groupsA.length!==35||groupsB.length!==37)throw Error('variant groups');
const pala=groupsA.find(x=>x.name==='Pala FRP NACA 0018');
if(pala.meshCount!==3||pala.totalKg!==1200)throw Error('duplicate instance weight');
const carenado=groupsA.find(x=>x.name==='Carenado FRP de brazo NACA 0022');
if(carenado.totalKg!==429||carenado.unitWeight!=='71,5 kg')throw Error('unit mass must use declared group total divided by count');
if(groupsA.find(x=>x.name==='T:Fundación existente').totalKg!==41785)throw Error('concrete density mistaken for mass');
if(groupsA.find(x=>x.name==='T:Pernería torre').unitKg!==0.375)throw Error('tower hardware unit mass');
if(groupsA.find(x=>x.name==='T:Montantes L150×150×15 / L150×150×10').unitKg!==1351/8)throw Error('group mass/count');
if(modelUnitWeight('0,0 kg','6').kg!==0||modelUnitWeight('150 kg','0').kg!==null||modelUnitWeight('150 kg','Sin dato').kg!==null||modelUnitWeight('Sin dato','6').kg!==null)throw Error('zero or missing denominator');
if(modelGroupQuantity('400 elementos')!==400||modelGroupQuantity('1.200 unidades')!==1200)throw Error('quantity labels');
if(modelWeightKg('0,0 kg')!==0||modelWeightKg('sin dato')!==null||modelWeightKg('71,4 kg')!==71.4)throw Error('weight parser');
const CostView={layer:pala.layer,package:'Fabricación Aspa',search:'original'};
let opened=null;showIfcWeightGroup=group=>{opened=group;};
updateCostPreview();
if(CostPreview.sourceKey!==null)throw Error('initial scope');
const groupKey=pala.key;
`,scope);
function buttons(node){return [node,...node.children.flatMap(buttons)].filter(x=>x.tagName==='button');}
const pick=buttons($('cost-model-weights')).find(x=>x.dataset.modelGroup?.includes('Pala FRP NACA 0018'));
assert(pick,'source component is selectable');pick.onclick();
vm.runInContext(`
if(CostPreview.sourceKey!==groupKey)throw Error('source selection lost');
if(CostView.package!=='Fabricación Aspa'||CostView.search!=='original')throw Error('cost filters changed');
if($('cost-preview-title').textContent!=='Pala FRP NACA 0018')throw Error('preview title');
$('cost-preview-open').onclick();if(opened.key!==groupKey)throw Error('open point 5 mismatch');
IFCView.offer='B';updateCostPreview();if(CostPreview.sourceKey!==null)throw Error('variant should reset component');
CostView.layer='unassigned';updateCostPreview();if(!$('cost-preview-open').hidden||!$('cost-preview-canvas').hidden)throw Error('unassigned should hide geometry');
`,scope);
assert.equal(buttons($('cost-model-weights')).length,0);
'''
        result = subprocess.run([NODE, '-e', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == '__main__':
    unittest.main()
