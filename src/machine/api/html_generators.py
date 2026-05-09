# from datetime import datetime


# def json_to_html_table(report_data):
#     """
#     Convert productivity report JSON to HTML table format
    
#     Args:
#         report_data: Dict from get_productivity_report_daily response
    
#     Returns:
#         HTML string of formatted table
#     """
    
#     if not report_data.get('daily_reports') or len(report_data['daily_reports']) == 0:
#         return '<p>No data available</p>'
    
#     html = '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">\n'
    
#     # Header row
#     html += '<thead>\n<tr style="background-color: #2c3e50; color: white;">\n'
#     html += '  <th>Date</th>\n'
#     html += '  <th>Equipment</th>\n'
#     html += '  <th colspan="3">Morning (08:00-20:00)</th>\n'
#     html += '  <th colspan="3">Night (20:00-08:00)</th>\n'
#     html += '  <th colspan="3">Total</th>\n'
#     html += '</tr>\n<tr style="background-color: #2c3e50; color: white;">\n'
#     html += '  <th></th>\n'
#     html += '  <th></th>\n'
#     html += '  <th>Hour</th>\n'
#     html += '  <th>Move</th>\n'
#     html += '  <th>Prod</th>\n'
#     html += '  <th>Hour</th>\n'
#     html += '  <th>Move</th>\n'
#     html += '  <th>Prod</th>\n'
#     html += '  <th>Hour</th>\n'
#     html += '  <th>Move</th>\n'
#     html += '  <th>Prod</th>\n'
#     html += '</tr>\n</thead>\n'
    
#     # Body rows
#     html += '<tbody>\n'
    
#     for day_report in report_data['daily_reports']:
#         date = day_report['date']
#         equipment_list = day_report['equipment']
        
#         for eq_idx, equipment in enumerate(equipment_list):
#             eq_name = equipment['equipment']
            
#             # Determine row styling
#             if eq_idx == 0:
#                 row_style = 'style="border-top: 2px solid #666;"'
#             else:
#                 row_style = ''
            
#             html += f'<tr {row_style}>\n'
            
#             # Date cell (only for first equipment)
#             if eq_idx == 0:
#                 html += f'  <td rowspan="{len(equipment_list)}" style="font-weight: bold; background-color: #f0f0f0;">{date}</td>\n'
            
#             # Equipment cell
#             html += f'  <td style="font-weight: bold; background-color: #f9f9f9;">{eq_name}</td>\n'
            
#             # Morning shift
#             morning = equipment.get('morning')
#             if morning:
#                 morning_hour = round(morning.get('crane_on_minute', 0) / 60, 2)
#                 morning_move = morning.get('number_of_move', '-')
#                 morning_prod = round(morning.get('productivity', 0), 4) if morning.get('productivity') else '-'
#                 html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_hour}</td>\n'
#                 html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_move}</td>\n'
#                 html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_prod}</td>\n'
#             else:
#                 html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
            
#             # Night shift
#             night = equipment.get('night')
#             if night:
#                 night_hour = round(night.get('crane_on_minute', 0) / 60, 2)
#                 night_move = night.get('number_of_move', '-')
#                 night_prod = round(night.get('productivity', 0), 4) if night.get('productivity') else '-'
#                 html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_hour}</td>\n'
#                 html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_move}</td>\n'
#                 html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_prod}</td>\n'
#             else:
#                 html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
            
#             # Total
#             total = equipment.get('total')
#             if total:
#                 total_hour = round(total.get('crane_on_minute', 0) / 60, 2)
#                 total_move = total.get('number_of_move', '-')
#                 total_prod = round(total.get('productivity', 0), 4) if total.get('productivity') else '-'
#                 html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_hour}</td>\n'
#                 html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_move}</td>\n'
#                 html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_prod}</td>\n'
#             else:
#                 html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
            
#             html += '</tr>\n'
    
#     html += '</tbody>\n</table>\n'
    
#     return html


