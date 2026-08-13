from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
)

from reportlab.lib.styles import getSampleStyleSheet


def generate_pdf(
    trip,
    filename,
):

    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(filename)

    elements = []

    elements.append(
        Paragraph(
            "TravelSync Trip Summary",
            styles["Heading1"],
        )
    )

    elements.append(
        Paragraph(
            f"Destination: {trip['destination']}",
            styles["Heading2"],
        )
    )

    doc.build(elements)