"""Startfil för äldre länkar: kör Road2Zero-Plan.

Repot har tre appar med var sin huvudfil:
  plan/streamlit_app.py           Road2Zero-Plan          en plan i detalj
  cityscenario/streamlit_app.py   Road2Zero-CityScenario  tre scenarier mot varandra
  op/streamlit_app.py             Road2Zero-OP            hela staden per DeSO
Peka Streamlit Community Cloud på den app du vill publicera. Den här filen finns kvar så att en befintlig publicering med
huvudfilen streamlit_app.py fortsätter att fungera och visar Road2Zero-Plan.
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "plan" / "streamlit_app.py"), run_name="__main__")
