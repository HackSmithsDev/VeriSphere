from html import escape
from typing import Any


def render_resume_document(portfolio: dict[str, Any]) -> str:
    student = portfolio["student"]
    milestones = portfolio["academic_milestones"]
    activities = portfolio["activities"]

    milestone_items = "".join(
        "<li>"
        f"<strong>{escape(item['title'])}</strong>"
        f"<span>{escape(item['subject'])} | Semester {item['semester']}</span>"
        "</li>"
        for item in milestones
    )
    activity_items_list = []
    for item in activities:
        issuer = f" | {escape(item['issuer'])}" if item.get("issuer") else ""
        activity_items_list.append(
            "<li>"
            f"<strong>{escape(item['title'])}</strong>"
            f"<span>{escape(item['category'].replace('_', ' ').title())}"
            f"{issuer}</span>"
            f"<p>{escape(item['description'])}</p>"
            "</li>"
        )
    activity_items = "".join(activity_items_list)
    course = escape(student["course"] or "Course not available")
    name = escape(student["name"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name} - VeriSphere Portfolio</title>
  <style>
    :root {{ color-scheme: light; font-family: Arial, sans-serif; color: #172033; }}
    body {{ max-width: 780px; margin: 48px auto; padding: 0 28px; line-height: 1.55; }}
    header {{ border-bottom: 2px solid #183153; padding-bottom: 20px; }}
    h1 {{ margin: 0; font-size: 2rem; }}
    h2 {{ margin-top: 32px; color: #183153; font-size: 1.15rem; }}
    ul {{ list-style: none; margin: 0; padding: 0; }}
    li {{ border-bottom: 1px solid #d9e0e9; padding: 12px 0; }}
    li strong, li span {{ display: block; }}
    li span, li p, .meta {{ color: #536176; }}
    li p {{ margin: 5px 0 0; }}
    @media print {{ body {{ margin: 0 auto; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{name}</h1>
    <div class="meta">{course} | Semester {student["semester"]}</div>
  </header>
  <main>
    <section>
      <h2>Verified academic milestones</h2>
      <ul>{milestone_items or "<li>No verified academic milestones yet.</li>"}</ul>
    </section>
    <section>
      <h2>Verified activities and achievements</h2>
      <ul>{activity_items or "<li>No verified activities yet.</li>"}</ul>
    </section>
  </main>
</body>
</html>
"""
