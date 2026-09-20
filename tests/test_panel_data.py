"""Exercise generated WFF branches with explicit fixtures, not live-device evidence.

The Node evaluator models documented WFF arithmetic/formatting for boundary tests.
Official WFF validation and native emulator rendering remain separate checks.
"""
import json
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FACE = ET.parse(ROOT/'app/src/main/res/raw/watchface.xml').getroot()
PANEL = FACE.find("Scene/Group[@name='bottom_panel']")
EXPRESSIONS = sorted({n.text for n in PANEL.iter('Expression')} |
                     {n.get('expression') for n in PANEL.iter('Parameter')} |
                     {n.get('value') for n in PANEL.iter('Transform')})
BASE = {'UTC_TIMESTAMP':1790033400000, 'IS_24_HOUR_MODE':False,
        'WEATHER.IS_AVAILABLE':True, 'WEATHER.IS_ERROR':False,
        'WEATHER.CONDITION':14, 'WEATHER.IS_DAY':True, 'WEATHER.CONDITION_NAME':'Partly cloudy',
        'WEATHER.TEMPERATURE':24, 'WEATHER.TEMPERATURE_UNIT':1,
        'WEATHER.DAY_TEMPERATURE_HIGH':28, 'WEATHER.DAY_TEMPERATURE_LOW':16,
        'WEATHER.CHANCE_OF_PRECIPITATION':20, 'STEP_COUNT':0, 'STEP_GOAL':10000, 'HEART_RATE':71}
for i, temp in enumerate([24, 23, 21, 20]):
    BASE.update({f'WEATHER.HOURS.{i}.IS_AVAILABLE':True, f'WEATHER.HOURS.{i}.TEMPERATURE':temp,
                 f'WEATHER.HOURS.{i}.CONDITION':i+1, f'WEATHER.HOURS.{i}.IS_DAY':True})

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
  const value=Function('clamp','min','max','numberFormat','icuText','textLength',`return (${code})`)(
   (v,a,b)=>Math.max(a,Math.min(v,b)),Math.min,Math.max,(_,n)=>Number(n).toLocaleString('en-US'),icu,s=>String(s).length);
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
    visit(PANEL.find(f"ListConfiguration/ListOption[@id='{option}']"))
    texts=[]
    for node in nodes:
        if node.tag=='Font':
            template=node.find('Template')
            if template is None:texts.append(node.text or '')
            else:texts.append(template.text % tuple(values[p.get('expression')] for p in template))
    return nodes, texts


class PanelDataTests(unittest.TestCase):
    def test_missing_and_stale_weather(self):
        missing,stale=evaluate(BASE|{'WEATHER.IS_AVAILABLE':False},BASE|{'WEATHER.IS_ERROR':True})
        for option in ['weather','temperature','detailed_weather','rain']:
            _,texts=visible(option,missing)
            self.assertEqual(texts,['Weather —','Tap to open Weather'])
            _,texts=visible(option,stale)
            self.assertIn('!',texts)
            self.assertTrue(any('24°' in t or '20%' in t for t in texts))

    def test_partial_forecast_does_not_fabricate_or_connect_missing_values(self):
        value,=evaluate(BASE|{'WEATHER.HOURS.1.IS_AVAILABLE':False,'WEATHER.HOURS.1.TEMPERATURE':999})
        for option in ['weather','temperature']:
            nodes,texts=visible(option,value)
            self.assertIn('—',texts)
            self.assertFalse(any('999' in t for t in texts))
            self.assertTrue(any('21°'==t for t in texts))
            if option=='temperature':
                self.assertEqual(len([n for n in nodes if n.tag=='Line' and n.find('Transform') is not None]),1)

    def test_units_extremes_and_flat_temperature_trend(self):
        for unit,temp in [(1,-40),(2,120),(1,0)]:
            data=BASE|{'WEATHER.TEMPERATURE':temp,'WEATHER.TEMPERATURE_UNIT':unit}
            data.update({f'WEATHER.HOURS.{i}.TEMPERATURE':temp for i in range(4)})
            values,=evaluate(data)
            nodes,texts=visible('temperature',values)
            self.assertIn(f'Now {temp}°'+('C' if unit==1 else 'F'),texts)
            self.assertEqual(texts.count(f'{temp}°'),4)
            for n in nodes:
                if n.tag=='Transform':self.assertEqual(values[n.get('value')],39.5)

    def test_forecast_times_midnight_noon_and_dst(self):
        from datetime import datetime, timezone
        for iso,zone,h24,expected in [
            ('2026-09-19T23:30:00','UTC',False,['11 PM','12 AM','1 AM','2 AM']),
            ('2026-09-19T11:30:00','UTC',False,['11 AM','12 PM','1 PM','2 PM']),
            ('2026-09-19T23:30:00','UTC',True,['23','00','01','02']),
            ('2026-03-08T06:30:00','America/New_York',False,['1 AM','3 AM','4 AM','5 AM']),
            ('2026-11-01T05:30:00','America/New_York',False,['1 AM','1 AM','2 AM','3 AM']),
            ('2026-09-19T18:30:00','Asia/Kolkata',True,['00','01','02','03'])]:
            stamp=int(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp()*1000)
            values,=evaluate(BASE|{'UTC_TIMESTAMP':stamp,'zone':zone,'IS_24_HOUR_MODE':h24})
            _,texts=visible('weather',values)
            self.assertEqual([t for t in texts if t in expected],expected)

    def test_health_zero_empty_and_over_goal(self):
        for hr in ['',0,-1,241]:
            values,=evaluate(BASE|{'HEART_RATE':hr})
            self.assertEqual(visible('heart_rate',values)[1],['Heart rate —'])
        values,=evaluate(BASE)
        self.assertIn('0 steps',visible('steps',values)[1])
        for steps in ['',-1]:
            values,=evaluate(BASE|{'STEP_COUNT':steps})
            self.assertEqual(visible('steps',values)[1],['Steps —'])
        values,=evaluate(BASE|{'STEP_COUNT':15000})
        nodes,texts=visible('steps',values)
        self.assertIn('15,000 steps',texts)
        self.assertEqual([values[n.get('value')] for n in nodes if n.tag=='Transform'],[252])

    def test_none_has_no_content_or_action(self):
        values,=evaluate(BASE)
        nodes,texts=visible('none',values)
        self.assertEqual(texts,[])
        self.assertFalse(any(n.tag in ['Launch','PartDraw','PartImage'] for n in nodes))

    def test_every_weather_condition_and_unknown_has_a_symbol(self):
        for code in list(range(16))+[99]:
            for day in [True,False]:
                values,=evaluate(BASE|{'WEATHER.CONDITION':code,'WEATHER.IS_DAY':day})
                nodes,texts=visible('weather',values)
                icon=next(n for n in nodes if n.get('name')=='panel_weather_icon')
                self.assertIsNotNone(icon)
                if code in [0,99]:self.assertIn('—',texts)
                else:self.assertTrue(any(n.tag in ['Ellipse','Line','Arc'] for n in nodes))

if __name__=='__main__':unittest.main()
