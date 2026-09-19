"""Regression checks for the WFF contracts, geometry, and time boundary cases."""
from pathlib import Path
import math
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

class WatchFaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.face=ET.parse(ROOT/'app/src/main/res/raw/watchface.xml').getroot()

    def test_six_slots_have_complete_renderers(self):
        slots=self.face.findall('.//ComplicationSlot')
        self.assertEqual([s.get('slotId') for s in slots],['1','2','3','4','5','6'])
        for slot in slots:
            self.assertEqual(set(slot.get('supportedTypes').split()),{c.get('type') for c in slot.findall('Complication')})
            self.assertEqual(slot.get('isCustomizable'),'TRUE')
            self.assertIsNotNone(slot.find("Variant[@mode='AMBIENT'][@value='0']"))

    def test_touch_regions_do_not_overlap_and_fit_round_screen(self):
        def contains(slot,x,y):
            x-=float(slot.get('x'));y-=float(slot.get('y'))
            b=next(n for n in slot if n.tag.startswith('Bounding'))
            if b.tag=='BoundingArc':
                dx=x-float(b.get('centerX'));dy=y-float(b.get('centerY'))
                r=math.hypot(dx,dy);angle=math.degrees(math.atan2(dx,-dy))%360
                return abs(r-float(b.get('width'))/2)<=float(b.get('thickness'))/2 and float(b.get('startAngle'))<=angle<=float(b.get('endAngle'))
            w=float(b.get('width'));h=float(b.get('height'))
            if b.tag=='BoundingOval':return ((x-w/2)/(w/2))**2+((y-h/2)/(h/2))**2<=1
            return 0<=x<=w and 0<=y<=h
        slots=self.face.findall('.//ComplicationSlot')
        for y in range(450):
            for x in range(450):
                touched=[s.get('slotId') for s in slots if contains(s,x,y)]
                self.assertLessEqual(len(touched),1,f'Overlapping tap areas at {x},{y}: {touched}')
                if touched:self.assertLessEqual(math.hypot(x-225,y-225),225.6)

    def test_runtime_rectangles_and_rendering_parts_do_not_steal_taps(self):
        slots=self.face.findall('.//ComplicationSlot')
        for i,a in enumerate(slots):
            ax,ay,aw,ah=map(float,(a.get(k) for k in ['x','y','width','height']))
            for b in slots[i+1:]:
                bx,by,bw,bh=map(float,(b.get(k) for k in ['x','y','width','height']))
                self.assertTrue(ax+aw<=bx or bx+bw<=ax or ay+ah<=by or by+bh<=ay,
                                f'Runtime tap rectangles overlap: {a.get("slotId")}, {b.get("slotId")}')
            for part in a.iter():
                if part.tag in ['PartDraw','PartText','PartImage']:
                    self.assertGreaterEqual(float(part.get('x')),0)
                    self.assertGreaterEqual(float(part.get('y')),0)
                    self.assertLessEqual(float(part.get('x'))+float(part.get('width')),aw)
                    self.assertLessEqual(float(part.get('y'))+float(part.get('height')),ah)

    def test_edge_clip_masks_contain_entire_label_rectangles(self):
        # Rendering masks crop the text independently of the slot's tap bounds.
        # Every point of each caption box must fit, not just its baseline.
        for sid in ['4','5']:
            slot=self.face.find(f'.//ComplicationSlot[@slotId="{sid}"]')
            bounds=slot.find('BoundingArc')
            radius=float(bounds.get('width'))/2
            half_thickness=float(bounds.get('thickness'))/2
            self.assertFalse(slot.findall('.//TextCircular'))
            labels=slot.findall('.//PartText')
            self.assertTrue(labels)
            for label in labels:
                x,y,w,h=map(float,(label.get(k) for k in ['x','y','width','height']))
                for row in range(int(h)+1):
                    for col in range(int(w)+1):
                        dx=x+col-float(bounds.get('centerX'));dy=y+row-float(bounds.get('centerY'))
                        r=math.hypot(dx,dy);a=math.degrees(math.atan2(dx,-dy))%360
                        self.assertLessEqual(radius-half_thickness,r)
                        self.assertGreaterEqual(radius+half_thickness,r)
                        self.assertLessEqual(float(bounds.get('startAngle')),a)
                        self.assertGreaterEqual(float(bounds.get('endAngle')),a)

    def test_all_weather_codes_and_future_hours_have_fallbacks(self):
        for font in self.face.findall('./BitmapFonts/BitmapFont'):
            self.assertEqual({n.get('name') for n in font},set(map(str,range(16))))
        for offset in (2,4,6,8):
            g=self.face.find(f".//Group[@name='forecast_{offset}']")
            e=g.find('./Condition/Expressions/Expression').text
            self.assertIn(f'WEATHER.HOURS.{offset}.IS_AVAILABLE',e)
            self.assertIsNotNone(g.find('./Condition/Default'))

    def test_forecast_labels_cover_midnight_noon_and_rollover(self):
        # Read and evaluate the actual generated arithmetic, not a second formula.
        for offset in (2,4,6,8):
            g=self.face.find(f".//Group[@name='forecast_{offset}']")
            # First Condition is weather fallback; select the 12-hour branch explicitly.
            c=g.findall('Condition')[1]
            expr=c.find('./Default/PartText/Text/Font/Template/Parameter').get('expression')
            for hour in range(24):
                actual=eval(expr.replace('[HOUR_0_23]',str(hour)),{'__builtins__':{}})
                expected=(hour+offset)%24%12 or 12
                self.assertEqual(actual,expected)

    def test_only_time_and_date_remain_in_ambient(self):
        scene=self.face.find('Scene')
        self.assertEqual(scene.get('backgroundColor'),'#FF000000')
        for n in scene:
            if n.get('name')=='ambient_time':
                self.assertEqual(n.get('alpha'),'0')
                self.assertIsNotNone(n.find("Variant[@mode='AMBIENT'][@value='255']"))
                self.assertFalse(any(t.get('format')=='ss' for t in n.iter('TimeText')))
            else:self.assertIsNotNone(n.find("Variant[@mode='AMBIENT'][@value='0']"),n.tag)

    def test_unique_expression_names_and_named_slots(self):
        names=[n.get('name') for n in self.face.iter('Expression')]
        self.assertEqual(len(names),len(set(names)))
        strings={s.get('name') for s in ET.parse(ROOT/'app/src/main/res/values/strings.xml').getroot()}
        for node in self.face.iter():
            if node.get('displayName'):
                self.assertIn(node.get('displayName'),strings)
                self.assertFalse(node.get('displayName').startswith('@'))

if __name__=='__main__':unittest.main()
