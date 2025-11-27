from django.db import transaction
import pandas as pd
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account_and_entitys.models import XX_gfs_Mamping


def _normalize_cell(value):
    """Convert Excel cell values to clean strings or None."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    #if isinstance(value, float) and value.is_integer():
    #    value = int(value)

    value_str = str(value).strip()
    return value_str or None


class GFSMappingsUploadView(APIView):
    """
    Upload GFS mapping rows from an Excel file.

    Expected columns (case-insensitive, spaces allowed):
    - To_Value
    - From_value
    - Target_value
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {"message": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not uploaded_file.name.lower().endswith((".xlsx", ".xls")):
            return Response(
                {"message": "Only Excel files (.xlsx, .xls) are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            df = pd.read_excel(uploaded_file, header=2)
        except Exception as exc:  # pragma: no cover - passthrough for pandas errors
            return Response(
                {"message": f"Unable to read Excel file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized_cols = {
            str(col).strip().lower(): col for col in df.columns
        }
        required_keys = ["to value", "from value", "target value" , "target alias"]
        missing = [key for key in required_keys if key not in normalized_cols]

        if missing:
            return Response(
                {
                    "message": "Missing required columns.",
                    "missing_columns": missing,
                    "expected": required_keys,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        rename_map = {
            normalized_cols["to value"]: "to value",
            normalized_cols["from value"]: "from value",
            normalized_cols["target value"]: "target value",
            normalized_cols["target alias"]: "target alias",
        }
        df = df.rename(columns=rename_map)

        summary = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "total_rows": len(df.index),
        }

        with transaction.atomic():
            for idx, row in df.iterrows():
                to_value = _normalize_cell(row.get("to value"))
                from_value = _normalize_cell(row.get("from value"))
                target_value = _normalize_cell(row.get("target value"))
                target_alias = _normalize_cell(row.get("target alias"))

                # Require To_Value and Target_value to satisfy unique constraint
                if not to_value or not target_value:
                    summary["skipped"] += 1
                    continue

                try:
                    obj, created = XX_gfs_Mamping.objects.update_or_create(
                        To_Value=to_value,
                        Target_value=target_value,
                        defaults={
                            "From_value": from_value,
                            "Target_alias": target_alias,
                            "is_active": True,
                        },
                    )
                    if created:
                        summary["created"] += 1
                    else:
                        summary["updated"] += 1
                except Exception as exc:  # pragma: no cover - DB level errors
                    summary["errors"].append(
                        {
                            "row": int(idx) + 2,  # Excel row number (including header)
                            "to_value": to_value,
                            "from_value": from_value,
                            "target_value": target_value,
                            "target_alias": target_alias,
                            "error": str(exc),
                        }
                    )

        return Response(
            {
                "message": "GFS mapping upload completed.",
                "summary": summary,
            },
            status=(
                status.HTTP_207_MULTI_STATUS
                if summary["errors"]
                else status.HTTP_200_OK
            ),
        )
