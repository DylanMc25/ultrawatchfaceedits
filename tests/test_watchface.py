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

    def test_seven_slots_have_complete_renderers(self):
        slots=self.face.findall('.//ComplicationSlot')
        self.assertEqual([s.get('slotId') for s in slots],['1','2','3','4','5','6','7'])
        for slot in slots:
            self.assertEqual(set(slot.get('supportedTypes').split()),{c.get('type') for c in slot.findall('Complication')})
            self.assertEqual(slot.get('isCustomizable'),'TRUE')
            self.assertIsNotNone(slot.find("Variant[@mode='AMBIENT'][@value='0']"))

    def test_visible_touch_regions_do_not_overlap(self):
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
        self.assertEqual(self.face.get('clipShape'),'CIRCLE')
        slots=self.face.findall('.//ComplicationSlot')
        for y in range(450):
            for x in range(450):
                if math.hypot(x-225,y-225)>225:continue
                touched=[s.get('slotId') for s in slots if contains(s,x,y)]
                self.assertLessEqual(len(touched),1,f'Overlapping tap areas at {x},{y}: {touched}')

    def test_slot_bounds_and_rendering_parts_do_not_steal_taps(self):
        slots=self.face.findall('.//ComplicationSlot')
        for i,a in enumerate(slots):
            ax,ay,aw,ah=map(float,(a.get(k) for k in ['x','y','width','height']))
            for b in slots[i+1:]:
                bx,by,bw,bh=map(float,(b.get(k) for k in ['x','y','width','height']))
                if a.find('BoundingOval') is not None and b.find('BoundingOval') is not None:
                    # Round regions can pack diagonally. Their unused rectangular
                    # corners overlap, but the selectable circles must not.
                    self.assertEqual(aw,ah);self.assertEqual(bw,bh)
                    self.assertGreaterEqual(math.hypot(ax+aw/2-bx-bw/2,ay+ah/2-by-bh/2),aw/2+bw/2+1)
                else:
                    self.assertTrue(ax+aw<=bx or bx+bw<=ax or ay+ah<=by or by+bh<=ay,
                                    f'Non-circular tap rectangles overlap: {a.get("slotId")}, {b.get("slotId")}')
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
            bounds=slot.find('BoundingRoundBox')
            self.assertIsNotNone(bounds)
            width,height=map(float,(bounds.get(k) for k in ['width','height']))
            radius=float(bounds.get('cornerRadius'))
            self.assertFalse(slot.findall('.//TextCircular'))
            labels=slot.findall('.//PartText')
            self.assertTrue(labels)
            for label in labels:
                x,y,w,h=map(float,(label.get(k) for k in ['x','y','width','height']))
                for row in range(int(h)+1):
                    for col in range(int(w)+1):
                        angle=math.radians(float(label.get('angle','0')))
                        dx,dy=col-w/2,row-h/2
                        px=x+w/2+dx*math.cos(angle)-dy*math.sin(angle)
                        py=y+h/2+dx*math.sin(angle)+dy*math.cos(angle)
                        self.assertTrue(0<=px<=width and 0<=py<=height)
                        dx=max(radius-px,0,px-(width-radius))
                        dy=max(radius-py,0,py-(height-radius))
                        self.assertLessEqual(math.hypot(dx,dy),radius)
                        self.assertLess(math.hypot(px+float(slot.get('x'))-225,
                                                   py+float(slot.get('y'))-225),225)

    def test_edge_gauges_leave_space_above_rotated_captions(self):
        for sid in ['4','5']:
            slot=self.face.find(f'.//ComplicationSlot[@slotId="{sid}"]')
            lowest_drawn_pixel=0
            for line in slot.findall('.//Line'):
                lowest_drawn_pixel=max(lowest_drawn_pixel,
                    max(float(line.get('startY')),float(line.get('endY')))+float(line.find('Stroke').get('thickness'))/2)
            for arc in slot.findall('.//Arc'):
                lowest_drawn_pixel=max(lowest_drawn_pixel,float(arc.get('centerY'))-
                    float(arc.get('height'))/2*math.cos(math.radians(float(arc.get('endAngle'))))+
                    float(arc.find('Stroke').get('thickness'))/2)
            for label in slot.findall('.//PartText'):
                y,w,h=map(float,(label.get(k) for k in ['y','width','height']))
                a=math.radians(float(label.get('angle')))
                highest_text_pixel=y+h/2-abs(math.sin(a))*w/2-abs(math.cos(a))*h/2
                self.assertGreaterEqual(highest_text_pixel-lowest_drawn_pixel,2)

    def test_weather_is_one_native_editable_slot(self):
        slot=self.face.find(".//ComplicationSlot[@slotId='7']")
        self.assertEqual(slot.get('name'),'weather')
        self.assertEqual(slot.get('displayName'),'slot_weather')
        self.assertIn('SHORT_TEXT',slot.get('supportedTypes').split())
        self.assertTrue({'LONG_TEXT','SMALL_IMAGE','PHOTO_IMAGE','RANGED_VALUE','GOAL_PROGRESS','WEIGHTED_ELEMENTS'} <= set(slot.get('supportedTypes').split()))
        self.assertEqual(slot.find('DefaultProviderPolicy').get('defaultSystemProvider'),'EMPTY')
        self.assertFalse(self.face.findall('.//Launch'), 'Provider must own the tap action')
        xml=ET.tostring(self.face,encoding='unicode')
        self.assertNotIn('[WEATHER.',xml)
        self.assertNotIn('com.samsung.android.watch.weather',xml)
        self.assertEqual(tuple(float(slot.get(k)) for k in ['x','y','width','height']),(94,339,262,60))

    def test_minutes_and_seconds_have_separate_space(self):
        g=self.face.find(".//Group[@name='interactive_time']")
        clocks=g.findall('DigitalClock')
        minutes=clocks[0].find("TimeText[@format='mm']")
        seconds=clocks[1]
        minute_right=float(clocks[0].get('x'))+float(minutes.get('x'))+float(minutes.get('width'))
        self.assertGreaterEqual(float(seconds.get('x'))-minute_right,2)
        self.assertGreaterEqual(float(seconds.find('TimeText/Font').get('size')),32)

    def test_clock_and_circles_fit_the_available_space(self):
        slots=self.face.findall('.//ComplicationSlot')
        for sid in ['1','2','3']:
            slot=self.face.find(f".//ComplicationSlot[@slotId='{sid}']")
            x,y,w,h=map(float,(slot.get(k) for k in ['x','y','width','height']))
            self.assertGreaterEqual(w,100)
            self.assertLessEqual(math.hypot(x+w/2-225,y+h/2-225)+w/2,225)
        g=self.face.find(".//Group[@name='interactive_time']")
        for clock in g.findall('DigitalClock'):
            for t in clock.findall('TimeText'):
                x=float(clock.get('x'))+float(t.get('x'));y=float(clock.get('y'))+float(t.get('y'))
                w=float(t.get('width'));h=float(t.get('height'))
                if t.get('format') in ['hh','mm']:
                    self.assertGreaterEqual(float(t.find('Font').get('size')),142)
                for slot in slots[:3]:
                    sx,sy,sw,sh=map(float,(slot.get(k) for k in ['x','y','width','height']))
                    self.assertTrue(x+w<=sx or sx+sw<=x or y+h<=sy or sy+sh<=y,
                                    f'Clock overlaps slot {slot.get("slotId")}')
        for clock in self.face.findall('.//DigitalClock'):
            hour=clock.find("TimeText[@format='hh']")
            if hour is not None:self.assertEqual(hour.get('hourFormat'),'SYNC_TO_DEVICE')

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
