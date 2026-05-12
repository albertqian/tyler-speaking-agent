from __future__ import annotations

import html
import smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from .models import Opportunity


def build_html_email(opportunities: list[Opportunity]) -> str:
    now = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%B %d, %Y")

    if not opportunities:
        return f"""
<html>
  <body>
    <p>Hi Tyler,</p>
    <p>No strong paid speaking opportunities were found this week based on the current filters.</p>
    <p>This does not mean there are no opportunities. It means the agent did not find listings that cleared the relevance and pay-confidence threshold.</p>
    <p><em>Generated on {html.escape(now)}.</em></p>
  </body>
</html>
"""

    rows = []
    for opp in opportunities:
        warnings = "; ".join(str(w) for w in opp.warnings) if opp.warnings else ""
        notes = opp.relevance_notes
        if warnings:
            notes = f"{notes} Caveats: {warnings}".strip()

        rows.append(
            f"""
<tr>
  <td><a href="{html.escape(opp.url)}">{html.escape(opp.opportunity)}</a></td>
  <td>{html.escape(opp.opportunity_description)}<br><small>{html.escape(notes)}</small></td>
  <td>{html.escape(opp.location)}</td>
  <td>{html.escape(opp.date_of_opportunity)}</td>
  <td>{html.escape(opp.pay)}<br><small>{html.escape(opp.pay_certainty)}</small></td>
  <td>{opp.fit_score}</td>
</tr>
"""
        )

    return f"""
<html>
  <body>
    <p>Hi Tyler,</p>

    <p>Here are this week's speaking opportunities that appear relevant to Women Making Waves, women’s leadership, entrepreneurship, mentorship, and community-building.</p>

    <p>I prioritized paid or likely paid opportunities and filtered out clearly unpaid exposure-only listings where possible.</p>

    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px;">
      <thead>
        <tr>
          <th>Opportunity</th>
          <th>Opportunity description</th>
          <th>Location</th>
          <th>Date of opportunity</th>
          <th>How much opportunity pays</th>
          <th>Fit score</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>

    <p><em>Generated on {html.escape(now)}.</em></p>
  </body>
</html>
"""


def build_text_email(opportunities: list[Opportunity]) -> str:
    if not opportunities:
        return "No strong paid speaking opportunities were found this week based on the current filters."

    lines = ["Weekly speaking opportunities:\n"]
    for i, opp in enumerate(opportunities, 1):
        lines.append(
            f"""{i}. {opp.opportunity}
Description: {opp.opportunity_description}
Location: {opp.location}
Date: {opp.date_of_opportunity}
Pay: {opp.pay} ({opp.pay_certainty})
Fit score: {opp.fit_score}
Link: {opp.url}
Notes: {opp.relevance_notes}
"""
        )
    return "\n".join(lines)


# Gmail App Password flow: the app password authenticates this SMTP login.
# This is not the user's normal Gmail password.
def send_email(
    *,
    gmail_user: str,
    gmail_app_password: str,  # Google/Gmail App Password
    to_email: str,
    from_name: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{gmail_user}>"
    message["To"] = to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(gmail_user, gmail_app_password)
        smtp.send_message(message)