# def json_to_plain_text_table(report_data):
#     """
#     Convert productivity report JSON to plain text table format (for console/email)
    
#     Args:
#         report_data: Dict from get_productivity_report_daily response
    
#     Returns:
#         Plain text formatted table string
#     """
    
#     if not report_data.get('daily_reports') or len(report_data['daily_reports']) == 0:
#         return 'No data available'
    
#     lines = []
    
#     # Header
#     lines.append('┌──────────┬───────────┬──────────────────┬──────────��───────┬──────────────────┐')
#     lines.append('│   Date   │ Equipment │ Morning          │ Night            │ Total            │')
#     lines.append('│          │           │ Hr | Mv | Prod   │ Hr | Mv | Prod   │ Hr | Mv | Prod   │')
#     lines.append('├──────────┼───────────┼──────────────────┼──────────────────┼──────────────────┤')
    
#     first_date = True
    
#     for day_report in report_data['daily_reports']:
#         date = day_report['date']
#         equipment_list = day_report['equipment']
        
#         for eq_idx, equipment in enumerate(equipment_list):
#             eq_name = equipment['equipment']
            
#             # Date column (only for first equipment)
#             if eq_idx == 0:
#                 date_str = date
#                 if not first_date:
#                     lines.append('├──────────┼───────────┼──────────────────┼──────────────────┼──────────────────┤')
#             else:
#                 date_str = '          '
            
#             first_date = False
            
#             # Morning
#             morning = equipment.get('morning')
#             if morning:
#                 m_hr = round(morning.get('crane_on_minute', 0) / 60, 2)
#                 m_mv = morning.get('number_of_move', 0)
#                 m_prod = round(morning.get('productivity', 0), 2) if morning.get('productivity') else 0
#             else:
#                 m_hr = m_mv = m_prod = '-'
            
#             # Night
#             night = equipment.get('night')
#             if night:
#                 n_hr = round(night.get('crane_on_minute', 0) / 60, 2)
#                 n_mv = night.get('number_of_move', 0)
#                 n_prod = round(night.get('productivity', 0), 2) if night.get('productivity') else 0
#             else:
#                 n_hr = n_mv = n_prod = '-'
            
#             # Total
#             total = equipment.get('total')
#             if total:
#                 t_hr = round(total.get('crane_on_minute', 0) / 60, 2)
#                 t_mv = total.get('number_of_move', 0)
#                 t_prod = round(total.get('productivity', 0), 2) if total.get('productivity') else 0
#             else:
#                 t_hr = t_mv = t_prod = '-'
            
#             # Format row
#             morning_str = f'{m_hr} | {m_mv} | {m_prod}'
#             night_str = f'{n_hr} | {n_mv} | {n_prod}'
#             total_str = f'{t_hr} | {t_mv} | {t_prod}'
            
#             line = f'│{date_str}│{eq_name:^11}│{morning_str:^18}│{night_str:^18}│{total_str:^18}│'
#             lines.append(line)
    
#     lines.append('└──────────┴───────────┴──────────────────┴──────────────────┴─��────────────────┘')
    
#     return '\n'.join(lines)


# def json_to_csv(report_data):
#     """
#     Convert productivity report JSON to CSV format
    
#     Args:
#         report_data: Dict from get_productivity_report_daily response
    
#     Returns:
#         CSV formatted string
#     """
    
#     if not report_data.get('daily_reports') or len(report_data['daily_reports']) == 0:
#         return ''
    
#     lines = []
#     lines.append('Date,Equipment,Morning Hour,Morning Move,Morning Productivity,Night Hour,Night Move,Night Productivity,Total Hour,Total Move,Total Productivity')
    
#     for day_report in report_data['daily_reports']:
#         date = day_report['date']
#         equipment_list = day_report['equipment']
        
#         for equipment in equipment_list:
#             eq_name = equipment['equipment']
            
#             # Morning
#             morning = equipment.get('morning', {})
#             m_hr = round(morning.get('crane_on_minute', 0) / 60, 2)
#             m_mv = morning.get('number_of_move', 0)
#             m_prod = round(morning.get('productivity', 0), 4) if morning.get('productivity') else ''
            
