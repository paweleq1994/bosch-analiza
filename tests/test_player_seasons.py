import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("seasons",Path(__file__).resolve().parents[1]/"src/sync_player_seasons.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Players(unittest.TestCase):
    def test_source_team_filter_and_skip_totals(self):
        data={"statistics":{"123":{"120":{"name":"Hala 2022","team":"<a href='https://podlaskaliga.pl/druzyna/bosch-service-tech-car/'>Bosch</a>","appearances":"13","goals":3,"assists":4},"-1":{"team":"Bosch","appearances":13},"125":{"team":"<a href='https://podlaskaliga.pl/druzyna/other/'>Other</a>","appearances":"14","goals":9}}}}
        self.assertEqual(list(mod.parse_player(data)),["120"])
        self.assertEqual(mod.parse_player(data)["120"]["assists"],4)
    def test_failed_source_keeps_existing_history(self):
        prior={"1960":{"120":{"apps":13}}}
        out,warnings=mod.refresh(["1960"],prior,lambda _: (_ for _ in ()).throw(RuntimeError("offline")))
        self.assertEqual(out,prior)
        self.assertTrue(warnings)
if __name__=="__main__":unittest.main()
