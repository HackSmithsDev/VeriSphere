from app.services.portfolio.resume_template import render_resume_document


def build_resume_html(portfolio: dict) -> str:
    return render_resume_document(portfolio)
