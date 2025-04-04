from datetime import datetime, timedelta

def update_transaction_date(instance):
        instance.created_year       = instance.created.year
        instance.created_month      = instance.created.month
        instance.created_day        = instance.created.day
        instance.created_hour       = instance.created.hour
        instance.created_week       = instance.created.isocalendar()[1]
        instance.save()
        print(f'Update transaction date {instance}...Successful.')

def get_day_or_night_with_date(input_datetime):
    """
    Determines if it's day or night based on the input datetime.
    Adjusts the date if before 8:00 AM (shifts to the previous day).
    
    Args:
        input_datetime (datetime): A datetime object representing the input time.
    
    Returns:
        tuple: (datetime.date, str) - The adjusted date and "Day" or "Night".
    """
    hour = input_datetime.hour

    if 8 <= hour < 20:  # Between 8:00 AM and 7:59 PM
        return input_datetime.date(), "Day"
    else:
        # Adjust date if before 8:00 AM
        adjusted_date = input_datetime.date() - timedelta(days=1) if hour < 8 else input_datetime.date()
        return adjusted_date, "Night"

def get_execution_time_in_minutes(start_datetime, finish_datetime):
    """
    Calculates the execution time between a start and finish datetime in minutes.
    
    Args:
        start_datetime (datetime): The start date and time.
        finish_datetime (datetime): The finish date and time.
    
    Returns:
        int: The total duration in minutes.
    """
    if finish_datetime is None:
        return 0  # Return 0 if finish_datetime is not provided
    # Addded on Apr 4,2025 -- To fix error when Add new failure
    if start_datetime is None :
        return 0
      
    # Calculate the difference between the two datetimes

    
    duration = finish_datetime - start_datetime
    
    # Convert the duration to total minutes
    total_minutes = duration.total_seconds() // 60
    return int(total_minutes)

from datetime import datetime, timedelta

def get_date_range(input_date, period):
    """
    Calculates the start and end date range based on the input date and period.
    
    Args:
        input_date (datetime): The reference date.
        period (str): The period to calculate the range for.
                      Supported values: "yesterday", "this week", "last week", "this month", "last month".
    
    Returns:
        tuple: (start_date, end_date) as datetime.date objects.
    """
#     input_date = input_date.date()  # Ensure input is a date object
    if period == "yesterday":
        start_date = input_date - timedelta(days=1)
        end_date = start_date
    elif period == "today":
        start_date = input_date 
        end_date = input_date
    elif period == "thisweek":
        start_date = input_date - timedelta(days=input_date.weekday())  # Start of this week (Monday)
        end_date = start_date + timedelta(days=6)  # End of this week (Sunday)
    elif period == "lastweek":
        start_date = input_date - timedelta(days=input_date.weekday() + 7)  # Start of last week
        end_date = start_date + timedelta(days=6)  # End of last week
    elif period == "thismonth":
        start_date = input_date.replace(day=1)  # First day of this month
        end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)  # Last day of this month
    elif period == "lastmonth":
        first_day_this_month = input_date.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1)  # First day of last month
        end_date = last_day_last_month  # Last day of last month
    elif period == "thisyear":
        # Start of the current year
        start_date = input_date.replace(month=1, day=1)
        # End of the current year
        end_date = input_date.replace(month=12, day=31)
        return start_date, end_date
    elif period == "lastyear":
        # Start of the previous year
        start_date = input_date.replace(year=input_date.year-1, month=1, day=1)
        # End of the previous year
        end_date = input_date.replace(year=input_date.year-1, month=12, day=31)
        return start_date, end_date
    else:
        raise ValueError(f"Unsupported period: {period}. Use 'yesterday', 'this week', 'last week', 'this month', or 'last month'.")
    
    return start_date, end_date + timedelta(days=1)