#             # Night
#             night = equipment.get('night', {})
#             n_hr = round(night.get('crane_on_minute', 0) / 60, 2)
#             n_mv = night.get('number_of_move', 0)
#             n_prod = round(night.get('productivity', 0), 4) if night.get('productivity') else ''
            
#             # Total
#             total = equipment.get('total', {})
#             t_hr = round(total.get('crane_on_minute', 0) / 60, 2)
#             t_mv = total.get('number_of_move', 0)
#             t_prod = round(total.get('productivity', 0), 4) if total.get('productivity') else ''
            
#             line = f'{date},"{eq_name}",{m_hr},{m_mv},{m_prod},{n_hr},{n_mv},{n_prod},{t_hr},{t_mv},{t_prod}'
#             lines.append(line)
    
#     return '\n'.join(lines)

from datetime import datetime


# def json_to_html_table(report_data):
#     """
#     Convert productivity report JSON to HTML table format
    
#     Args:
#         report_data: Dict from get_productivity_report_daily response
    
#     Returns:
#         HTML string of formatted table
#     """
    
#     if not report_data.get('daily_reports') or len(report_data['daily_reports']) == 0:
#         return '<p>No data available</p>'
    
#     html = '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">\n'
    
#     # Header row
#     html += '<thead>\n<tr style="background-color: #2c3e50; color: white;">\n'
#     html += '  <th>Date</th>\n'
#     html += '  <th>Equipment</th>\n'
#     html += '  <th colspan="3">Morning (08:00-20:00)</th>\n'
#     html += '  <th colspan="3">Night (20:00-08:00)</th>\n'
#     html += '  <th colspan="3">Total</th>\n'
#     html += '</tr>\n<tr style="background-color: #2c3e50; color: white;">\n'
#     html += '  <th></th>\n'
#     html += '  <th></th>\n'
#     html += '  <th>Hour</th>\n'
#     html += '  <th>Move</th>\n'
#     html += '  <th>Prod</th>\n'
#     html += '  <th>Hour</th>\n'
#     html += '  <th>Move</th>\n'
#     html += '  <th>Prod</th>\n'
#     html += '  <th>Hour</th>\n'
#     html += '  <th>Move</th>\n'
#     html += '  <th>Prod</th>\n'
#     html += '</tr>\n</thead>\n'
    
#     # Body rows
#     html += '<tbody>\n'
    
#     for day_report in report_data['daily_reports']:
#         date = day_report['date']
#         equipment_list = day_report['equipment']
        
#         for eq_idx, equipment in enumerate(equipment_list):
#             eq_name = equipment['equipment']
            
#             # Determine row styling
#             if eq_idx == 0:
#                 row_style = 'style="border-top: 2px solid #666;"'
#             else:
#                 row_style = ''
            
#             html += f'<tr {row_style}>\n'
            
#             # Date cell (only for first equipment)
#             if eq_idx == 0:
#                 html += f'  <td rowspan="{len(equipment_list)}" style="font-weight: bold; background-color: #f0f0f0;">{date}</td>\n'
            
#             # Equipment cell
#             html += f'  <td style="font-weight: bold; background-color: #f9f9f9;">{eq_name}</td>\n'
            
#             # Morning shift
#             morning = equipment.get('morning') or {}  # ✅ FIX: Handle None
#             if morning:
#                 morning_hour = morning.get('crane_on_minute', 0) / 60
#                 morning_move = morning.get('number_of_move', '-')
#                 morning_prod = round(morning.get('productivity', 0), 2) if morning.get('productivity') else '-'
#                 html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_hour:.2f}</td>\n'
#                 html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_move}</td>\n'
#                 html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_prod}</td>\n'
#             else:
#                 html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
            
