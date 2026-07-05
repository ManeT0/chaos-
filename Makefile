run:
	uvicorn backend.main:app --reload

test:
	pytest -q

dashboard:
	streamlit run frontend/app.py
