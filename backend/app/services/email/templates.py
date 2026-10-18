from html import escape


def review_notification(
    student_name: str,
    item_title: str,
    decision: str,
    feedback: str | None,
) -> tuple[str, str]:
    outcome = "verified" if decision == "verified" else "returned for revision"
    safe_title = item_title.replace("\r", " ").replace("\n", " ")
    subject = f"VeriSphere update: {safe_title} was {outcome}"
    body = (
        f"Hello {student_name},\n\n"
        f"Your submission “{item_title}” was {outcome} by your faculty reviewer."
    )
    if feedback:
        body += f"\n\nReviewer feedback:\n{feedback}"
    body += "\n\nSign in to VeriSphere to view your updated progress."
    return subject, body


def review_notification_html(
    student_name: str,
    item_title: str,
    decision: str,
    feedback: str | None,
) -> str:
    outcome = "verified" if decision == "verified" else "returned for revision"
    feedback_html = (
        f"<p><strong>Reviewer feedback</strong><br>{escape(feedback)}</p>"
        if feedback
        else ""
    )
    return (
        "<!doctype html><html><body>"
        f"<p>Hello {escape(student_name)},</p>"
        f"<p>Your submission <strong>{escape(item_title)}</strong> was "
        f"{outcome} by your faculty reviewer.</p>"
        f"{feedback_html}"
        "<p>Sign in to VeriSphere to view your updated progress.</p>"
        "</body></html>"
    )


def student_invitation(
    student_name: str,
    invitation_url: str,
    expires_in_hours: int,
) -> tuple[str, str]:
    subject = "Your VeriSphere student account invitation"
    body = (
        f"Hello {student_name},\n\n"
        "An administrator invited you to join VeriSphere. Set your password "
        f"within {expires_in_hours} hours using this one-time link:\n"
        f"{invitation_url}\n\n"
        "If you were not expecting this invitation, you can ignore this email."
    )
    return subject, body


def student_invitation_html(
    student_name: str,
    invitation_url: str,
    expires_in_hours: int,
) -> str:
    return (
        "<!doctype html><html><body>"
        f"<p>Hello {escape(student_name)},</p>"
        "<p>An administrator invited you to join VeriSphere.</p>"
        f'<p><a href="{escape(invitation_url, quote=True)}">'
        "Set your password</a>. This one-time link expires in "
        f"{expires_in_hours} hours.</p>"
        "<p>If you were not expecting this invitation, you can ignore this email.</p>"
        "</body></html>"
    )
