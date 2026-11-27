"""Nested page refresh and reversible bulk visibility controls."""
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NODE='/Users/jonathan.diaz/.nvm/versions/node/v24.18.0/bin/node'

class PageControlTests(unittest.TestCase):
    def run_js(self, script):
        result=subprocess.run([NODE,'-e',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_bulk_visibility_from_all_none_and_partial(self):
        self.run_js(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const button={setAttribute(k,v){this[k]=v;}},inputs=['palas','torre'].map(layer=>({checked:true,dataset:{layer}}));
const scope={matchMedia:()=>({matches:false}),$:id=>id==='ifc-layers'?{querySelectorAll:()=>inputs}:button};vm.createContext(scope);
vm.runInContext(fs.readFileSync('assets/ifc_viewer.js','utf8'),scope);
vm.runInContext("IFCView.data={layers:[{name:'palas',defaultVisible:true,rotating:true},{name:'torre',defaultVisible:true,rotating:false}]};",scope);
let changes=0;inputs.forEach(input=>input.onchange=()=>{changes++;scope.updateIfcLayerToggle();});
scope.updateIfcLayerToggle();assert.equal(button.textContent,'Ocultar todas');
scope.toggleIfcLayers();assert(inputs.every(x=>!x.checked));assert.equal(button.textContent,'Mostrar todas');
scope.toggleIfcLayers();assert(inputs.every(x=>x.checked));assert.equal(button.textContent,'Ocultar todas');
inputs[0].checked=false;scope.updateIfcLayerToggle();scope.toggleIfcLayers();assert(inputs.every(x=>x.checked));assert.equal(changes,6);
scope.setIfcLayers(l=>l.rotating);assert(inputs[0].checked);assert(!inputs[1].checked);
''')

    def test_refresh_roundtrip_preserves_nested_viewports_and_stops_on_user_input(self):
        self.run_js(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const store=new Map(),timers=[],frames=[];
function makeFrame(){
 const nodes=new Map(),events=new Map(),details=[{open:true},{open:false}],main={scrollTop:0};
 const frame={scrollX:0,scrollY:0,events,location:{pathname:'/',reload(){frame.reloaded=true;}},sessionStorage:{setItem:(k,v)=>store.set(k,v),getItem:k=>store.get(k)||null,removeItem:k=>store.delete(k)},scrollTo(x,y){this.scrollX=x;this.scrollY=y;},addEventListener(t,f){events.set(t,f);},removeEventListener(t){events.delete(t);}};
 const makeEl=tag=>({tag,children:[],style:{},append(x){this.children.push(x);if(x.id)nodes.set(x.id,x);},remove(){nodes.delete(this.id);},setAttribute(k,v){this[k]=v;},querySelector(){return this.span||(this.span={textContent:'Actualizar'});}});
 const anchor={id:'step-6',getBoundingClientRect:()=>({top:1500-frame.scrollY})};nodes.set(anchor.id,anchor);
 frame.document={nodes,details,main,head:makeEl('head'),body:makeEl('body'),createElement:makeEl,getElementById:id=>nodes.get(id)||null,querySelector:selector=>selector.includes('stMain')?main:null,querySelectorAll:selector=>selector.startsWith('details')?details:[anchor]};return frame;
}
const inner=makeFrame(),wrapper=makeFrame(),host=makeFrame();inner.parent=wrapper;wrapper.parent=host;host.parent=host;frames.push(inner,wrapper,host);
const scope={window:inner,sessionStorage:inner.sessionStorage,console,setTimeout:(fn,delay)=>{const t={fn,delay};timers.push(t);return t;},clearTimeout:t=>t.cancelled=true,requestAnimationFrame:fn=>fn(),costSave:()=>scope.saved=true};vm.createContext(scope);
vm.runInContext(fs.readFileSync('assets/page_refresh.js','utf8'),scope);
inner.scrollY=1600;host.document.main.scrollTop=340;wrapper.scrollY=5;
scope.initPageRefresh();const button=host.document.nodes.get('vawt-page-refresh');assert(button,'button is in top viewport');button.onclick();assert(host.reloaded);assert(scope.saved);
inner.scrollY=0;host.document.main.scrollTop=0;wrapper.scrollY=0;inner.document.details[0].open=false;
scope.initPageRefresh();assert.equal(inner.scrollY,1600);assert.equal(wrapper.scrollY,5);assert.equal(host.document.main.scrollTop,340);assert(inner.document.details[0].open);
// A genuine user scroll cancels pending corrections; no later jump back.
inner.events.get('wheel')();inner.scrollY=2200;for(const t of timers)if(!t.cancelled)t.fn();assert.equal(inner.scrollY,2200);
assert.equal(store.size,0,'restore is one-shot');
// Cross-origin embedding safely falls back to the accessible local viewport.
const standalone=makeFrame();Object.defineProperty(standalone,'parent',{get(){throw Error('blocked');}});
// Standard cross-origin WindowProxy permits parent access but denies its document.
const cross=makeFrame();cross.parent={get document(){throw Error('cross-origin');}};
assert.equal(scope.pageRefreshWindows(cross).length,1);
''')

if __name__=='__main__':unittest.main()
