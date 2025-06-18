# reports/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Report
from .serializers import ReportSerializer, ReportCreateSerializer
from deep_researcher_agent.deep_report_generator import DeepReportGenerator
# from .worker.report_worker import generate_report_direct

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ReportCreateSerializer
        return ReportSerializer

    def get_queryset(self):
        # Users can see only their own reports
        return Report.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Tie report to requesting user
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # Optionally restrict deletes based on status
        instance = self.get_object()
        if instance.status == Report.STATUS_RUNNING:
            return Response({'detail': 'Cannot delete a running report.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """
        1) Validate & save the incoming Report parameters,
        2) kick off your generation logic,
        3) update the Report record,
        4) return the finished report.
        """
        # Validate input params (uses ReportCreateSerializer)
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 1) Create a new Report with status 'pending' or 'running'
        report: Report = serializer.save(
            user=request.user,
            status=Report.STATUS_RUNNING
        )

        # 2) Run your report-generation logic (sync or async)
        try:
            # result_content, generated_files = generate_report_direct()
            # 3) Update the report record
            # report.content = result_content
            # report.generated_files = generated_files
            report.status = Report.STATUS_COMPLETED
            report.save()
        except Exception as e:
            report.status = Report.STATUS_FAILED
            report.error_message = str(e)
            report.save()
            return Response(
                {'detail': 'Report generation failed', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 4) Serialize & return the finished report
        out = ReportSerializer(report)
        return Response(out.data, status=status.HTTP_200_OK)