#             # Night shift
#             night = equipment.get('night') or {}  # ✅ FIX: Handle None
#             if night:
#                 night_hour = night.get('crane_on_minute', 0) / 60
#                 night_move = night.get('number_of_move', '-')
#                 night_prod = round(night.get('productivity', 0), 2) if night.get('productivity') else '-'
#                 html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_hour:.2f}</td>\n'
#                 html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_move}</td>\n'
#                 html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_prod}</td>\n'
#             else:
#                 html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
            
#             # Total
#             total = equipment.get('total') or {}  # ✅ FIX: Handle None
#             if total:
#                 total_hour = total.get('crane_on_minute', 0) / 60
#                 total_move = total.get('number_of_move', '-')
#                 total_prod = round(total.get('productivity', 0), 2) if total.get('productivity') else '-'
#                 html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_hour:.2f}</td>\n'
#                 html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_move}</td>\n'
#                 html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_prod}</td>\n'
#             else:
#                 html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
#                 html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
            
#             html += '</tr>\n'
    
#     html += '</tbody>\n</table>\n'
    
#     return html
def json_to_html_table(report_data):
    """
    Convert productivity report JSON to HTML table format
    
    Args:
        report_data: Dict from get_productivity_report_daily response
    
    Returns:
        HTML string of formatted table
    """
    
    if not report_data.get('daily_reports') or len(report_data['daily_reports']) == 0:
        return '<p>No data available</p>'
    
    html = '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">\n'
    
    # Header row
    html += '<thead>\n<tr style="background-color: #2c3e50; color: white;">\n'
    html += '  <th>Date</th>\n'
    html += '  <th>Equipment</th>\n'
    html += '  <th colspan="3">Morning (08:00-20:00)</th>\n'
    html += '  <th colspan="3">Night (20:00-08:00)</th>\n'
    html += '  <th colspan="3">Total</th>\n'
    html += '</tr>\n<tr style="background-color: #2c3e50; color: white;">\n'
    html += '  <th></th>\n'
    html += '  <th></th>\n'
    html += '  <th>Hour</th>\n'
    html += '  <th>Move</th>\n'
    html += '  <th>Prod</th>\n'
    html += '  <th>Hour</th>\n'
    html += '  <th>Move</th>\n'
    html += '  <th>Prod</th>\n'
    html += '  <th>Hour</th>\n'
    html += '  <th>Move</th>\n'
    html += '  <th>Prod</th>\n'
    html += '</tr>\n</thead>\n'
    
    # Body rows
    html += '<tbody>\n'
    
    for day_report in report_data['daily_reports']:
        date = day_report['date']
        equipment_list = day_report['equipment']
        
        for eq_idx, equipment in enumerate(equipment_list):
            eq_name = equipment['equipment']
            
            # Determine row styling
            if eq_idx == 0:
                row_style = 'style="border-top: 2px solid #666;"'
            else:
                row_style = ''
            
            html += f'<tr {row_style}>\n'
            
            # Date cell (only for first equipment)
            if eq_idx == 0:
                html += f'  <td rowspan="{len(equipment_list)}" style="font-weight: bold; background-color: #f0f0f0;">{date}</td>\n'
            
            # Equipment cell
            html += f'  <td style="font-weight: bold; background-color: #f9f9f9;">{eq_name}</td>\n'
            
            # Morning shift
            morning = equipment.get('morning') or {}  # ✅ FIX: Handle None
            if morning is not None:  # ✅ Check for None, not truthiness
                morning_hour = morning.get('crane_on_minute', 0) / 60
                morning_move = morning.get('number_of_move', '-')
                morning_prod = round(morning.get('productivity', 0), 2) if morning.get('productivity') else '-'
                html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_hour:.2f}</td>\n'
                html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_move}</td>\n'
                html += f'  <td style="background-color: #e3f2fd; text-align: center;">{morning_prod}</td>\n'
            else:
                # ✅ EXPLICITLY OUTPUT BLANK CELLS
                html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
                html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
                html += '  <td style="background-color: #e3f2fd; text-align: center;">-</td>\n'
            
            # Night shift
            night = equipment.get('night') or {}  # ✅ FIX: Handle None
            if night is not None:  # ✅ Check for None, not truthiness
                night_hour = night.get('crane_on_minute', 0) / 60
                night_move = night.get('number_of_move', '-')
                night_prod = round(night.get('productivity', 0), 2) if night.get('productivity') else '-'
                html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_hour:.2f}</td>\n'
                html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_move}</td>\n'
                html += f'  <td style="background-color: #f5f5f5; text-align: center;">{night_prod}</td>\n'
            else:
                # ✅ EXPLICITLY OUTPUT BLANK CELLS
                html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
                html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
                html += '  <td style="background-color: #f5f5f5; text-align: center;">-</td>\n'
            
            # Total
            total = equipment.get('total') or {}  # ✅ FIX: Handle None
            if total is not None:  # ✅ Check for None, not truthiness
                total_hour = total.get('crane_on_minute', 0) / 60
                total_move = total.get('number_of_move', '-')
                total_prod = round(total.get('productivity', 0), 2) if total.get('productivity') else '-'
                html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_hour:.2f}</td>\n'
                html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_move}</td>\n'
                html += f'  <td style="background-color: #fff9e6; text-align: center; font-weight: bold;">{total_prod}</td>\n'
            else:
                html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
                html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
                html += '  <td style="background-color: #fff9e6; text-align: center;">-</td>\n'
            
            html += '</tr>\n'
    
    html += '</tbody>\n</table>\n'
    
    return html


