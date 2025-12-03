import io
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from . import register

def generate_pdf(title, content):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setLineWidth(.3)
    p.setFont('Helvetica', 12)
    
    p.drawString(100, 750, title)
    p.line(100, 747, 500, 747)
    
    y = 700
    for line in content:
        p.drawString(100, y, line)
        y -= 20
        
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

@register("clearance_pack")
def handle(payload: dict, *, job_id: int, trace_id: str):
    required = payload.get("required_uom")
    invoice = payload.get("invoice_uom")
    
    if not required or not invoice:
        from app.jobs import cli
        raise cli.NonRetriableError("missing uom fields")

    # Generate Invoice PDF
    invoice_content = [
        f"Trace ID: {trace_id}",
        f"Invoice UOM: {invoice}",
        "Item: Widget A",
        "Price: $10.00"
    ]
    invoice_pdf = generate_pdf("COMMERCIAL INVOICE", invoice_content)
    invoice_media_id = f"doc:ci:{uuid.uuid4()}"
    # In a real app, we would save invoice_pdf to blob storage here
    
    # Generate Packing List PDF
    pl_content = [
        f"Trace ID: {trace_id}",
        f"Required UOM: {required}",
        "Item: Widget A",
        "Quantity: 100"
    ]
    pl_pdf = generate_pdf("PACKING LIST", pl_content)
    pl_media_id = f"doc:pl:{uuid.uuid4()}"
    # Save pl_pdf to blob storage
    
    return {
        "artifacts": [
            {"type": "commercial_invoice", "media_id": invoice_media_id, "size": len(invoice_pdf)},
            {"type": "packing_list", "media_id": pl_media_id, "size": len(pl_pdf)},
        ],
        "uom_check": {"required": required, "invoice": invoice, "valid": (required == invoice)},
        "trace_id": trace_id,
    }
