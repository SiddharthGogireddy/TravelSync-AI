from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)

from reportlab.lib.styles import (
    getSampleStyleSheet,
)


def generate_trip_pdf(
    trip,
    filename,
):
    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "TravelSync AI",
            styles["Title"],
        )
    )

    elements.append(
        Spacer(1, 12)
    )

    elements.append(
        Paragraph(
            f"Destination: "
            f"{trip['dashboard']['destination']}",
            styles["Normal"],
        )
    )

    elements.append(
        Paragraph(
            f"Days: "
            f"{trip['dashboard']['days']}",
            styles["Normal"],
        )
    )

    elements.append(
        Paragraph(
            f"Travel mode: "
            f"{trip['dashboard']['travel_mode']}",
            styles["Normal"],
        )
    )

    doc = SimpleDocTemplate(
        filename
    )

    doc.build(elements)

    return filename