def json_to_plain_text_table(report_data):
    """
    Convert productivity report JSON to plain text table format (for console/email)
    
    Args:
        report_data: Dict from get_productivity_report_daily response
    
    Returns:
        Plain text formatted table string
    """
    
    if not report_data.get('daily_reports') or len(report_data['daily_reports']) == 0:
        return 'No data available'
    
    lines = []
    
    # Header
    lines.append('┌──────────┬───────────┬──────────────────┬──────────────────┬──────────────────┐')
    lines.append('│   Date   │ Equipment │ Morning          │ Night            │ Total            │')
    lines.append('│          │           │ Hr | Mv | Prod   │ Hr | Mv | Prod   │ Hr | Mv | Prod   │')
    lines.append('├──────────┼───────────┼──────────────────┼──────────────────┼──────────────────┤')
    
    first_date = True
    
    for day_report in report_data['daily_reports']:
        date = day_report['date']
        equipment_list = day_report['equipment']
        
        for eq_idx, equipment in enumerate(equipment_list):
            eq_name = equipment['equipment']
            
            # Date column (only for first equipment)
            if eq_idx == 0:
                date_str = date
                if not first_date:
                    lines.append('├──────────┼───────────┼──────────────────┼──────────────────┼──────────────────┤')
            else:
                date_str = '          '
            
            first_date = False
            
            # Morning ✅ FIX: Handle None
            morning = equipment.get('morning') or {}
            if morning:
                m_hr = round(morning.get('crane_on_minute', 0) / 60, 2)
                m_mv = morning.get('number_of_move', 0)
                m_prod = round(morning.get('productivity', 0), 2) if morning.get('productivity') else 0
            else:
                m_hr = m_mv = m_prod = '-'
            
            # Night ✅ FIX: Handle None
            night = equipment.get('night') or {}
            if night:
                n_hr = round(night.get('crane_on_minute', 0) / 60, 2)
                n_mv = night.get('number_of_move', 0)
                n_prod = round(night.get('productivity', 0), 2) if night.get('productivity') else 0
            else:
                n_hr = n_mv = n_prod = '-'
            
            # Total ✅ FIX: Handle None
            total = equipment.get('total') or {}
            if total:
                t_hr = round(total.get('crane_on_minute', 0) / 60, 2)
                t_mv = total.get('number_of_move', 0)
                t_prod = round(total.get('productivity', 0), 2) if total.get('productivity') else 0
            else:
                t_hr = t_mv = t_prod = '-'
            
            # Format row
            morning_str = f'{m_hr} | {m_mv} | {m_prod}'
            night_str = f'{n_hr} | {n_mv} | {n_prod}'
            total_str = f'{t_hr} | {t_mv} | {t_prod}'
            
            line = f'│{date_str}│{eq_name:^11}│{morning_str:^18}│{night_str:^18}│{total_str:^18}│'
            lines.append(line)
    
    lines.append('└──────────┴───────────┴──────────────────┴──────────────────┴──────────────────┘')
    
    return '\n'.join(lines)


