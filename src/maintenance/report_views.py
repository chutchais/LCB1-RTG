# Added on Mar 6, 2026 -- Failure Analysis Report Views
from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime, timedelta
import json

# Import Models
from .models import Failure, Section, MachineType, Machine  


from .report_utils import (
    get_today_failures_by_type,
    get_week_failures_by_type,
    get_today_failures_by_section,
    get_week_failures_by_section,
    get_all_sections,
    get_machine_types_by_section,
    get_machine_performance_metrics,
    get_machine_failure_history,
    get_all_machine_types,
    get_timezone,
    get_failures_by_date_range,
    get_performance_metrics_by_date_range,
    get_failures_by_date_shift_and_type,
    get_failures_by_date_and_shift,
    get_today_start_end,  # Add this
    get_week_start_end,   # Add this
    get_failures_by_date_shift_section,
    get_failures_by_date_range_section
)

class WeekFailureReportView(LoginRequiredMixin, TemplateView):
    """Display this week's failure report with trends"""
    template_name = 'maintenance/reports/week_report.html'
    
    def get_context_data(self, **kwargs):
        from .report_utils import get_all_sections, get_week_failures_by_section
        import json
        
        context = super().get_context_data(**kwargs)
        
        section = self.request.GET.get('section', None)
        
        # Get all sections
        sections = list(get_all_sections())
        
        # If no section selected, use first one
        if not section:
            if sections:
                section = sections[0]
            else:
                context['error'] = 'No sections available'
                return context
        
        # Get report data
        report_data = get_week_failures_by_section(section)
        
        # logger.info(f"Week report data: {report_data}")
        
        context['report_data'] = report_data
        context['period_start'] = report_data.get('period_start', '')
        context['period_end'] = report_data.get('period_end', '')
        context['total_failures'] = report_data.get('total_failures', 0)
        context['avg_mttr_hours'] = report_data.get('avg_mttr_hours', 0)
        context['sections'] = sections
        context['selected_section'] = section
        
        # Prepare data for JavaScript - convert to JSON
        context['daily_data_json'] = json.dumps(report_data.get('daily_data', {}))
        context['machine_type_names_json'] = json.dumps(report_data.get('machine_type_names', []))
        context['pareto_data_json'] = json.dumps(report_data.get('pareto_data', {}))
        context['failures_json'] = json.dumps(report_data.get('failures', []))
        
        # logger.info(f"Context daily_data_json: {context['daily_data_json']}")
        
        return context

# ==================== Date Range Selection ====================

class ReportDateRangeView(LoginRequiredMixin, TemplateView):
    """Display date range selector for custom reports"""
    template_name = 'maintenance/reports/date_range_selector.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all sections
        from .report_utils import get_all_sections
        sections = get_all_sections()
        
        context['sections'] = sections
        context['selected_section'] = self.request.GET.get('section', '')
        
        # Set default dates (last 30 days)
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = end_date.strftime('%Y-%m-%d')
        
        return context


# ==================== Custom Date Range Reports ====================

class CustomDateRangeFailureReportView(LoginRequiredMixin, TemplateView):
    """Display failure report for custom date range"""
    template_name = 'maintenance/reports/custom_failure_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
        machine_type = self.request.GET.get('machine_type', None)
        
        if start_date and end_date:
            try:
                report_data = get_failures_by_date_range(start_date, end_date, machine_type)
                context['report_data'] = report_data
                context['start_date'] = start_date
                context['end_date'] = end_date
                context['has_data'] = True
                
                # Calculate avg repair time
                total_repair_time = 0
                total_count = 0
                for mt_data in report_data['machine_types']:
                    for cat in mt_data['by_category']:
                        total_repair_time += sum([f.repairing_time or 0 for f in cat['failures']])
                        total_count += len(cat['failures'])
                
                context['avg_repair_hours'] = round((total_repair_time / total_count / 60), 2) if total_count > 0 else 0
                context['total_failures'] = report_data['total_failures']
            except Exception as e:
                context['error'] = str(e)
                context['has_data'] = False
        else:
            context['has_data'] = False
        
        context['machine_types'] = get_all_machine_types()
        context['selected_machine_type'] = machine_type
        
        return context


class CustomDateRangePerformanceView(LoginRequiredMixin, TemplateView):
    """Display performance metrics for custom date range"""
    template_name = 'maintenance/reports/custom_performance_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
        machine_type = self.request.GET.get('machine_type', None)
        
        if start_date and end_date:
            try:
                metrics = get_performance_metrics_by_date_range(start_date, end_date, machine_type)
                context['metrics'] = metrics
                context['start_date'] = start_date
                context['end_date'] = end_date
                context['has_data'] = True
            except Exception as e:
                context['error'] = str(e)
                context['has_data'] = False
        else:
            context['has_data'] = False
        
        context['machine_types'] = get_all_machine_types()
        context['selected_machine_type'] = machine_type
        
        return context


# ==================== HTML Views ====================

class TodayFailureReportView(LoginRequiredMixin, TemplateView):
    """Display today's failure report with bar chart"""
    template_name = 'maintenance/reports/today_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        machine_type = self.request.GET.get('machine_type', None)
        
        report_data = get_today_failures_by_type(machine_type)
        
        context['report_data'] = report_data
        context['report_date'] = report_data['report_date']
        context['total_failures'] = report_data['total_failures']
        context['avg_repair_hours'] = report_data['avg_repairing_time_hours']
        context['machine_types'] = get_all_machine_types()
        context['selected_machine_type'] = machine_type
        
        return context


