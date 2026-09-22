"""Exercise the rectangle's actual generated expressions with provider payloads.
These modeled checks complement native emulator checks; they do not prove any app's data availability.
"""
import json
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
FACE=ET.parse(ROOT/'app/src/main/res/raw/watchface.xml').getroot()
PANEL=FACE.find("Scene/ComplicationSlot[@slotId='7']")
EXPRESSIONS=sorted({n.text for n in PANEL.iter('Expression')} |
                   {n.get('expression') for n in PANEL.iter('Parameter')} |
                   {n.get('value') for n in PANEL.iter('Transform')})
JS = r'''
let input='';process.stdin.on('data',d=>input+=d);process.stdin.on('end',()=>{
 const {expressions, fixtures}=JSON.parse(input);
 const output=fixtures.map(values=>Object.fromEntries(expressions.map(expression=>{
  const code=expression.replace(/\[([^\]]+)\]/g,(_,key)=>JSON.stringify(values[key]??''));
  const icu=(format,stamp)=>{
   const date=new Date(Number(stamp));
   const hour=Number(new Intl.DateTimeFormat('en-GB',{timeZone:values.zone||'UTC',hour:'numeric',hourCycle:'h23'}).format(date));
   return format==='HH'?String(hour).padStart(2,'0'):`${hour%12||12} ${hour<12?'AM':'PM'}`;
  };
  const value=Function('clamp','numberFormat','icuText','textLength',`return (${code})`)(
   (v,a,b)=>Math.max(a,Math.min(v,b)),(_,n)=>Number(n).toLocaleString('en-US'),icu,s=>String(s).length);
  return [expression,value];
 })));
 process.stdout.write(JSON.stringify(output));
});
'''


def evaluate(*fixtures):
    result = subprocess.run(['node','-e',JS],input=json.dumps({'expressions':EXPRESSIONS,'fixtures':fixtures}),
                            text=True,capture_output=True,check=True)
    return json.loads(result.stdout)


def visible(option, values):
    """Resolve the actual XML branches; retain chart lines and text for assertions."""
    nodes=[]
    def visit(node):
        if node.tag=='Condition':
            for compare in node.findall('Compare'):
                exp=node.find(f"Expressions/Expression[@name='{compare.get('expression')}']").text
                if values[exp]:
                    visit(compare)
                    return
            default=node.find('Default')
            if default is not None:visit(default)
            return
        nodes.append(node)
        for child in node:visit(child)
    visit(PANEL.find(f"Complication[@type='{option}']"))
    texts=[]
    for node in nodes:
        if node.tag=='Font':
            template=node.find('Template')
            if template is None:texts.append(node.text or '')
            else:texts.append(template.text % tuple(values[p.get('expression')] for p in template))
    return nodes, texts


class RectangleDataTests(unittest.TestCase):
    def test_provider_text_and_units_are_preserved(self):
        for text in ['-40°C', '120°F', '0°', 'Meeting at noon', 'Rain likely after 11 PM']:
            values,=evaluate({'COMPLICATION.TEXT':text,'COMPLICATION.TITLE':'Provider title'})
            for kind in ['SHORT_TEXT','LONG_TEXT']:
                self.assertEqual(visible(kind,values)[1],[text,'Provider title'])

    def test_missing_data_is_not_a_fake_weather_reading(self):
        values,=evaluate({})
        for kind in ['SHORT_TEXT','LONG_TEXT']:
            self.assertEqual(visible(kind,values)[1],['—'])
        nodes,texts=visible('EMPTY',values)
        self.assertEqual(texts,['+ Complication'])
        self.assertFalse(any(n.tag=='Launch' for n in nodes))

    def test_progress_zero_invalid_range_and_over_goal(self):
        for kind,prefix,limits in [('RANGED_VALUE','RANGED_VALUE',{'MIN':0,'MAX':100}),
                                   ('GOAL_PROGRESS','GOAL_PROGRESS',{'TARGET_VALUE':100})]:
            for amount,expected in [(-1,0),(0,0),(50,115),(150,230)]:
                data={f'COMPLICATION.{prefix}_{k}':v for k,v in limits.items()}
                data[f'COMPLICATION.{prefix}_VALUE']=amount
                values,=evaluate(data)
                nodes,texts=visible(kind,values)
                endpoints=[values[n.get('value')] for n in nodes if n.tag=='Transform']
                self.assertEqual(endpoints,[] if expected==0 else [expected])
            values,=evaluate({f'COMPLICATION.{prefix}_{k}':0 for k in limits} |
                             {f'COMPLICATION.{prefix}_VALUE':50})
            self.assertFalse(any(n.tag=='Transform' for n in visible(kind,values)[0]))

if __name__=='__main__':unittest.main()