def json_to_csv(report_data):
    """
    Convert productivity report JSON to CSV format
    
    Args:
        report_data: Dict from get_productivity_report_daily response
    
    Returns:
        CSV formatted string
    """
    
    if not report_data.get('daily_reports') or len(report_data['daily_reports']) == 0:
        return ''
    
    lines = []
    lines.append('Date,Equipment,Morning Hour,Morning Move,Morning Productivity,Night Hour,Night Move,Night Productivity,Total Hour,Total Move,Total Productivity')
    
    for day_report in report_data['daily_reports']:
        date = day_report['date']
        equipment_list = day_report['equipment']
        
        for equipment in equipment_list:
            eq_name = equipment['equipment']
            
            # Morning ✅ FIX: Handle None
            morning = equipment.get('morning') or {}
            if morning:
                m_hr = round(morning.get('crane_on_minute', 0) / 60, 2)
                m_mv = morning.get('number_of_move', 0)
                m_prod = round(morning.get('productivity', 0), 4) if morning.get('productivity') else ''
            else:
                m_hr = m_mv = m_prod = ''
            
            # Night ✅ FIX: Handle None
            night = equipment.get('night') or {}
            if night:
                n_hr = round(night.get('crane_on_minute', 0) / 60, 2)
                n_mv = night.get('number_of_move', 0)
                n_prod = round(night.get('productivity', 0), 4) if night.get('productivity') else ''
            else:
                n_hr = n_mv = n_prod = ''
            
            # Total ✅ FIX: Handle None
            total = equipment.get('total') or {}
            if total:
                t_hr = round(total.get('crane_on_minute', 0) / 60, 2)
                t_mv = total.get('number_of_move', 0)
                t_prod = round(total.get('productivity', 0), 4) if total.get('productivity') else ''
            else:
                t_hr = t_mv = t_prod = ''
            
            line = f'{date},"{eq_name}",{m_hr},{m_mv},{m_prod},{n_hr},{n_mv},{n_prod},{t_hr},{t_mv},{t_prod}'
            lines.append(line)
    
    return '\n'.join(lines)

