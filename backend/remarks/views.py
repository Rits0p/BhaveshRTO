from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsTheOneAdmin

from .models import Remark
from .serializers import RemarkSerializer


class RemarkListCreateView(APIView):
    """GET /api/remarks — list all remarks (newest first).

    POST /api/remarks — create a remark for a customer.
    """
    permission_classes = [IsTheOneAdmin]

    def get(self, request):
        remarks = Remark.objects.all()
        return Response({
            'success': True,
            'total': remarks.count(),
            'data': RemarkSerializer(remarks, many=True).data,
        })

    def post(self, request):
        serializer = RemarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'success': True, 'message': 'Remark added.', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )


class RemarkDetailView(APIView):
    """GET/PUT/PATCH/DELETE /api/remarks/<uuid:pk> — single remark."""
    permission_classes = [IsTheOneAdmin]

    def get_object(self, pk):
        try:
            return Remark.objects.get(pk=pk)
        except Remark.DoesNotExist:
            return None

    def get(self, request, pk):
        remark = self.get_object(pk)
        if remark is None:
            return Response({'success': False, 'message': 'Remark not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': RemarkSerializer(remark).data})

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        remark = self.get_object(pk)
        if remark is None:
            return Response({'success': False, 'message': 'Remark not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RemarkSerializer(remark, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'message': 'Remark updated.', 'data': serializer.data})

    def delete(self, request, pk):
        remark = self.get_object(pk)
        if remark is None:
            return Response({'success': False, 'message': 'Remark not found.'}, status=status.HTTP_404_NOT_FOUND)
        remark.delete()
        return Response({'success': True, 'message': 'Remark deleted.'})
