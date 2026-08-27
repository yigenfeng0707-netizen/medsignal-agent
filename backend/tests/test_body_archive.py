"""Digital body archive taxonomy and safety-boundary tests."""

import asyncio
import importlib.util
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import crud
from app.models import Base, User

SERVICE_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "body_archive.py"
SPEC = importlib.util.spec_from_file_location("body_archive", SERVICE_PATH)
assert SPEC and SPEC.loader
body_archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(body_archive)


class TestUserAndDateValidation:
    @pytest.mark.parametrize("value, expected", [(1, 1), ("1", 1), ("user_001", 1), ("user_120", 120)])
    def test_normalize_user_id(self, value, expected):
        assert body_archive.normalize_user_id(value) == expected

    @pytest.mark.parametrize("value", ["", "demo", "user_x", "../1", 0, -1])
    def test_reject_invalid_user_id(self, value):
        with pytest.raises(ValueError):
            body_archive.normalize_user_id(value)

    @pytest.mark.parametrize("value", ["", "2026-02", "2024-02-29"])
    def test_accept_valid_partial_dates(self, value):
        assert body_archive.validate_event_date(value) == value

    @pytest.mark.parametrize("value", ["2026/02", "2023-02-29", "2026-13", "today"])
    def test_reject_invalid_dates(self, value):
        with pytest.raises(ValueError):
            body_archive.validate_event_date(value)


class TestTaxonomy:
    def test_specific_side_wins_over_generic_key(self):
        assert body_archive.infer_organ("左膝半月板损伤") == "knee_l"
        assert body_archive.infer_organ("膝关节不适") == "knee"

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("冠心病PCI术后", "heart"),
            ("右肺上叶小结节", "lungs"),
            ("2型糖尿病", "pancreas"),
            ("腰椎间盘突出", "spine"),
            ("左肾结石", "kidneys"),
        ],
    )
    def test_common_medical_record_mapping(self, text, expected):
        assert body_archive.infer_organ(text) == expected

    def test_unknown_text_is_not_guessed(self):
        assert body_archive.infer_organ("常规复诊") is None


class TestSerializationAndAssets:
    def test_legacy_record_preserves_source_fields(self):
        record = SimpleNamespace(
            id=7,
            diagnosis="右肺小结节",
            department="呼吸科",
            hospital="示例医院",
            visit_type="门诊",
            date=datetime(2026, 2, 3),
        )
        payload = body_archive.legacy_medical_record_to_dict(record)
        assert payload["id"] == "medical-7"
        assert payload["organ"] == "lungs"
        assert payload["description"] == "右肺小结节"
        assert payload["source_ref"] == "示例医院 · 呼吸科"

    def test_viewer_and_core_models_are_packaged(self):
        static_dir = Path(__file__).resolve().parents[1] / "app" / "static" / "digital-body"
        assert (static_dir / "index.html").is_file()
        for model in (
            "VH_M_Skin.glb",
            "VH_M_Heart.glb",
            "VH_F_Heart.glb",
            "skeleton/overview-skeleton.glb",
        ):
            assert (static_dir / "models" / model).stat().st_size > 0


class TestArchivePersistence:
    def test_append_record_and_material(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with session_factory() as session:
                session.add(
                    User(
                        id=1,
                        name="测试用户",
                        age=35,
                        gender="男",
                        city="南京",
                        insurance_type="职工医保",
                        employee_status="在职",
                    )
                )
                await session.commit()
                record = await crud.create_body_archive_record(
                    session,
                    "user_001",
                    organ="lungs",
                    event_date="2026-02",
                    source_type="chat",
                    source_label="对话输入",
                    source_ref="",
                    description="肺部复查记录",
                    raw_excerpt="肺部复查记录",
                )
                material = await crud.create_body_archive_material(
                    session, "user_001", filename="胸部CT.pdf", note="复查资料"
                )
                records = await crud.get_body_archive_records(session, 1)
                materials = await crud.get_body_archive_materials(session, 1)
                assert record.id == records[0].id
                assert material.id == materials[0].id
            await engine.dispose()

        asyncio.run(scenario())