from datetime import datetime
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def json_to_excel(report_data):
    """
    Convert productivity report JSON to Excel format
    
    Args:
        report_data: Dict from get_productivity_report_daily response
    
    Returns:
        Bytes of Excel file
    """
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Productivity Report"
    
    # Define styles
    header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    title_font = Font(bold=True, size=14, color="2C3E50")
    info_font = Font(size=11)
    
    date_fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
    date_font = Font(bold=True)
    
    equipment_fill = PatternFill(start_color="F9F9F9", end_color="F9F9F9", fill_type="solid")
    equipment_font = Font(bold=True)
    
    morning_fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
    night_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
    total_fill = PatternFill(start_color="FFF9E6", end_color="FFF9E6", fill_type="solid")
    total_font = Font(bold=True)
    
    center_alignment = Alignment(horizontal="center", vertical="center")
    left_alignment = Alignment(horizontal="left", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Title
    ws['A1'] = "Daily Productivity Report"
    ws['A1'].font = title_font
    ws.merge_cells('A1:K1')
    
    # Info section
    current_row = 3
    ws[f'A{current_row}'] = "Date Range:"
    ws[f'B{current_row}'] = f"{report_data['date_range']['from']} to {report_data['date_range']['to']}"
    ws[f'A{current_row}'].font = Font(bold=True)
    
    current_row += 1
    ws[f'A{current_row}'] = "Equipment:"
    ws[f'B{current_row}'] = report_data['summary']['total_equipment']
    ws[f'A{current_row}'].font = Font(bold=True)
    
    current_row += 1
    ws[f'A{current_row}'] = "Generated:"
    ws[f'B{current_row}'] = report_data.get('timestamp', 'N/A')
    ws[f'A{current_row}'].font = Font(bold=True)
    
    # Header row
    current_row = 7
    headers = [
        'Date', 'Equipment',
        'Morning Hour', 'Morning Move', 'Morning Productivity',
        'Night Hour', 'Night Move', 'Night Productivity',
        'Total Hour', 'Total Move', 'Total Productivity'
    ]
    
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=current_row, column=col_idx)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Data rows
    current_row = 8
    
    for day_report in report_data['daily_reports']:
        date = day_report['date']
        equipment_list = day_report['equipment']
        
        for eq_idx, equipment in enumerate(equipment_list):
            eq_name = equipment['equipment']
            
            # Date cell
            date_cell = ws.cell(row=current_row, column=1)
            date_cell.value = date if eq_idx == 0 else ""
            date_cell.fill = date_fill
            date_cell.font = date_font
            date_cell.alignment = center_alignment
            date_cell.border = thin_border
            
            # Equipment cell
            eq_cell = ws.cell(row=current_row, column=2)
            eq_cell.value = eq_name
            eq_cell.fill = equipment_fill
            eq_cell.font = equipment_font
            eq_cell.alignment = left_alignment
            eq_cell.border = thin_border
            
            col = 3
            
            # Morning shift
            morning = equipment.get('morning') or {}
            if morning:
                m_hr = round(morning.get('crane_on_minute', 0) / 60, 2)
                m_mv = morning.get('number_of_move', 0)
                m_prod = round(morning.get('productivity', 0), 4) if morning.get('productivity') else None
            else:
                m_hr = m_mv = m_prod = None
            
            for val in [m_hr, m_mv, m_prod]:
                cell = ws.cell(row=current_row, column=col)
                cell.value = val if val is not None else ""
                cell.fill = morning_fill
                cell.alignment = center_alignment
                cell.border = thin_border
                if val is not None and isinstance(val, (int, float)):
                    cell.number_format = '0.00' if isinstance(val, float) else '0'
                col += 1
            
            # Night shift
            night = equipment.get('night') or {}
            if night:
                n_hr = round(night.get('crane_on_minute', 0) / 60, 2)
                n_mv = night.get('number_of_move', 0)
                n_prod = round(night.get('productivity', 0), 4) if night.get('productivity') else None
            else:
                n_hr = n_mv = n_prod = None
            
            for val in [n_hr, n_mv, n_prod]:
                cell = ws.cell(row=current_row, column=col)
                cell.value = val if val is not None else ""
                cell.fill = night_fill
                cell.alignment = center_alignment
                cell.border = thin_border
                if val is not None and isinstance(val, (int, float)):
                    cell.number_format = '0.00' if isinstance(val, float) else '0'
                col += 1
            
            # Total
            total = equipment.get('total') or {}
            if total:
                t_hr = round(total.get('crane_on_minute', 0) / 60, 2)
                t_mv = total.get('number_of_move', 0)
                t_prod = round(total.get('productivity', 0), 4) if total.get('productivity') else None
            else:
                t_hr = t_mv = t_prod = None
            
            for val in [t_hr, t_mv, t_prod]:
                cell = ws.cell(row=current_row, column=col)
                cell.value = val if val is not None else ""
                cell.fill = total_fill
                cell.font = total_font
                cell.alignment = center_alignment
                cell.border = thin_border
                if val is not None and isinstance(val, (int, float)):
                    cell.number_format = '0.00' if isinstance(val, float) else '0'
                col += 1
            
            current_row += 1
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 12
    for col in range(3, 12):
        ws.column_dimensions[get_column_letter(col)].width = 15
    
    # Set row height for header
    ws.row_dimensions[7].height = 25
    
    # Save to bytes
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer.getvalue()