"""Riktiga Streamlit-flödestester. Körs i GitHub Actions och med requirements-dev."""
import importlib.util
from pathlib import Path
import unittest

HAS_UI=all(importlib.util.find_spec(x) is not None for x in ("streamlit","plotly"))


@unittest.skipUnless(HAS_UI,"Streamlit/Plotly är inte installerade i denna miljö")
class StreamlitTests(unittest.TestCase):
    def app(self, demo=False):
        from streamlit.testing.v1 import AppTest
        from road2zero.seeds import demonstration
        at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"streamlit_app.py"),default_timeout=60)
        if demo:
            at.session_state["scenario"]=demonstration().model_dump()
            at.session_state["generation"]="test-demo"
        return at.run(timeout=60)

    def test_initial_smt_six_tabs_and_no_exceptions(self):
        at=self.app()
        self.assertEqual(len(at.exception),0,str(at.exception))
        self.assertEqual(len(at.tabs),6)
        self.assertEqual(at.session_state["scenario"]["project"]["homes"],4000)

    def test_all_input_modules_render(self):
        at=self.app(demo=True)
        modules=list(at.selectbox(key="input-module").options)
        for module in modules:
            at.selectbox(key="input-module").set_value(module).run(timeout=60)
            self.assertEqual(len(at.exception),0,f"{module}: {at.exception}")

    def test_edit_total_bta_changes_model(self):
        at=self.app(demo=True)
        field=next(x for x in at.number_input if x.label.startswith("Total nybyggd BTA"))
        field.set_value(2000.)
        next(x for x in at.button if x.label=="Spara projekt").click().run(timeout=60)
        self.assertEqual(len(at.exception),0,str(at.exception))
        self.assertEqual(at.session_state["scenario"]["project"]["total_bta_override"],2000)


if __name__=="__main__":unittest.main()
