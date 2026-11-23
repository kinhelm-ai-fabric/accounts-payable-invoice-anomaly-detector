import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

KINDO_API_URL = "https://api.kindo.ai/v1/chat/completions"


def analyze_invoice(invoice, vendor, historical_invoices):
    """Send invoice data to the Kindo anomaly-detection agent and return findings.

    Returns a list of anomaly dicts: [{anomaly_type, severity, description, confidence, recommendation}]
    Falls back to rule-based detection when the Kindo agent is unavailable.
    """
    agent_id = os.environ.get("KINDO_INVOICE_ANOMALY_AGENT_ID", "")
    api_key = os.environ.get("KINDO_API_KEY", "")

    # Build history summary
    hist_summary = []
    for h in historical_invoices[:20]:
        hist_summary.append({
            "invoice_number": h.invoice_number,
            "amount": h.amount,
            "invoice_date": h.invoice_date.isoformat() if h.invoice_date else None,
            "status": h.status,
        })

    request_payload = {
        "invoice": {
            "invoice_number": invoice.invoice_number,
            "amount": invoice.amount,
            "currency": invoice.currency,
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "description": invoice.description or "",
            "status": invoice.status,
        },
        "vendor": {
            "name": vendor.name,
            "code": vendor.code,
        },
        "historical_invoices": hist_summary,
    }

    if agent_id and api_key:
        try:
            return _call_kindo_agent(agent_id, api_key, request_payload)
        except Exception as exc:
            logger.warning("Kindo agent call failed, falling back to rules: %s", exc)

    return _rule_based_detection(invoice, historical_invoices)


def _call_kindo_agent(agent_id, api_key, request_payload):
    """Call the Kindo anomaly detection agent."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": agent_id,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(request_payload),
            }
        ],
    }

    resp = requests.post(KINDO_API_URL, json=body, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # Parse the agent JSON response
    result = json.loads(content)
    anomalies = result.get("anomalies", [])

    validated = []
    for a in anomalies:
        validated.append({
            "anomaly_type": a.get("anomaly_type", "unknown"),
            "severity": a.get("severity", "medium"),
            "description": a.get("description", ""),
            "confidence": a.get("confidence", 0.5),
            "recommendation": a.get("recommendation", ""),
        })
    return validated


def _rule_based_detection(invoice, historical_invoices):
    """Simple rule-based anomaly detection fallback."""
    anomalies = []

    if not historical_invoices:
        return anomalies

    amounts = [h.amount for h in historical_invoices if h.amount]
    if amounts:
        avg = sum(amounts) / len(amounts)
        std_dev = (sum((a - avg) ** 2 for a in amounts) / len(amounts)) ** 0.5

        if std_dev > 0 and abs(invoice.amount - avg) > 2 * std_dev:
            anomalies.append({
                "anomaly_type": "amount_outlier",
                "severity": "high" if abs(invoice.amount - avg) > 3 * std_dev else "medium",
                "description": f"Invoice amount ${invoice.amount:,.2f} deviates significantly from vendor average of ${avg:,.2f} (std dev: ${std_dev:,.2f}).",
                "confidence": min(0.95, 0.5 + abs(invoice.amount - avg) / (3 * std_dev) * 0.45) if std_dev > 0 else 0.5,
                "recommendation": "Review this invoice amount against the purchase order and contract terms.",
            })

        if invoice.amount > avg * 5 and invoice.amount > 10000:
            anomalies.append({
                "anomaly_type": "unusually_large_amount",
                "severity": "critical",
                "description": f"Invoice amount ${invoice.amount:,.2f} is more than 5x the vendor average of ${avg:,.2f}.",
                "confidence": 0.85,
                "recommendation": "Requires manager approval. Verify with vendor and check for duplicate billing.",
            })

    if invoice.amount < 0:
        anomalies.append({
            "anomaly_type": "negative_amount",
            "severity": "high",
            "description": f"Negative invoice amount: ${invoice.amount:,.2f}.",
            "confidence": 0.95,
            "recommendation": "Verify if this is a credit memo or data entry error.",
        })

    if invoice.due_date and invoice.invoice_date:
        days_to_pay = (invoice.due_date - invoice.invoice_date).days
        if days_to_pay < 0:
            anomalies.append({
                "anomaly_type": "past_due_at_creation",
                "severity": "medium",
                "description": f"Due date ({invoice.due_date}) is before invoice date ({invoice.invoice_date}).",
                "confidence": 0.90,
                "recommendation": "Verify dates -- the due date appears to be before the invoice date.",
            })

    # Check for duplicate amounts on same date
    for h in historical_invoices:
        if (h.amount == invoice.amount and
                h.invoice_date == invoice.invoice_date and
                h.invoice_number != invoice.invoice_number):
            anomalies.append({
                "anomaly_type": "potential_duplicate",
                "severity": "high",
                "description": f"Possible duplicate: same amount (${invoice.amount:,.2f}) and date as invoice {h.invoice_number}.",
                "confidence": 0.75,
                "recommendation": "Compare line items to confirm this is not a duplicate payment.",
            })
            break

    return anomalies
