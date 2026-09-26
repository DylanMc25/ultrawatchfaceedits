"""Exercise bundle preparation without Gradle, network access or real project writes."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_push_bundle", ROOT / "tools/prepare_push_bundle.py")
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


def fixture_xml():
    slots = []
    for slot_id in range(1, 8):
        slots.append(f'''<ComplicationSlot slotId="{slot_id}" name="slot_{slot_id}"
            x="{slot_id * 10}" y="310" width="262" height="94"
            isCustomizable="TRUE" supportedTypes="LONG_TEXT SMALL_IMAGE EMPTY">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <BoundingBox x="0" y="0" width="262" height="94" />
            <DefaultProviderPolicy primaryProvider="original.provider/Slot{slot_id}"
                primaryProviderType="LONG_TEXT" defaultSystemProvider="EMPTY" defaultSystemProviderType="EMPTY" />
            <Complication type="LONG_TEXT"><PartText name="long_text" /></Complication>
            <Complication type="SMALL_IMAGE">
                <PartImage x="12" y="6" width="238" height="48">
                    <Image resource="[COMPLICATION.SMALL_IMAGE]" />
                </PartImage>
            </Complication>
            <Complication type="EMPTY"><PartText name="empty_{slot_id}" /></Complication>
        </ComplicationSlot>''')
    return '<WatchFace><Scene><PartText name="clock" />' + "\n".join(slots) + '</Scene></WatchFace>'


class PushBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "app/src/main/res"
        (self.source / "raw").mkdir(parents=True)
        (self.source / "drawable").mkdir()
        (self.source / "values").mkdir()
        self.xml_file = self.source / "raw/watchface.xml"
        self.xml_file.write_text(fixture_xml())
        (self.source / "drawable/preview.png").write_bytes(b"unchanged image bytes")
        (self.source / "values/strings.xml").write_text(
            '<resources><string name="app_name">Ultra Info Board</string>'
            '<string name="slot_rectangle">Bottom rectangle</string></resources>'
        )
        root_patch = patch.object(PREPARE, "ROOT", self.root)
        network_patch = patch.object(
            PREPARE.urllib.request, "urlretrieve", side_effect=AssertionError("Tests must not download")
        )
        root_patch.start()
        network_patch.start()
        self.addCleanup(root_patch.stop)
        self.addCleanup(network_patch.stop)

    def snapshot(self, path):
        return {file.relative_to(path): file.read_bytes() for file in path.rglob("*") if file.is_file()}

    def test_only_bottom_provider_image_and_face_label_change(self):
        original_files = self.snapshot(self.source)
        destination = PREPARE.prepare_resources()
        generated_files = self.snapshot(destination)
        self.assertEqual(self.snapshot(self.source), original_files, "Source resources must remain untouched")
        self.assertEqual(set(generated_files), set(original_files))
        self.assertEqual(
            {name for name in generated_files if generated_files[name] != original_files[name]},
            {Path("raw/watchface.xml"), Path("values/strings.xml")},
        )
        original_strings = ET.fromstring(original_files[Path("values/strings.xml")])
        generated_strings = ET.fromstring(generated_files[Path("values/strings.xml")])
        app_name = generated_strings.find("string[@name='app_name']")
        self.assertEqual(app_name.text, "Ultra Forecast")
        app_name.text = original_strings.find("string[@name='app_name']").text
        self.assertEqual(ET.tostring(generated_strings), ET.tostring(original_strings))

        original = ET.fromstring(original_files[Path("raw/watchface.xml")])
        generated = ET.fromstring(generated_files[Path("raw/watchface.xml")])
        old_slots = original.findall(".//ComplicationSlot")
        new_slots = generated.findall(".//ComplicationSlot")
        self.assertEqual([slot.get("slotId") for slot in new_slots], [str(i) for i in range(1, 8)])
        self.assertEqual(new_slots[6].get("supportedTypes"), "SMALL_IMAGE EMPTY")
        self.assertIsNone(new_slots[6].find("Complication[@type='LONG_TEXT']"))
        new_slots[6].set("supportedTypes", old_slots[6].get("supportedTypes"))
        self.assertEqual([slot.attrib for slot in new_slots], [slot.attrib for slot in old_slots])
        for old_slot, new_slot in zip(old_slots[:6], new_slots[:6]):
            self.assertEqual(ET.tostring(new_slot), ET.tostring(old_slot))

        policy = new_slots[6].find("DefaultProviderPolicy")
        self.assertEqual(policy.attrib, {
            "primaryProvider": "com.example.ultrainfoboard.bridge/com.example.ultrainfoboard.bridge.SamsungForecastService",
            "primaryProviderType": "SMALL_IMAGE",
            "defaultSystemProvider": "EMPTY",
            "defaultSystemProviderType": "EMPTY",
        })
        image = new_slots[6].find("Complication[@type='SMALL_IMAGE']/PartImage")
        self.assertEqual(image.attrib, {"x": "0", "y": "0", "width": "262", "height": "94"})
        # Reverting intended edits must recover the original document.
        old_slots[6].remove(old_slots[6].find("Complication[@type='LONG_TEXT']"))
        policy.attrib.clear()
        policy.attrib.update(old_slots[6].find("DefaultProviderPolicy").attrib)
        image.attrib.clear()
        image.attrib.update(old_slots[6].find("Complication[@type='SMALL_IMAGE']/PartImage").attrib)
        # Whitespace around the removed renderer is not significant XML content.
        for root in [original, generated]:
            for node in root.iter():
                if node.text and not node.text.strip(): node.text = None
                if node.tail and not node.tail.strip(): node.tail = None
        self.assertEqual(ET.tostring(generated), ET.tostring(original))

    def test_repreparation_removes_stale_generated_assets(self):
        destination = PREPARE.prepare_resources()
        (destination / "raw/stale.xml").write_text("obsolete")
        first_result = (destination / "raw/watchface.xml").read_bytes()
        PREPARE.prepare_resources()
        self.assertFalse((destination / "raw/stale.xml").exists())
        self.assertEqual((destination / "raw/watchface.xml").read_bytes(), first_result)

    def test_ambiguous_or_uneditable_rectangle_fails_without_source_mutation(self):
        for change in ("missing", "duplicate", "locked", "missing_image_type"):
            with self.subTest(change=change):
                document = ET.fromstring(fixture_xml())
                scene = document.find("Scene")
                rectangle = scene.find("ComplicationSlot[@slotId='7']")
                if change == "missing":
                    scene.remove(rectangle)
                elif change == "duplicate":
                    scene.append(ET.fromstring(ET.tostring(rectangle)))
                elif change == "locked":
                    rectangle.set("isCustomizable", "FALSE")
                else:
                    rectangle.set("supportedTypes", "EMPTY")
                self.xml_file.write_bytes(ET.tostring(document))
                before = self.snapshot(self.source)
                with self.assertRaises(RuntimeError):
                    PREPARE.prepare_resources()
                self.assertEqual(self.snapshot(self.source), before)

    def test_corrupted_validator_override_is_rejected(self):
        jar = self.root / "official-looking.jar"
        jar.write_bytes(b"changed validator")
        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            PREPARE.get_validator(str(jar))

    def test_corrupted_cached_validator_is_rejected_without_download(self):
        cache = self.root / ".cache"
        cache.mkdir()
        jar = cache / f"validator-push-cli-{PREPARE.VALIDATOR_VERSION}.jar"
        jar.write_bytes(b"changed cached validator")
        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            PREPARE.get_validator(None)


if __name__ == "__main__":
    unittest.main()