class PerformanceMetricsView(LoginRequiredMixin, TemplateView):
    """Display performance metrics dashboard"""
    template_name = 'maintenance/reports/metrics_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        machine_type = self.request.GET.get('machine_type', None)
        
        metrics = get_machine_performance_metrics(machine_type)
        
        context['metrics'] = metrics
        context['report_date'] = metrics['report_date']
        context['machine_types'] = get_all_machine_types()
        context['selected_machine_type'] = machine_type
        
        return context


class MachineDetailReportView(LoginRequiredMixin, TemplateView):
    """Display machine-specific failure history and performance"""
    template_name = 'maintenance/reports/machine_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        machine_name = kwargs.get('machine_name')
        days = int(self.request.GET.get('days', 30))
        
        machine_data = get_machine_failure_history(machine_name, days)
        
        if not machine_data:
            context['error'] = f"Machine '{machine_name}' not found"
            return context
        
        context['machine_data'] = machine_data
        context['machine_name'] = machine_name
        context['days'] = days
        
        return context


# ==================== API Views ====================

class TodayFailureReportAPIView(LoginRequiredMixin, View):
    """API endpoint for today's failure data"""
    
    def get(self, request):
        machine_type = request.GET.get('machine_type', None)
        
        report_data = get_today_failures_by_type(machine_type)
        
        return JsonResponse(report_data, safe=False)


class WeekFailureReportAPIView(LoginRequiredMixin, View):
    """API endpoint for this week's failure data"""
    
    def get(self, request):
        machine_type = request.GET.get('machine_type', None)
        
        report_data = get_week_failures_by_type(machine_type)
        
        return JsonResponse(report_data, safe=False)


class PerformanceMetricsAPIView(LoginRequiredMixin, View):
    """API endpoint for performance metrics"""
    
    def get(self, request):
        machine_type = request.GET.get('machine_type', None)
        
        metrics = get_machine_performance_metrics(machine_type)
        
        return JsonResponse(metrics, safe=False)


class MachineDetailAPIView(LoginRequiredMixin, View):
    """API endpoint for machine detail and history"""
    
    def get(self, request, machine_name):
        days = int(request.GET.get('days', 30))
        
        machine_data = get_machine_failure_history(machine_name, days)
        
        if not machine_data:
            return JsonResponse({'error': f"Machine '{machine_name}' not found"}, status=404)
        
        return JsonResponse(machine_data, safe=False)


# ==================== Custom Date Range API Views ====================

class CustomDateRangeFailureAPIView(LoginRequiredMixin, View):
    """API endpoint for custom date range failure data"""
    
    def get(self, request):
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        machine_type = request.GET.get('machine_type', None)
        
        if not start_date or not end_date:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        try:
            report_data = get_failures_by_date_range(start_date, end_date, machine_type)
            return JsonResponse(report_data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class CustomDateRangePerformanceAPIView(LoginRequiredMixin, View):
    """API endpoint for custom date range performance metrics"""
    
    def get(self, request):
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        machine_type = request.GET.get('machine_type', None)
        
        if not start_date or not end_date:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        try:
            metrics = get_performance_metrics_by_date_range(start_date, end_date, machine_type)
            return JsonResponse(metrics, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class DailyFailureDetailsAPIView(LoginRequiredMixin, View):
    """API endpoint for daily failure details"""
    
    def get(self, request, date):
        shift = request.GET.get('shift', 'all')
        section = request.GET.get('section', None)  # Add section parameter
        
        try:
            failures_data = get_failures_by_date_shift_section(date, shift, section)
            return JsonResponse(failures_data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class TodayFailureReportView(LoginRequiredMixin, TemplateView):
    """Display today's failure report with bar chart"""
    template_name = 'maintenance/reports/today_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        section = self.request.GET.get('section', None)
        
        # If no section selected, redirect to select one
        if not section:
            sections = get_all_sections()
            if sections.exists():
                section = sections.first()
            else:
                context['error'] = 'No sections available'
                return context
        
        report_data = get_today_failures_by_section(section)
        
        context['report_data'] = report_data
        context['report_date'] = report_data['report_date']
        context['total_failures'] = report_data['total_failures']
        context['avg_repair_hours'] = report_data['avg_repairing_time_hours']
        context['sections'] = get_all_sections()
        context['selected_section'] = section
        
        return context






class DailyFailuresRangeAPIView(LoginRequiredMixin, View):
    """API endpoint for date range failure details with section filter"""
    
    def get(self, request):
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        section = request.GET.get('section', None)
        
        if not start_date or not end_date:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        try:
            failures_data = get_failures_by_date_range_section(start_date, end_date, section)
            return JsonResponse(failures_data, safe=False)
        except Exception as e:
            # logger.error(f"Error in DailyFailuresRangeAPIView: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=400)

class CustomFailuresWithChartsAPIView(LoginRequiredMixin, View):
    """API endpoint for custom date range with charts data"""
    
    def get(self, request):
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        section = request.GET.get('section', None)
        
        if not start_date or not end_date:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        try:
            from .report_utils import get_failures_by_date_range_with_charts
            failures_data = get_failures_by_date_range_with_charts(start_date, end_date, section)
            return JsonResponse(failures_data, safe=False)
        except Exception as e:
            # logger.error(f"Error in CustomFailuresWithChartsAPIView: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=400)