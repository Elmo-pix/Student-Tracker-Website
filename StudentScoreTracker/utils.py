import pandas as pd
import io
import csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def generate_csv(data):
    """Generate CSV file from data"""
    if isinstance(data, pd.DataFrame):
        output = io.StringIO()
        data.to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
        output.seek(0)
        return io.BytesIO(output.getvalue().encode('utf-8'))
    elif isinstance(data, dict):
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
        
        # Write header row
        writer.writerow(['Report Data'])
        
        # Write each section
        for key, value in data.items():
            writer.writerow([])
            writer.writerow([key])
            
            if isinstance(value, dict):
                # Handle nested dictionaries
                for sub_key, sub_value in value.items():
                    writer.writerow([sub_key])
                    if isinstance(sub_value, list):
                        for item in sub_value:
                            writer.writerow([item])
                    else:
                        writer.writerow([sub_value])
            else:
                writer.writerow([value])
        
        output.seek(0)
        return io.BytesIO(output.getvalue().encode('utf-8'))
    else:
        raise ValueError("Unsupported data type for CSV generation")

def generate_pdf(title, data):
    """Generate PDF report from data"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Add title
    styles = getSampleStyleSheet()
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Paragraph(' ', styles['Normal']))  # Add some space
    
    # Convert data to table format
    if isinstance(data, pd.DataFrame):
        # Convert DataFrame to list of lists
        table_data = [data.columns.tolist()] + data.values.tolist()
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
    elif isinstance(data, dict):
        for key, value in data.items():
            elements.append(Paragraph(key, styles['Heading2']))
            
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    elements.append(Paragraph(f"{sub_key}:", styles['Heading3']))
                    if isinstance(sub_value, list):
                        for item in sub_value:
                            elements.append(Paragraph(f"- {item}", styles['Normal']))
                    else:
                        elements.append(Paragraph(str(sub_value), styles['Normal']))
            else:
                elements.append(Paragraph(str(value), styles['Normal']))
            
            elements.append(Paragraph(' ', styles['Normal']))  # Add some space
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
