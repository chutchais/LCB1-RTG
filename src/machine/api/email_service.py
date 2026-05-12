import smtplib
import logging
from email.message import EmailMessage
from datetime import datetime, timedelta
import pytz
from machine.api.report_services import get_productivity_report_daily
from machine.api.html_generators import json_to_html_table, json_to_excel

logger = logging.getLogger(__name__)


def send_rtg_productivity_report(
    to_email,
    send_email,
    server='192.168.1.15',
    equipment_list=None,
    shift='all'
):
    """
    Send productivity report via email
    
    Reuses the SAME functions as:
    - /api/productivity-report-daily-html/ (uses json_to_html_table)
    - /api/productivity-report-daily-excel/ (uses json_to_excel)
    
    Date logic:
    - 08:00 run → yesterday's report
    - 20:00 run → today's report
    """
    
    tz = pytz.timezone('Asia/Bangkok')
    now_tz = datetime.now(tz=tz)
    current_hour = now_tz.hour
    
    # ✅ Smart date logic
    if 8 <= current_hour < 20:
        report_date = (now_tz - timedelta(days=1)).date()
        logger.info(f"📅 Morning run: Sending yesterday's report ({report_date})")
        mail_topic_shift = 'Morning and Night shifts' 
    else:
        report_date = now_tz.date()
        logger.info(f"📅 Evening run: Sending today's report ({report_date})")
        mail_topic_shift = 'Morning' 
    try:
        # ✅ Get productivity report (SAME as views.productivity_report_daily_html)
        logger.info(f"📊 Fetching report for {report_date}")
        report_result = get_productivity_report_daily(
            equipment_name=None,  # All equipment
            target_date=str(report_date),
            shift=shift
        )
        
        if report_result['status'] == 'error':
            logger.error(f"Error: {report_result.get('error')}")
            return False
        
        report_data = report_result['data']
        
        # ✅ Generate HTML (SAME as views.productivity_report_daily_html)
        logger.info("📄 Generating HTML")
        html_table = json_to_html_table(report_data)
        
        if not html_table:
            logger.error("Failed to generate HTML")
            return False
        
        # html_body = _wrap_html_email(html_table, report_data, shift)
        html_body = html_table
        
        # ✅ Generate Excel (SAME as views.productivity_report_daily_excel)
        logger.info("📑 Generating Excel")
        excel_bytes = json_to_excel(report_data)
        
        if not excel_bytes:
            logger.error("Failed to generate Excel")
            return False
        
        # ✅ Send email
        msg = EmailMessage()
        msg['Subject'] = f'RTG Productivity: {report_date.strftime("%d-%b-%Y")} ({mail_topic_shift})'
        msg['From'] = send_email
        msg['To'] = to_email if isinstance(to_email, str) else ', '.join(to_email)
        
        msg.set_content(html_body, subtype='html')
        msg.add_attachment(
            excel_bytes,
            maintype='application',
            subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f'productivity-report-{report_date.strftime("%Y-%m-%d")}.xlsx'
        )
        
        logger.info(f"📧 Sending to {msg['To']}")
        with smtplib.SMTP(server) as smtp_server:
            smtp_server.send_message(msg)
        
        logger.info("✅ Email sent successfully")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return False


def _wrap_html_email(html_content, report_data, shift):
    """Wrap HTML in professional email template (same style as views)"""
    
    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.now(tz=tz)
    
    date_range = report_data.get('date_range', {})
    summary = report_data.get('summary', {})
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Daily Productivity Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            h1 {{
                color: #2c3e50;
            }}
            .info {{
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .info p {{
                margin: 5px 0;
            }}
            table {{
                background-color: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin: 20px 0;
            }}
            td, th {{
                padding: 8px 12px;
                text-align: center;
            }}
            th {{
                color: white;
            }}
            @media print {{
                body {{
                    background-color: white;
                }}
                .info {{
                    display: none;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>📊 Daily Productivity Report</h1>
        <div class="info">
            <p><strong>Date Range:</strong> {date_range.get('from', 'N/A')} to {date_range.get('to', 'N/A')}</p>
            <p><strong>Shift:</strong> {shift.upper()}</p>
            <p><strong>Equipment:</strong> {summary.get('total_equipment', 'N/A')}</p>
            <p><strong>Generated:</strong> {now.strftime("%d-%b-%Y %H:%M:%S")} (Bangkok Time)</p>
        </div>
        {html_content}
    </body>
    </html>
    '''